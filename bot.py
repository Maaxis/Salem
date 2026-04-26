# starts the bot, also responds to events and triggers cogs to raect

test = False

#import importlib

import discord
from discord import app_commands
from discord.ext import commands
import utils
from datetime import datetime
from rich import print

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# -------- Shared variables --------
bot.paused = False
bot.timer_task = None
bot.latest_message = None
bot.temp_messages = ""
bot.messages = ""
bot.test = test
bot.ai_ready = False

# --------- Load cogs --------
import cogs
async def load_all_cogs():
    for cog in cogs.list_cogs():
        try:
            module_path = f"cogs.{cog}"
            await bot.load_extension(module_path)
            print(f"✅ Loaded cog: {cog}")

        except Exception as e:
            print(f"❌ Failed to load cog '{cog}': {e}")

    for cmd in bot.tree.walk_commands():
        if isinstance(cmd, (app_commands.Command, app_commands.ContextMenu)):
            cmd.guild_only = True

# event listeners
@bot.event
async def on_message(message):
    # log the message
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[green]\\[{now}][/] [cyan]\\[{message.guild.name}: #{message.channel.name}][/] [grey50]{message.author}:[/] {message.content}')
    if not should_process(message):
        return
    # process in cogs if needed
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_message", None)
        if handler:
            await handler(message)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_member_join", None)
        if handler:
            await handler(member)

@bot.event
async def on_member_remove(member):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_member_remove", None)
        if handler:
            await handler(member)

@bot.event
async def on_thread_create(thread):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_thread_create", None)
        if handler:
            await handler(thread)

@bot.event
async def on_thread_update(before, after):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_thread_update", None)
        if handler:
            await handler(before, after)

@bot.event
async def on_thread_member_join(member):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_thread_member_join", None)
        if handler:
            await handler(member)

@bot.event
async def on_raw_reaction_add(payload):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_reaction_add", None)
        if handler:
            await handler(payload)

@bot.event
async def on_raw_reaction_remove(payload):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_reaction_remove", None)
        if handler:
            await handler(payload)

@bot.event
async def on_member_update(before, after):
    for cog in bot.cogs.values():
        handler = getattr(cog, "handle_member_update", None)
        if handler:
            await handler(before, after)

def should_process(message):
    return not message.author.bot and message.guild

# start
async def main():
    await load_all_cogs()
    if not bot.test:
        await bot.start(utils.get_token(beta_mode=False))
    else:
        await bot.start(utils.get_token(beta_mode=True))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
