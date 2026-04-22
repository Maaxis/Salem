# general commands
#/ping, /choose, /flip, /roll

import traceback

from discord import app_commands
from discord.ext import commands
import random
import re
import discord
import text_strings


class General(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@app_commands.command(name="ping", description="Test Salem's responsiveness.")
	async def ping(self, interaction: discord.Interaction):
		await interaction.response.send_message("Pong!", ephemeral=True)

	@app_commands.command(name="choose", description="Make a random choice.")
	@app_commands.describe(choices="Separate choices with commas.")
	async def choose(self, interaction: discord.Interaction, choices: str):
		options = choices.split(",")
		choice = random.choice(options)
		options_str = ', '.join(options)
		msg = f"*SPINNING THE CHAOS WHEEL for {interaction.user.display_name}! {text_strings.catJAM}*\nOptions: `{options_str}`\nFINAL CHOICE...\n# **{choice}**\n*✨ THE PAWS OF FATE HAVE SPOKEN!! ✨*"
		await interaction.response.send_message(msg)

	@app_commands.command(name="flip", description="Flip a coin!")
	async def flip(self, interaction: discord.Interaction):
		heads = "[HEADS!](https://file.garden/aP6stBdvrQfG8PTL/heads.png)"
		tails = "[TAILS!](https://file.garden/aP6stBdvrQfG8PTL/tails.png)"
		choice = random.choice([heads, tails])
		msg = f"*FLIPPING A COIN for {interaction.user.display_name}!* {text_strings.catJAM}\n**{choice}**"
		await interaction.response.send_message(msg)

	@app_commands.command(name="roll", description="Roll a die in NdN format (e.g., 2d6+1 or 1d20-2).")
	@app_commands.describe(dice="Format: XdY+Z (e.g., 2d6, 8d6+2, 1d8-1)")
	async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
		try:
			match = re.fullmatch(r'(\d+)d(\d+)([+-]\d+)?', dice.lower().replace(' ', ''))
			if not match:
				await interaction.response.send_message(
					'Format has to be in NdN, optionally with + or - modifier (e.g., 2d6, 1d20+3, 4d8-2)', ephemeral=True)
				return

			rolls = int(match.group(1))
			sides = int(match.group(2))
			modifier = int(match.group(3)) if match.group(3) else 0

			roll_results = [random.randint(1, sides) for _ in range(rolls)]
			total = sum(roll_results) + modifier

			result = ', '.join(map(str, roll_results))
			res = (
				f"🎲 LET THE DICE GODS DECIDE! Rolling {rolls}d{sides}"
				f"{f'{modifier:+}' if modifier else ''} for the mighty {interaction.user.display_name}...\n"
			)
			if rolls > 1 or modifier:
				res += f"Rolled **{result}** {'(+' if modifier > 0 else '(-' if modifier < 0 else ''}{(str(abs(modifier)) + ') ') if modifier else ''}=\n# {total}"
				await interaction.response.send_message(res)
			else:
				res += f"# {result}"
				await interaction.response.send_message(res)
		except:
			print(traceback.format_exc())

async def setup(bot):
	await bot.add_cog(General(bot))
