# utils.py
import datetime
import os
import db.config as config


# get config based on message.guild.id
def get_server_config(guild_id):
	for name, data in config.servers.items():
		if data["id"] == guild_id:
			return data
	return None


def get_token(beta_mode=False):
	"""Get token from secret.py"""
	if beta_mode:
		from db.secret import token_beta
		return token_beta
	else:
		from db.secret import token
		return token


async def log(message, bot, warning=0, dump=None, mention=False):
	"""Send a log message to the log channel with optional traceback or mention."""
	server_cfg = get_server_config(message.guild.id)
	guild = await get_guild_safe(bot, server_cfg["id"])
	if not guild:
		return
	channel = await get_channel_safe(guild, server_cfg["log_channel_id"])
	if not channel:
		return

	now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	warning_label = ['[INFO]', '[WARNING]', '[ERROR]'][warning]

	log_message = f"`{warning_label}` `[{now}]` {message}"
	if dump:
		bot_admin_m = guild.get_member(config.bot_admin)
		traceback_str = dump.replace(os.getcwd(), "...")
		await channel.send(f"{log_message}\n```{traceback_str}```\n{bot_admin_m.mention}")
	elif mention:
		bot_admin_m = guild.get_member(config.bot_admin)
		await channel.send(f"{log_message}\n{bot_admin_m.mention}")
	else:
		await channel.send(log_message)


def determine_context(message):  # todo: set this up actually
	"""Auto determine AI context based on guild and channel."""
	# if message.channel.id == config.servers["sh9"]["vl_channel"]:
	#    return "sh8_viewer"
	# elif message.guild.id == config.servers["sh9"]["id"]:
	#    return "sh8_strict"
	if message.guild.id == config.servers["void"]["id"]:
		return "void"
	return "base"


def load_user_ids(path="db/user_ids.txt"):
	"""Load user ID mappings."""
	user_ids = {}
	with open(path, "r", encoding="utf-8") as f:
		for line in f:
			name, user_id = line.strip().split(",")
			user_ids[int(user_id)] = name
	return user_ids


async def get_guild_safe(bot, guild_id):
	"""Get guild or None if missing."""
	return bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)


async def get_channel_safe(guild, channel_id):
	"""Get channel or None if missing."""
	return guild.get_channel(channel_id) or await guild.fetch_channel(channel_id)
