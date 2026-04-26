import os
import queue

import discord
import asyncio
import requests
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from ai import ai_openai as ai
import utils
import text_strings
from db import config as config
import traceback

BOT_ADMIN = config.bot_admin

CPM = 2000  # Characters per minute typing speed

org_server_ids = [info["id"] for info in config.servers.values() if info.get("type") == "org"]


async def is_whitelisted(member):  # currently for orgs only
	role_ids = [role.id for role in member.roles]
	with open("db/ai_org_whitelist.txt", "r") as f:
		whitelist = f.read().splitlines()
		print(whitelist)
		for _id in whitelist:
			if member.id == int(_id) or int(_id) in role_ids:
				return True
	return False


class AssistantInstance:
	def __init__(self, assistant, personal_channel_id=None, personal_log=None, channel_blacklist=None,
	             server_blacklist=None):
		if channel_blacklist is None:
			channel_blacklist = []
		if server_blacklist is None:
			server_blacklist = []
		self.channel_blacklist = channel_blacklist
		self.server_blacklist = server_blacklist
		self.assistant = assistant
		self.personal_channel_id = personal_channel_id
		self.personal_log = personal_log
		self.memory_buffer = ""
		self.last_personal_message_time = None
		self.personal_timer_task = None
		self.lock = False
		self.chat_history = ""
		self.images_buffer = []
		self.text_file_buffer = ""


class AIHandler(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.user_ids = utils.load_user_ids()
		self.assistants = {}
		self.ai_ready = False
		asyncio.create_task(self.async_init_assistants())

	async def async_init_assistants(self):
		await asyncio.sleep(15)  # Give time for bot to be fully ready
		try:
			print("Initializing Assistants...")
			salem_ai = await asyncio.to_thread(ai.salem_assistant)
			print("Salem initialized")
			# org_ai = await asyncio.to_thread(ai.org_assistant)
			# print("ORG assistant initialized")
			# vl_ai = await asyncio.to_thread(ai.vl_assistant)
			# print("VL assistant initialized")

			self.assistants = {
				"personal": AssistantInstance(assistant=salem_ai,
				                              personal_channel_id=config.servers["void"]["personal_channel_id"],
				                              personal_log="ai/salem/knowledge/salem_channel_log.txt"),
				# "org": AssistantInstance(assistant=org_ai)
				# "vl": AssistantInstance(assistant=vl_ai),
			}
			self.ai_ready = True
			print("AI assistants ready")

		except Exception as e:
			print("Exception occurred in async_init_assistants")
			traceback.print_exc()

	async def handle_message(self, msg_obj):  # called in on_message by bot.py
		msg_dict = self.get_author_and_content(msg_obj)
		if self.is_personal_channel(msg_obj):
			if not self.ai_ready:
				await msg_obj.channel.send(f"I'm still booting up, try again in a moment...{text_strings.SleepyCat}")
				return
			await self.handle_personal_message(msg_obj, msg_dict)
		elif self.is_bot_mentioned(msg_obj):
			if not self.ai_ready:
				await msg_obj.channel.send(f"I'm still booting up, try again in a moment...{text_strings.SleepyCat}")
				return
			await self.handle_public_mention(msg_obj, msg_dict)

	async def download_attachments(self, message):
		"""Downloads images from message attachments and returns a list of image paths."""
		images = []
		text_file = ""
		try:
			if message.attachments:
				for attachment in message.attachments:
					if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
						await attachment.save(f"temp/{attachment.filename}")
						images.append(f"temp/{attachment.filename}")
					elif attachment.filename.lower().endswith(".txt"):
						await attachment.save(f"temp/{attachment.filename}")
						with open(f"temp/{attachment.filename}", "r") as text_file:
							text_file = text_file.read()
			elif message.embeds:
				for embed in message.embeds:
					if embed.url and any(ext in embed.url.lower() for ext in [".png", ".jpg", ".jpeg", ".gif"]):
						img_data = requests.get(embed.url).content
						filename = embed.url.split("/")[-1]
						with open(f"temp/{filename}", 'wb') as handler:
							handler.write(img_data)
						images.append(f"temp/{filename}")
		except Exception as e:
			print(f"Error downloading images: {e}")
		return images, text_file

	def is_personal_channel(self, message):
		"""Returns True if the message is in the 'personal', conversational channel."""
		return message.channel.id == self.assistants["personal"].personal_channel_id

	def is_bot_mentioned(self, message):
		"""Returns True if the message includes a ping of the bot."""
		return self.bot.user in message.mentions

	def get_author_and_content(self, msg_obj):
		"""Takes a message object and returns a dictionary with the author name and the cleaned message content."""
		author_name = self.user_ids.get(msg_obj.author.id,
		                                msg_obj.author.display_name)  # return display name if no user id
		try:
			# this replaces IDs in the message with names
			replaced_content = ai.replace_substrings(msg_obj.content,
			                                         ai.user_mentions)  # TODO: move this all into discord module?
		except Exception as e:
			print(f"Couldn't get replaced_content, returning original content: {e}")
			traceback.print_exc()
			replaced_content = msg_obj.content
		return {
			"author_name": author_name,
			"content"    : replaced_content
		}

	async def handle_public_mention(self, msg_obj, msg_dict):
		if msg_obj.guild.id in org_server_ids:
			# if msg_obj.channel.category.id == 1394759276358139985 or msg_obj.channel.category.id == 1393735964253225101:
			#    ctx = "vl"
			# else:
			ctx = "org"
		else:
			ctx = "public"
		await self.process_ai_input(msg_obj, ctx=ctx, message_content=msg_dict["content"])

	# --------------------- personal channel fun ---------------------

	@app_commands.command()
	async def nap(self, interaction: discord.Interaction):  # deletes personal channel session history
		"""Refresh personal channel chat history."""
		if interaction.channel.id != config.servers["void"]["personal_channel_id"]:
			await interaction.response.send_message("You can only use this command in my personal channel in VOID.",
			                                        ephemeral=True)
			return
		self.assistants["personal"].memory_buffer = ""
		self.assistants["personal"].last_personal_message_time = None
		self.assistants["personal"].personal_timer_task = None
		self.assistants["personal"].chat_history = ""
		await interaction.response.send_message(
			"*BIG STRETCH!* My memory banks have been purrrged and I’m back from my magical catnap—recharged and ready! (≧▽≦)/")

	async def handle_personal_message(self, msg_obj, msg_dict):
		"""Logs a new message in personal channel and sets up response timer."""
		self.append_to_memory_buffer(msg_dict)
		self.append_to_log_file(msg_dict)
		images, text_file = await self.download_attachments(msg_obj)  # list of paths
		if images:
			self.assistants["personal"].images_buffer += images
		if text_file:
			self.assistants["personal"].text_file_buffer += text_file
		if self.assistants["personal"].personal_timer_task and not self.assistants[
			"personal"].personal_timer_task.done() and not self.assistants["personal"].lock:
			self.assistants["personal"].personal_timer_task.cancel()
		if not self.assistants["personal"].lock:
			self.assistants["personal"].personal_timer_task = asyncio.create_task(self.delay_response(msg_obj))
		if self.assistants["personal"].lock:
			pass

	def append_to_memory_buffer(self, msg_dict):
		"""SHORT TERM MEMORY: Adds a new message to AI-formatted memory buffer. Unlike append_to_session_history, this is for temporary use only. Memory buffer is cleared after each AI response."""
		try:
			now = datetime.now().strftime("%H:%M:%S")
			self.assistants["personal"].memory_buffer += f"\n[{now}] {msg_dict['author_name']}: {msg_dict['content']}"
			self.assistants["personal"].last_personal_message_time = datetime.now()
		except Exception as e:
			print(f"Error in append_to_memory: {e}")
			traceback.print_exc()

	def append_to_session_history(self, msg_dict):
		"""MEDIUM TERM MEMORY: Adds a new message to AI-formatted chat history, truncates over 20k. Saved until the bot restarts."""
		try:
			now = datetime.now().strftime("%H:%M:%S")
			self.assistants["personal"].chat_history += f"\n[{now}] {msg_dict['author_name']}: {msg_dict['content']}"
			if len(self.assistants["personal"].chat_history) > 20000:  # truncate
				self.assistants["personal"].chat_history = self.assistants["personal"].chat_history[-20000:]
		except Exception as e:
			print(f"Error in append_to_session_history: {e}")
			traceback.print_exc()

	def append_to_log_file(self, msg_dict):
		"""LONG TERM MEMORY: Logs a new message in personal channel log file."""
		now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		message_content = msg_dict["content"]
		try:
			with open(self.assistants["personal"].personal_log, "a+", encoding="utf-8") as f:
				f.write(f"\n[{now}] {msg_dict['author_name']}: {message_content}")
		except Exception as e:
			print(f"Error in append_to_log_file: {e}")
			traceback.print_exc()

	async def delay_response(self, msg_obj):
		"""Enforces 8 seconds of required silence before the bot responds."""
		try:
			await asyncio.sleep(8)
			if self.assistants["personal"].last_personal_message_time:
				elapsed_seconds = (
						datetime.now() - self.assistants["personal"].last_personal_message_time).total_seconds()
				if round(elapsed_seconds) >= 8:
					try:
						self.assistants["personal"].lock = True  # prevent interruption
						self.assistants["personal"].chat_history += self.assistants["personal"].memory_buffer
						self.assistants["personal"].memory_buffer = ""
						await self.process_ai_input(msg_obj, ctx="personal",
						                            message_content=self.assistants["personal"].chat_history)
						self.assistants["personal"].chat_history += self.assistants[
							"personal"].memory_buffer  # TODO: this isn't using add_to_chat_history so it doesn't truncate lol
						self.assistants["personal"].memory_buffer = ""
						self.assistants["personal"].images_buffer = []
						self.assistants["personal"].text_file_buffer = ""
						self.assistants["personal"].lock = False
					except Exception as e:
						print(f"Error in delayed_personal_response to send_ai_response: {e}")
						traceback.print_exc()
		except asyncio.CancelledError:  # a new message came in
			pass
		except Exception as e:
			print(f"Error in delayed_personal_response: {e}")

	# -----------------------------------------------------------------

	async def process_ai_input(self, msg_obj, ctx, message_content):
		"""Formats prompt for AI and returns response text and thread ID from process_ai_response."""
		# message_content is NOT the same as msg_obj.content in the case of personal channel (chat log preprocessed)
		# ctx should be "personal", "public", or "org", org calls a separate assistant
		author_name = self.user_ids.get(msg_obj.author.id, msg_obj.author.display_name)
		if ctx == "personal":
			user_context = ''
			env_context = ai.get_env_context(ctx="personal")
		elif ctx == "public":
			user_context = ai.get_user_context(name=author_name,
			                                   role='a VOID server member')  # TODO: context for server
			env_context = f"You are speaking in the VOID server, channel #{msg_obj.channel.name}"
		elif ctx == "org":
			try:  # check whitelist
				whitelist = await is_whitelisted(msg_obj.author)
				if not whitelist:
					await msg_obj.channel.send(
						f"PAWS! {text_strings.HackerBongoCat} You gotta promise to follow my rules before we can start meowing—[read them here!](https://discord.com/channels/1377082900163330058/1394759528268038336/1399811066388545546)",
						reference=msg_obj, allowed_mentions=discord.AllowedMentions.none())
					return None
			except Exception as e:
				print(f"Error in process_ai_input: {e}")
				traceback.print_exc()
			user_context = ai.get_user_context(name=author_name, role='someone involved in Survival Horror 9')
			env_context = f"You are speaking in the Survival Horror 9 server, channel #{msg_obj.channel.name}"
		elif ctx == "vl":
			user_context = ai.get_user_context(name=author_name, role='someone viewing Survival Horror 9')
			env_context = f"You are speaking in the Survival Horror 9 server, channel #{msg_obj.channel.name}"
		print(author_name, user_context, env_context)
		thread_id = None
		# get thread id by reply chain
		if msg_obj.reference and msg_obj.reference.resolved:
			replied_msg = msg_obj.reference.resolved
			if replied_msg.author == self.bot.user:
				thread_id = self.bot.assistant_threads.get(replied_msg.id)
			# TODO: set up my own damn threads instead
		# chained messages in personal channel have attachments saved to a buffer, so refer back to them
		if ctx == "personal":
			images = self.assistants["personal"].images_buffer  # list of paths
			text_file = self.assistants["personal"].text_file_buffer  # text content
		elif ctx == "public" or ctx == "vl":
			images, text_file = await self.download_attachments(msg_obj)
		else:
			images, text_file = None, None
		if text_file:
			message_content = message_content + "\n\nContents of attached text file:\n" + text_file
		replaced_input = ai.replace_input(message_content, self.bot.user.id)  # clean user prompt, fix Salem mention
		async with msg_obj.channel.typing():  # start AI streaming
			try:
				response, thread_id = await self.process_ai_response(msg_obj, replaced_input, msg_obj.channel, ctx,
				                                                     thread_id, user_context, env_context, images)
				# clean up
				if images:
					for path in images:
						os.remove(path)
				return response, thread_id  # this doesn't actually do anything?
			except TypeError:  # ?
				return None

	async def process_ai_response(self, message, input_text, channel, ctx, thread_id, user_context, env_context,
	                              images):
		"""Handles processing of AI response. Returns response text and thread ID and sends back to channel."""
		try:
			if not thread_id:
				thread_id = ai.new_thread_id()
			if ctx == "personal" or ctx == "public":
				assistant = self.assistants["personal"].assistant
			elif ctx == "org":
				assistant = self.assistants["org"].assistant
			elif ctx == "vl":
				assistant = self.assistants["vl"].assistant
			future = asyncio.create_task(
				asyncio.to_thread(ai.add_to_thread, message=input_text, bot=self.bot, user_id=message.author.id,
				                  assistant=assistant, thread_id=thread_id, user_context=user_context,
				                  env_context=env_context, images=images))
			if thread_id not in ai.thread_buffers:
				ai.thread_buffers[thread_id] = {
					"queue"     : queue.Queue(),
					"channel_id": message.channel.id,
				}

			if ctx == "personal":  # handle personal context messages by splitting the message based on the delimiter and saving chat history
				buffer = ai.thread_buffers[thread_id]["queue"]
				while True:
					try:
						msg = await asyncio.wait_for(asyncio.to_thread(buffer.get), timeout=60)
					except asyncio.TimeoutError:
						print("Timeout waiting for next AI message in buffer.")
						# return None, thread_id
						if msg:
							msg = msg + "\n\nTimeout waiting for next AI message in buffer."
						else:
							msg = "Timeout waiting for next AI message in buffer."
						break
					if msg is None:  # stream has ended
						break
					response_part = ai.replace_output(msg)
					delay = len(response_part) * (60 / CPM)  # response time based on CPM
					if delay > 10:  # max out at 10 seconds for long response times
						delay = 10
					await asyncio.sleep(delay)
					try:
						for i in range(0, len(response_part), 2000):
							# send message
							chunk = response_part[i:i + 2000]
							msg_obj = await channel.send(chunk)
							# handle logging
							msg_dict = self.get_author_and_content(msg_obj)
							self.append_to_session_history(
								msg_dict)  # annoying that we have to do this but seems to be the only way???
							self.append_to_log_file(msg_dict)
					except discord.errors.HTTPException as e:  # probably tried to send an empty message
						if e.code == 50006:
							print("Tried to send empty message, continuing")
							continue
						else:
							print(f"Discord exception: {e}")
							traceback.print_exc()
							raise
			try:
				response, thread_id = await asyncio.wait_for(future, timeout=60)
			except asyncio.TimeoutError:
				print("Timed out waiting for AI response.")
				response = "Timed out waiting for AI response."
			if response:
				response = ai.replace_output(response)
				if ctx == "personal":  # personal context messages are handled by this point, so we return
					return response, thread_id
				else:
					if ctx == "org" or ctx == "vl":
						response = response + "\n\n*This message was AI-generated. Reply to continue the conversation!*"
					try:
						for i in range(0, len(response), 2000):
							chunk = response[i:i + 2000]
							bot_response = await channel.send(chunk, reference=message,
							                                  allowed_mentions=discord.AllowedMentions.none())
						self.bot.assistant_threads[bot_response.id] = thread_id
						return response, thread_id
					except Exception as e:
						print(f"Error in responding to mention: {e}")
						traceback.print_exc()
						return None, None
			else:
				print("No response")
				return None, None
		except Exception as e:
			print(f"Error in process_ai_response: {e}")
			traceback.print_exc()
			return None, None


async def setup(bot):
	if not bot.test:
		await bot.add_cog(AIHandler(bot))
