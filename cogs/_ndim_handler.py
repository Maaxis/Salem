# Handle bridging between ndimtools and Discord

import random

from discord.ext import commands, tasks
import traceback
import ndimtools
import itertools

import text_strings
from cogs.org import log, get_config, set_config
from rich import print
from datetime import datetime


def format_ip_warning(ip_address, display_name1, display_name2, id1, id2):
	url1 = f"http://www.ndimforums.com/survivalhorror10/profile.asp?memberid={id1}"
	url2 = f"http://www.ndimforums.com/survivalhorror10/profile.asp?memberid={id2}"
	return (f"""**IP Address Match**
The IP address **{ip_address}** is shared between users [{display_name1}](<{url1}>) and [{display_name2}](<{url2}>).
If this situation is known or expected, no action is needed. This specific IP match will not be flagged again. Check logs for more info.""")


class NDIMHandler(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.forum = ndimtools.Forum(subdomain="survivalhorror10")
		self.minute_updates.start()

	@tasks.loop(seconds=900)
	async def minute_updates(self):
		await self.bot.wait_until_ready()
		if not self.bot.paused:
			await self.background_tasks()

	async def background_tasks(self):
		await ndimtools.log_active_users(self.forum)
		await self.check_ip_matches()
		await self.confessionals()

	async def confessionals(self, char_min=400):
		try:
			new_posts = await ndimtools.get_active_topics(self.forum, mask=14, time_limit=360)
			if len(new_posts) > 0:
				for post in new_posts:
					# Open the file and check for the existence of the datetime
					file_path = 'db/last_time.txt'
					with open(file_path, 'r+') as file:
						lines = file.readlines()  # Read all lines into a list
						# print(lines)
						if f"{post.time}\n" in lines or f"{post.time}" in [line.strip() for line in lines]:
							# If we have the datetime in the file, we can skip this post
							# TODO: switch to using post ID to confirm an existing post, not datetime
							pass
						else:
							file.write(f"{post.time}\n")
							await log(f"{post.title} ({post.author}) - <{post.url}>", self.bot, warning=0)
							post = await ndimtools.get_post_content_with_time(self.forum, post)
							quote_content = post.content
							while "\n\n\n" in quote_content:
								quote_content = quote_content.replace("\n\n\n", "\n\n")
							quote_content = quote_content.replace("\n", "\n> ")
							if len(quote_content) > char_min:
								guild = self.bot.get_guild(get_config('server_id'))
								current_vl_channel = get_config('active_vl_channel_id')
								channel = guild.get_channel(current_vl_channel)
								await channel.send(
									content=f"{random.choice(text_strings.confessional_notif)} {text_strings.random_happy()}\n[{post.title}](<{post.url}#new>) by **{post.author}**\n> {quote_content[:400]}...")
								with open("db/confessionals.txt", encoding="utf-8", mode="a",
								          errors="replace") as c_file:
									c_file.write(f"\n{post.time} - {post.title} {post.url} by {post.author}\n")
									c_file.write(f"{post.content}\n\n")
		except Exception as e:
			traceback.print_exc()
			await log(f"Error in confessionals(): {e}", self.bot, warning=2, dump=traceback.format_exc())
		now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		print(f'[green]\\[{now}][/] [yellow]\\[ndim_handler][/]: Checked confessionals.')
		self.forum.driver.get(self.forum.url)

	# IP WARNING -----------------------------------------------------
	async def check_ip_matches(self):
		ACTIVITY_LOG = "db/activity.log"
		WHITELIST_FILE = "db/user_ip_whitelist.txt"

		# load whitelisted ips
		whitelist = set()
		try:
			with open(WHITELIST_FILE, "r") as f:
				for line in f:
					user_ids = line.strip().split("|")
					if len(user_ids) == 2:
						whitelist.add(tuple(sorted(user_ids)))
		except FileNotFoundError:
			pass  # No whitelist yet
		except Exception:
			traceback.print_exc()
			raise

		# parse activity log
		try:
			ip_map = {}  # ip -> list of (display_name, user_id)
			with open(ACTIVITY_LOG, "r", encoding="utf-8", errors="replace") as f:
				for line in f:
					parts = line.strip().split("|")
					if len(parts) < 7:
						continue
					display_name, user_id, ip = parts[1], parts[2], parts[5]
					if ip.lower() == "hidden":
						continue
					ip_map.setdefault(ip, []).append((display_name, user_id))
		except Exception:
			traceback.print_exc()

		# detect matches
		new_whitelist_entries = set()
		for ip, users in ip_map.items():
			if len(users) < 2:
				continue
			for (user1, id1), (user2, id2) in itertools.combinations(users, 2):
				if id1 == id2:
					continue  # Same user
				if id1 == "Guest" or id2 == "Guest":
					continue  # guest users
				pair = tuple(sorted([id1, id2]))
				if pair not in whitelist and pair not in new_whitelist_entries:
					print(f"IP Match: {ip}")
					print(f"• {user1} ({id1})")
					print(f"• {user2} ({id2})\n")
					try:
						channel = self.bot.get_channel(get_config('host_channel_id'))
						host_role = self.bot.get_role(get_config('host_role_id'))
						warning_msg = format_ip_warning(ip, user1, user2, id1, id2)
						await channel.send(content=f"<@&{host_role}>\n{warning_msg}")
					except Exception as e:
						print("An error occurred in check_ip_matches(): ", e)
						print(traceback.format_exc())
						await log(f"Error in check_ip_matches(): {e}", self.bot, warning=2, dump=traceback.format_exc())
					new_whitelist_entries.add(pair)

		# append this match to whitelist
		if new_whitelist_entries:
			with open(WHITELIST_FILE, "a") as f:
				for id1, id2 in sorted(new_whitelist_entries):
					f.write(f"{id1}|{id2}\n")
		# ---------------------------------------------------------------


async def setup(bot):
	if not bot.test:
		await bot.add_cog(NDIMHandler(bot))
