# bot functions for ongoing game
import asyncio
from typing import Literal
import discord
from discord import app_commands
from discord.ext import tasks, commands
import traceback
from datetime import datetime, timedelta
import text_strings
from db.config import bot_admin
import db.sql as db
import configparser
from bot import bot

if bot.test:
	test = True
else:
	test = False


def get_config(key):
	_config = configparser.ConfigParser()
	_config.read("db/org_config.ini")
	if key:
		if not test:
			return int(_config['DEFAULT'][key])
		else:
			return int(_config['TEST'][key])
	else:
		if not test:
			return _config['DEFAULT']
		else:
			return _config['TEST']


def set_config(key, value):
	_config = configparser.ConfigParser()
	_config.read("db/org_config.ini")
	if not test:
		_config['DEFAULT'][key] = str(value)
	else:
		_config['TEST'][key] = str(value)
	with open("db/org_config.ini", "w") as configfile:
		_config.write(configfile)
	if not test:
		return _config['DEFAULT'][key]
	else:
		return _config['TEST'][key]


async def log(message, bot, warning, dump=None, mention=False):
	guild = bot.get_guild(get_config('server_id'))
	if guild is None:
		try:
			guild = await bot.fetch_guild(get_config('server_id'))
		except discord.NotFound:
			print(f"Guild with ID {get_config('server_id')} not found.")
			return
		except discord.Forbidden:
			print(
				f"Bot does not have permission to access guild with ID {get_config('server_id')}."
			)
			return
		except discord.HTTPException as e:
			print(f"Failed to fetch guild: {e}")
			return

	channel = guild.get_channel(get_config('log_channel_id'))
	if channel is None:
		try:
			channel = await guild.fetch_channel(get_config('log_channel_id'))
		except discord.NotFound:
			print(f"Channel with ID {get_config('log_channel_id')} not found.")
			return
		except discord.Forbidden:
			print(
				f"Bot does not have permission to access channel with ID {get_config('log_channel_id')}."
			)
			return
		except discord.HTTPException as e:
			print(f"Failed to fetch channel: {e}")
			return
	print(message)
	now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	warning_label = ''
	if warning == 0:
		warning_label = "[INFO]"
	elif warning == 1:
		warning_label = "[WARNING]"
	elif warning == 2:
		warning_label = "[ERROR]"
	if dump:
		bot_admin_m = guild.get_member(bot_admin)
		traceback_str = dump.replace("C:\\SalemVOID", "...\\")
		traceback_str = traceback_str.replace("C:\\Users\\Max\\AppData\\Local\\Programs", "...\\")
		await channel.send(f"`{warning_label}` `[{now}]` {message}\n```{traceback_str}```\n{bot_admin_m.mention}")
	elif mention:
		bot_admin_m = guild.get_member(bot_admin)
		await channel.send(f"`{warning_label}` `[{now}]` {message}\n{bot_admin_m.mention}")
	else:
		await channel.send(f"`{warning_label}` `[{now}]` {message}")


async def user_is_admin(interaction):
	return interaction.user.guild_permissions.administrator and interaction.guild.id == get_config('server_id')


class Game(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def handle_message(self, msg_obj):  # called in on_message by bot.py
		if self.is_bot_mentioned(msg_obj):
			await msg_obj.channel.send(f"AI chatbot has been disabled, sorry!")

	@app_commands.command()
	async def current_vl_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
		"""Set currently active VL channel for confessional updates."""
		if not await user_is_admin(interaction):
			await interaction.response.send_message(
				"You need to be an admin and in the SH10 server to use this command.")
			return
		try:
			set_config('active_vl_channel_id', channel.id)
			await interaction.response.send_message(f"Set current VL channel to <#{channel.id}>", ephemeral=True)
		except Exception:
			traceback.print_exc()
			await log(f"An error occurred in current_vl_channel", self.bot, warning=2, dump=traceback.format_exc())

	# confirmation button
	class Confirm(discord.ui.View):

		def __init__(self, original_user: discord.User):
			super().__init__()
			self.value = None
			self.original_user = original_user

		@discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
		async def confirm(self, interaction: discord.Interaction,
		                  button: discord.ui.Button):
			if interaction.user == self.original_user:
				await interaction.response.send_message("HOLD YOUR KITTENS! Processing your request! 🐱✨",
				                                        ephemeral=False)
				self.value = True
				self.stop()
			else:
				await interaction.response.send_message("PAWS OFF! That button isn't for you! 🚫",
				                                        ephemeral=True)

		@discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
		async def cancel(self, interaction: discord.Interaction,
		                 button: discord.ui.Button):
			if interaction.user == self.original_user:
				await interaction.response.send_message("ABORT MISSION! The chaos has been averted... for now. 🔥",
				                                        ephemeral=False)
				self.value = False
				self.stop()
			else:
				await interaction.response.send_message("PAWS OFF! That button isn't for you! 🚫",
				                                        ephemeral=True)

	# Using these commands requires db/game.db to be up to date
	'''
	@app_commands.command() #modify cast list TODO: make dynamic
	async def boot(self, interaction: discord.Interaction, player: str, status: Literal['PREJURY', 'JURY'], placement: int):
		"""ADMIN ONLY: Update basically everything after TC results. WARNING: fix get_tribes() first"""
		try:
			if self.bot.paused:
				await interaction.response.send_message(
					text_strings.pause_msg, ephemeral=True)
				await log(
					f"{interaction.channel.mention}: {interaction.user.mention} tried to use /boot but the bot is paused.",
					self.bot,
					warning=0)
				return
			if not await user_is_admin(interaction):
				await interaction.response.send_message(
					"You need to be an admin and in the SH9 server to use this command.")
				return
			players = await db.get_players()
			for p in players:
				if p.name.lower() == player.lower():
					player = p
			if player.status != "CONTESTANT":
				await interaction.response.send_message("Player must be a CONTESTANT.")
			view = self.Confirm(interaction.user)
			await interaction.response.send_message(
				f"**WARNING: "
				f"**Confirm you want the following to occur:**"
				f"\n- Lock all alliance threads with {player.name}"
				f"\n- Remove tribe role from {player.name}"
				f"\n- Remove Alive role from {player.name}"
				f"\n- Add {status} role to {player.name}"
				f"\n- Update {player.name}'s tribe, placement, and status in database"
				f"\nAfterwards, use /current_vl_channel",
				view=view, ephemeral=False)
			await view.wait()
			if view.value is None:
				await interaction.channel.send(
					content="Oh no, the buttons timed out! You'll need to run the command again to confirm your decision.")  # TODO: check how long this is?
			elif view.value:  # hit confirm
				await interaction.channel.send(content="Alright, let's go!")
				await self._boot(player, status, placement)
				#await self._tribe_vote_end()
			else:
				print('Canceled.')

		except Exception as e:
			await log(
				f"{interaction.channel.mention}: {interaction.user.mention} tried to use `/boot` but an error occurred: `{e}`",
				self.bot, warning=2, dump=traceback.format_exc()
			)

	async def boot_from_tribe(self, player, status):  # todo: fix assuming all these roles exist
		guild = self.bot.get_guild(get_config('server_id'))
		player_role = guild.get_role(player.d_role_id)
		member = None
		if player_role:
			member = player_role.members[0]
		#tribes = await get_tribes()
		tribes = '' #placeholder
		tribe_roles = []
		if len(tribes) > 0:
			for tribe in tribes:
				role = guild.get_role(tribe.d_role_id)
				tribe_roles.append(role)
		else:
			await log("Can't remove tribe role from user because get_tribes() did not return any tribes", self.bot, warning=1, mention=True)
		#conf = db.get_config()
		contender_role = guild.get_role(get_config('alive_role_id'))
		tribe_removed = False
		contender_removed = False
		for role in member.roles:
			if role in tribe_roles:
				await member.remove_roles(role)
				tribe_removed = True
			if role == contender_role:
				await member.remove_roles(role)
				contender_removed = True
		if not tribe_removed:
			await log("Failed to remove tribe role from user because get_tribes() did not return any of their roles", self.bot, warning=1, mention=True)
		if not contender_removed:
			await log("Failed to remove contender role from user", self.bot, warning=1, mention=True)
		new_role = None
		if status.lower().startswith("jury"):
			new_role = guild.get_role(get_config('jury_role_id'))
		elif status.lower().startswith("pre"):
			new_role = guild.get_role(get_config('prejury_role_id'))
		await member.add_roles(new_role)

	async def _boot(self, player, status, placement):
		try:
			await self.lock_alliance_threads(player)
			await log(f"Locked alliance threads for {player.name}", self.bot, warning=0)
			await self.boot_from_tribe(player, status)
			await log(f"Edited roles for {player.name}", self.bot, warning=0)
			db.update_player(d_role_id=player.d_role_id, name=player.name, d_channel_id=player.d_channel_id, f_board_id=player.f_board_id, f_user_id=player.f_user_id, tribe_id=0, status=status, placement=placement)
			await log(f"Updated player database for {player.name}", self.bot, warning=0)
			await log(f"Done.", self.bot, warning=0)
		except Exception as e:
			await log(f"An error occurred while booting {player.name}: {e}", self.bot, warning=2,
					  dump=traceback.format_exc())

	async def lock_alliance_threads(self, player):
		try:
			guild = self.bot.get_guild(get_config('server_id'))
			alliance_threads = (self.bot.get_channel(get_config('alliance_channel_id'))).threads
			role_id = str(player.d_role_id)
			for thread in alliance_threads:
				if thread.is_private and not thread.archived and not thread.locked:
					thread_members = await thread.fetch_members()
					locked = False
					for member in thread_members:
						if locked:
							break
						real_member = guild.get_member(member.id)
						for role in real_member.roles:
							if str(role.id) == role_id:
								await thread.send(content="🔒")
								await thread.edit(locked=True)
								await log(f"Locked {thread.mention} for {player.name}.", self.bot, warning=0)
								locked = True
								break
		except:
			raise
	'''

	async def handle_member_join(self, member):  # ping hosts on server member join
		if member.guild.id == get_config('server_id'):
			try:
				channel = self.bot.get_channel(get_config('host_channel_id'))
				host_role = get_config("host_role_id")
				await channel.send(content=f"{member.mention} joined the server. <@&{host_role}>")
				await log(f"{member.mention} joined the server.", self.bot, warning=0)
			except Exception as e:
				await log(f"An error occurred in handle_member_join: {e}", self.bot, warning=2,
				          dump=traceback.format_exc())

	async def handle_member_remove(self, member):  # ping hosts on server member leave
		if member.guild.id == get_config('server_id'):
			try:
				channel = self.bot.get_channel(get_config('host_channel_id'))
				host_role = get_config("host_role_id")
				await channel.send(content=f"{member.mention} left the server. <@&{host_role}>")
				await log(f"{member.mention} left the server.", self.bot, warning=0)
			except Exception as e:
				await log(f"An error occurred in handle_member_remove: {e}", self.bot, warning=2,
				          dump=traceback.format_exc())

	async def handle_thread_create(self, thread):  # new thread
		if thread.guild.id == get_config('server_id'):
			try:
				# auto lock thread
				channel = self.bot.get_channel(get_config('alliance_channel_id'))
				host_role = get_config("host_role_id")
				if thread.is_private and thread.parent == channel:  # alliance thread - auto add hosts and viewers
					await thread.edit(invitable=False)
					viewer_role = get_config("viewer_role_id")
					await thread.send(
						content=f"{text_strings.new_alliance_msg}\n<@&{host_role}> <@&{viewer_role}>")
					await log(
						f"{thread.mention}: New alliance thread has been automatically set to non-invitable.",
						self.bot,
						warning=0)
				else:
					await thread.send(content=f"<@&{host_role}>")  # not alliance thread - just add hosts
			except Exception as e:
				await log(
					f"{thread.mention}: An error occurred while handling an alliance thread: {e}", self.bot, warning=2,
					dump=traceback.format_exc())

	async def handle_thread_update(self, before,
	                               after):  # for private threads, keep locked / uninvitable by non thread owner
		if after.guild.id == get_config('server_id'):
			try:
				if self.bot.paused:
					await log(
						f"{after.mention}: An alliance thread was updated while the bot is paused. The thread has not been automatically set to non-invitable.",
						self.bot,
						warning=0)
					return
				if after.is_private and after.invitable:
					await after.edit(invitable=False)
					await log(
						f"{after.mention}: Alliance thread has been locked for invites.",
						self.bot,
						warning=0)
					print(f'Thread {after.name} has been locked again for new invites.')
			except Exception as e:
				await log(
					f"{after.mention}: An error occurred while updating the alliance thread: {e}",
					self.bot,
					warning=2, dump=traceback.format_exc())

	async def handle_thread_member_join(self,
	                                    member):  # for alliance threads, don't allow new users to join after 10min
		try:
			if member.thread.guild.id == get_config('server_id'):
				if self.bot.paused:
					await log(
						f"{member.mention}: A user joined an alliance thread while the bot is paused. No updates have been made to the thread members.",
						self.bot,
						warning=1)
					return
				thread = member.thread
				created_at = thread.created_at
				now = datetime.now(tz=created_at.tzinfo)
				time_diff = now - created_at
				if time_diff >= timedelta(minutes=10):  # adjust time as needed
					async for message in thread.history(
							limit=3):  # checks 3 most recent messages
						if any(mention.id == member.id for mention in message.mentions):
							# found the invite message
							author = message.author
							guild = thread.guild
							author_permissions = guild.get_member(author.id).guild_permissions
							channel = self.bot.get_channel(get_config('alliance_channel_id'))
							host_role = guild.get_role(get_config('host_role_id'))
							viewer_role = guild.get_role(get_config('viewer_role_id'))
							if not author_permissions.manage_threads and thread.parent == channel:
								invited_member = guild.get_member(member.id)
								if host_role not in invited_member.roles and viewer_role not in invited_member.roles:
									await thread.remove_user(member)
									await thread.send(
										content=
										f"MORE ALLIES, MORE POWER! If you wanna bring in reinforcements, start a fresh alliance and PLOT YOUR DOMINATION! {text_strings.catJAM}"
									)
									await log(
										f"{thread.mention}: {author.mention} attempted to invite {invited_member.mention} to the thread and was blocked.",
										self.bot,
										warning=0)
							break  # stop once the invite message is found
		except Exception as e:
			await log(f"Something went wrong in handle_thread_member_join: {e}", self.bot, warning=2,
			          dump=traceback.format_exc())

	async def handle_reaction_add(self, payload):  # viewer disclaimer reaction
		# print("handle_reaction_add called")
		if payload.message_id == 1484605667355394239:  # viewer verify TODO: don't hardcode message id
			try:
				guild = self.bot.get_guild(payload.guild_id)
				member = guild.get_member(payload.user_id)
				host_role = guild.get_role(get_config('host_role_id'))
				viewer_role = guild.get_role(get_config('viewer_role_id'))
				if host_role not in member.roles and viewer_role not in member.roles:
					await member.add_roles(viewer_role)
					unverified_role = guild.get_role(get_config('unverified_role_id'))
					await member.remove_roles(unverified_role)
					await log(f"Viewer {member.mention} has verified by reacting to the viewer disclaimer.", self.bot,
					          warning=0)
			except:
				await log(f"An error occurred while adding the viewer role to {member.mention}.", self.bot, warning=2,
				          dump=traceback.format_exc())

	async def handle_member_update(self, before, after):  # for adding new viewers to alliance threads
		if after.guild.id == get_config('server_id'):
			if not self.bot.paused:
				if get_config('viewer_role_id') in [role.id for role in after.roles] and get_config(
						'viewer_role_id') not in [role.id for role in
				                                  before.roles]:
					try:
						await log(
							f"Adding {after.mention} to alliance threads in 1 minute (unless viewer role is removed).",
							self.bot,
							warning=0)
						await asyncio.sleep(60)

						# double check user still has viewer role (for accidents)
						after = await after.guild.fetch_member(after.id)
						if get_config('viewer_role_id') in [role.id for role in after.roles]:
							# alliance channel
							channel = self.bot.get_channel(get_config('alliance_channel_id'))
							if channel is not None:
								# fetch all threads in the channel
								threads = channel.threads
								# iterate over each thread and check if private
								for thread in threads:
									if thread.is_private and not thread.locked and not thread.archived:
										await thread.send(content=f"A NEW VIEWER IN OUR MIDST! {after.mention}")
										await asyncio.sleep(1)  # try to prevent api rate limit LOL
								await log(f"Added {after.mention} to alliance threads.", self.bot, warning=0)
						else:
							await log(f"Viewer role removed from {after.mention}.", self.bot, warning=0)
					except Exception as e:
						await log(f"An error occurred trying to add a viewer to alliances: {e}", self.bot, warning=2)

	def is_bot_mentioned(self, message):
		"""Returns True if the message includes a ping of the bot."""
		return self.bot.user in message.mentions


async def setup(bot):
	await bot.add_cog(Game(bot))
