import asyncio
import gc
import traceback

import aiohttp
import os
import discord
from discord import app_commands
from discord.ext import commands
import ai.transcriber as transcriber
TRANSCRIBE_BLACKLIST = "db/transcribe_blacklist.txt"
TRANSCRIBED_MSGS = "db/transcribed_msgs.txt"


def split_message(text: str, limit: int = 2000) -> list[str]:
    """Split text into chunks under Discord's character limit, preferably at line breaks or spaces."""
    lines = text.splitlines(keepends=True)
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            if len(line) > limit:
                # Fallback to hard split
                for i in range(0, len(line), limit):
                    chunks.append(line[i:i + limit])
            else:
                current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks


class TranscriberCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def handle_message(self, message):
        try:
            for attachment in message.attachments:
                if attachment.filename.endswith('.ogg'):
                    # ignore users that disabled transcribe
                    with open(TRANSCRIBE_BLACKLIST, "r") as f:
                        blacklist = {line.strip() for line in f}
                    if str(message.author.id) in blacklist:
                        return
                    async with message.channel.typing():
                        # save audio to disk
                        ogg_path = f"temp/{attachment.id}.ogg"
                        async with aiohttp.ClientSession() as session:
                            async with session.get(attachment.url) as resp:
                                if resp.status == 200:
                                    with open(ogg_path, 'wb') as f:
                                        f.write(await resp.read())
                        model = transcriber.model
                        result = await asyncio.to_thread(transcriber.transcribe_audio_ogg, ogg_path, model)
                        print(result)

                        #format message
                        header = "**TRANSCRIPTION** (react with :no_entry_sign: to delete, `/transcribe` to disable)\n\n"
                        chunks = split_message(header + result)
                        for chunk in chunks:
                            bot_msg = await message.channel.send(chunk, reference=message, allowed_mentions=discord.AllowedMentions.none())
                            await bot_msg.add_reaction("🚫")
                            with open(TRANSCRIBED_MSGS, "a") as f: # log both bot's message id and OP's message id
                                f.write(f"\n{bot_msg.id},{message.author.id}")
                        # Cleanup
                        del model
                        gc.collect()
                        os.remove(ogg_path)
                        wav_path = f"temp/{attachment.id}.wav"
                        os.remove(wav_path)
        except Exception:
            traceback.print_exc()


    async def handle_reaction_add(self, payload):
        if str(payload.emoji) != "🚫": #ignore if not the delete request
            return
        if payload.user_id == self.bot.user.id: #ignore if it's bot's own reaction
            return
        with open(TRANSCRIBED_MSGS, "r") as f:
            transcribed = {}
            for line in f:
                try:
                    msg_id, user_id = line.strip().split(",")
                    transcribed[int(msg_id)] = int(user_id)
                except Exception:
                    continue
        # check if the message was transcribed
        if payload.message_id not in transcribed:
            return

        # check if the user who reacted is the one who triggered the transcription
        if payload.user_id != transcribed[payload.message_id]:
            return

        # fetch the channel and message
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(payload.channel_id)

        try:
            msg = await channel.fetch_message(payload.message_id)
            await msg.delete() # delete
        except discord.NotFound:
            pass  # message already deleted

    @app_commands.command()
    async def transcribe(self, interaction: discord.Interaction):
        """Enable or disable automatic transcription of messages sent as voice memos."""
        user_id = str(interaction.user.id)
        with open(TRANSCRIBE_BLACKLIST, "r") as f:
            blacklist = {line.strip() for line in f}
        if user_id in blacklist:
            blacklist.remove(user_id)
            message = "Auto transcription enabled! Try sending a voice memo!"
        else:
            blacklist.add(user_id)
            message = "Auto transcription disabled! I'll ignore your voice memos."
        with open(TRANSCRIBE_BLACKLIST, "w") as f:
            for uid in blacklist:
                f.write(f"{uid}\n")
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot):
    if not bot.test:
        await bot.add_cog(TranscriberCog(bot))
