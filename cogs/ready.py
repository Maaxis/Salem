# forces slash commands to sync on startup
import discord
from discord.ext import commands
import traceback
from db import config as config

class ReadyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # --- Sync slash commands globally ---
        try:
            await self.bot.tree.sync()
            print("✅ Slash commands synced globally.")
        except Exception as e:
            print(f"Slash sync failed globally: {e}")

        # --- Sync to servers quickly ---
        for name, info in config.servers.items():
            if info.get("auto_sync") == True:
                guild_id = info["id"]
                try:
                    guild = discord.Object(id=guild_id)
                    await self.bot.tree.sync(guild=guild)
                    print(f"✅ Slash commands synced to server \"{name}\" (ID: {guild_id}).")
                except Exception as e:
                    print(f"Sync failed with server \"{name}\" (ID: {guild_id}): {e}")
                    traceback.print_exc()

        print(f"Logged in as {self.bot.user.name}\n------")

async def setup(bot):
    await bot.add_cog(ReadyCog(bot))
