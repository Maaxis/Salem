#server admin only commands
#/say, /clear

import discord
from discord import app_commands
from discord.ext import commands
import utils

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def user_is_admin(self, interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("You need to be an admin to use this command!", ephemeral=True)
        await utils.log(f"{interaction.channel.mention}: {interaction.user.mention} tried to use an admin command but was not an admin.", self.bot, warning=0)
        return False

    # TODO: rewrite/re-ensure pause

    @app_commands.command()
    async def clear(self, interaction: discord.Interaction):
        """ADMIN ONLY: Delete the last 200 messages in this channel. (WARNING: no confirmation)"""
        if not await self.user_is_admin(interaction):
            return
        await interaction.response.send_message("Clearing messages...", ephemeral=False)
        async for message in interaction.channel.history(limit=200):
            await message.delete()
        await utils.log(f"{interaction.channel.mention}: Cleared by {interaction.user.mention}", self.bot, warning=0)

    @app_commands.command()
    async def say(self, interaction: discord.Interaction, channel: discord.TextChannel, msg: str):
        """ADMIN ONLY: Make the bot speak."""
        if not await self.user_is_admin(interaction):
            return
        await channel.send(msg.replace("\\n", "\n"))
        await interaction.response.send_message("Message sent.", ephemeral=True)
        await utils.log(f"{interaction.channel.mention}: Message sent to {channel.mention} by {interaction.user.mention}.", self.bot, warning=0)

async def setup(bot):
    await bot.add_cog(Admin(bot))
