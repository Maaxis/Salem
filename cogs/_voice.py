# rudimentary AI assistant and TTS/STT via Discord voice chat

import asyncio
import datetime
import gc
import os
import re
import time
import traceback
import wave
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands, voice_recv
from discord.ext.voice_recv import AudioSink, VoiceData

from ai import ai_openai as ai
from ai import character
from ai import transcriber
from ai import tts_out as tts
from utils import load_user_ids

user_ids = load_user_ids()

import contextlib


def get_wav_duration(filepath):
	with contextlib.closing(wave.open(filepath, 'r')) as f:
		frames = f.getnframes()
		rate = f.getframerate()
		return frames / float(rate)


# Ensure Opus is loaded for voice decoding
discord.opus._load_default()


def remove_emojis(text):
	text = text.replace("—", ", ").replace("*", "").replace("=", " equals ").replace("+", " plus ").replace("OH",
	                                                                                                        "Oh").replace(
		"...", ", ").replace("ORG", "org").replace("YAAAS", "Yas")
	emoji_pattern = re.compile(
		"["
		"\U0001F600-\U0001F64F"  # Emoticons
		"\U0001F300-\U0001F5FF"  # Symbols & Pictographs
		"\U0001F680-\U0001F6FF"  # Transport & Map
		"\U0001F1E0-\U0001F1FF"  # Flags
		"\U00002702-\U000027B0"  # Dingbats
		"\U000024C2-\U0001F251"  # Enclosed characters
		"\U0001f900-\U0001f9ff"  # Supplemental Symbols and Pictographs
		"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
		# "\U00002500-\U00002BEF"  # Chinese/Japanese characters and symbols
		"]+",
		flags=re.UNICODE,
	)
	return emoji_pattern.sub(r'', text)


class VoiceRecorder:
	def __init__(self, user: discord.User, filename: str):
		self.user = user
		self.filename = filename
		self._file = wave.open(filename, 'wb')
		self._file.setnchannels(2)
		self._file.setsampwidth(2)
		self._file.setframerate(48000)
		self.last_packet_time = time.time()
		self.active = True

	def write(self, data: bytes):
		self._file.writeframes(data)
		self.last_packet_time = time.time()

	def is_silent_for(self, threshold: float) -> bool:
		return (time.time() - self.last_packet_time) > threshold

	def close(self):
		if self.active:
			self._file.close()
			self.active = False


class VoiceSink(AudioSink):
	def __init__(self, silence_threshold=2.0, on_recording_complete=None,
	             event_loop: Optional[asyncio.AbstractEventLoop] = None, guild_id: int = None, stt=False):
		super().__init__()
		self.stt = stt
		self.recorders: Dict[int, VoiceRecorder] = {}
		self.silence_threshold = silence_threshold
		self.cleanup_tasks: Dict[int, asyncio.Task] = {}
		self.on_recording_complete = on_recording_complete
		self.loop = event_loop or asyncio.get_event_loop()
		self.guild_id = guild_id

	def wants_opus(self) -> bool:
		return False

	# record audio from voice
	def write(self, user: Optional[discord.User], data: VoiceData):
		try:
			if user is None or user.bot:
				return

			if user.id not in self.recorders:
				filename = f"temp/{user.id}_{int(time.time())}.wav"
				recorder = VoiceRecorder(user, filename)
				self.recorders[user.id] = recorder
				print(f"[🔴] Started recording {user.display_name} → {filename}")

				# ✅ Launch silence watcher safely from thread
				asyncio.run_coroutine_threadsafe(
					self._start_silence_watch(user.id),
					self.loop
				)

			if data.pcm:
				pass
			else:
				print(f"[🧊] Got empty audio from {user.display_name}")

			if user.id in self.recorders:
				recorder = self.recorders[user.id]
				if recorder.active:
					recorder.write(data.pcm)
				elif not self.stt:
					print(f"[⚠️] Ignored audio: recorder inactive for {user.display_name}")
				else:
					recorder.active = True
					recorder.write(data.pcm)


		except Exception as e:
			print(f"Exception in write(): {e}")
			traceback.print_exc()

	# create a task for _watch_silence
	async def _start_silence_watch(self, user_id: int):
		print(f"[🧿] Started silence watcher for {self.recorders[user_id].user.display_name}")
		task = asyncio.create_task(self._watch_silence(user_id))
		self.cleanup_tasks[user_id] = task

	# watch for silence before completing recording, then call on_recording_complete
	async def _watch_silence(self, user_id: int):
		print(f"[👂] Watching for silence for {user_id}")
		while True:
			await asyncio.sleep(0.25)
			recorder = self.recorders.get(user_id)
			if recorder:
				elapsed = time.time() - recorder.last_packet_time
				print(f"[⏱️] {recorder.user.display_name} silent for {elapsed:.2f}s")
				if recorder.is_silent_for(self.silence_threshold):
					recorder.close()
					print(f"[🛑] Finished recording {recorder.filename}")
					if self.on_recording_complete:
						await self.on_recording_complete(user_id, recorder.filename, self.guild_id)
					del self.recorders[user_id]  # allow re-recording in future
					break

	def cleanup(self):
		for recorder in self.recorders.values():
			recorder.close()
		for task in self.cleanup_tasks.values():
			task.cancel()


class VoiceCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.sink: Optional[VoiceSink] = None
		self.character = character.init_salem_character(True)
		self.instructions = self.character.instructions
		self.message_history = []
		self.stt = False
		self.tts_channel = None
		self.tts = False
		self.model = transcriber.model

	# text to speech
	async def handle_message(self, message: discord.Message):
		guild = message.guild
		if not guild:
			return
		voice_client = guild.voice_client
		if not voice_client:
			return
		if message.author.bot or message.channel != self.tts_channel or not self.tts:
			return
		msg = remove_emojis(message.content)
		msg = f"{message.author.display_name} said: {msg}"
		await generate_tts_and_play(voice_client, msg)

	# ran after getting audio from another user, called by on_recording_complete
	async def handle_complete(self, user_id: int, path: str,
	                          guild_id: int):  # TODO: separate stt and chat with salem features
		if not self.stt and self.tts:  # TODO: /tts is broken, does nothing after recording, is this why?
			if os.path.exists(path):
				os.remove(path)
			return
		user = self.bot.get_user(user_id)
		duration = get_wav_duration(path)
		if duration < 0.8:
			print(f"[⏱️] Ignored short audio from {user.name} ({duration:.2f}s)")
			if os.path.exists(path):
				os.remove(path)
			return
		if user:
			print(f"handle_complete for {user.name}")
			try:
				guild = self.bot.get_guild(guild_id)
				if not guild:
					print(f"No guild found for ID {guild_id}")
					return
				voice_client = guild.voice_client
				if not voice_client:
					print("No voice client in guild")
					return
				phrase = transcriber.transcribe_audio_wav(path, self.model)
				if os.path.exists(path):  # clean up recording
					os.remove(path)
				print(phrase)
				if self.stt:  # transcribe the message
					try:
						await self.tts_channel.send(f"**{user.display_name}:** {phrase}")
					except asyncio.exceptions.CancelledError:
						await self.tts_channel.send(f"**{user.display_name}:** {phrase}")
				elif not self.tts:  # have Salem respond if not in TTS
					now = datetime.datetime.now()
					author_name = user_ids.get(user_id, "unknown user")
					user_context = ai.get_user_context(author_name, "a member of the VOID server in a voice channel.")
					response, message_history = await ai.response_completion(
						# TODO: move all LLM to this response_completion architecture
						phrase,
						self.instructions,
						user_context=user_context,
						env_context="You are in a voice call. KEEP RESPONSES SHORT - less than 2 sentences.",
						message_history=self.message_history,
						model="gpt-4.1-mini"
					)
					response_time = datetime.datetime.now() - now
					print(f"AI response time: {response_time}")
					now = datetime.datetime.now()
					print(f"[{now}] SALEM:\t" + response)
					# optional save to file - can be used for OBS subtitles
					# with open("salem.txt", "a", encoding="utf-8") as file:
					# file.write("\n" + response)
					response = remove_emojis(response)  # post-process for tts
					await generate_tts_and_play(voice_client=voice_client, text=response)
			except Exception as e:
				print(f"Error in handle_complete: {e}")
				traceback.print_exc()

	# talk to Salem
	@app_commands.command()
	async def join(self, interaction: discord.Interaction):
		"""Join the current voice channel and talk to Salem."""
		try:
			await self.connect_vc(interaction)
		except Exception as e:
			traceback.print_exc()

	@app_commands.command()
	async def leave(self, interaction: discord.Interaction):
		"""Have Salem leave the current voice channel."""
		try:
			await self.disconnect_vc(interaction)
		except Exception as e:
			traceback.print_exc()

	async def connect_vc(self, interaction: discord.Interaction):
		await interaction.response.defer(thinking=True)
		if not interaction.user.voice:
			await interaction.edit_original_response(
				content="MEOW ALERT: You are not lurking in a VC! Are you hiding, or just being a sneaky little gremlin? >:3")
			return
		global model
		model = self.model
		vc = await interaction.user.voice.channel.connect(cls=voice_recv.VoiceRecvClient)
		self.sink = VoiceSink(
			silence_threshold=1.0,
			on_recording_complete=self.handle_complete,
			event_loop=asyncio.get_running_loop(),
			guild_id=interaction.guild.id,
		)
		vc.listen(self.sink)
		await interaction.edit_original_response(
			content="MEOWDY-HO, mortals!! This feline has entered the sacred VC. Who dares entertain my mystical ears? Spill the tea, hoomans! (₌＾ΦωΦ^₌)")

	async def disconnect_vc(self, interaction: discord.Interaction):  # helper function to disconnect
		await interaction.response.defer(thinking=True)
		gc.collect()
		vc = interaction.guild.voice_client
		if vc:
			if hasattr(vc, "stop_receiving"):
				vc.stop_receiving()
			self.sink.cleanup()
			self.stt = False
			self.tts = False
			self.tts_channel = None
			await vc.disconnect(force=True)
			await interaction.edit_original_response(
				content="ABANDON SHIP! Salem has YEETED herself out of VC—probably chasing a laser pointer, not gonna lie. ZOOM ZOOM~!! (ﾉ≧∀≦)ﾉ")
		else:
			await interaction.edit_original_response(content="Who, ME?? In a voice channel? PFFT, as if!")

	@app_commands.command()
	async def stt(self, interaction: discord.Interaction):
		try:
			if not self.stt:
				vc = interaction.guild.voice_client
				if not vc:
					try:
						await self.connect_vc(interaction)
					except Exception as e:
						traceback.print_exc()
				self.tts_channel = interaction.channel
				self.stt = True
				await interaction.response.send_message(
					"MEOWDY-HO, mortals!! This feline has entered the sacred VC to yap the messages from within this channel! (₌＾ΦωΦ^₌)")
			else:
				self.stt = False
				await interaction.response.send_message("✨Speech to Text DISABLED!!!✨")
		except Exception as e:
			traceback.print_exc()

	@app_commands.command()
	async def tts(self, interaction: discord.Interaction):
		vc = interaction.guild.voice_client
		if not vc:
			try:
				await self.connect_vc(interaction)
			except Exception as e:
				traceback.print_exc()
		if not self.tts:
			self.tts = True
			self.tts_channel = interaction.channel
			await interaction.response.send_message(
				"TTS SPELL ACTIVATED! 🗣️✨ Now EVERYONE shall witness my melodious meowagic, echoing through the void like a dramatic confessional! Speak, mortals, and let the audio chaos REIGN!! (ΦωΦ)")
			return
		if self.tts:
			self.tts = False
			await interaction.response.send_message(
				"MEWL OF SILENCE! The TTS has gone DARK—no more mystical incantations in your ears. Did someone cast the ‘mute the gremlin’ curse, or are you just afraid of my sonic purrfection??? (ฅ^•ﻌ•^ฅ)🔇")
			# await self.disconnect_vc(interaction)
			return


async def generate_tts_and_play(voice_client: discord.VoiceClient, text: str):
	now = datetime.datetime.now()
	if not voice_client or not voice_client.is_connected():
		print("Bot is not connected to a voice channel!")
		return

	tts_file = await tts.generate(text)
	tts_time = datetime.datetime.now() - now
	print(f"TTS generation time: {tts_time}")
	try:
		await speak(voice_client, tts_file)
		while voice_client.is_playing():
			await asyncio.sleep(0.5)
		if os.path.exists(tts_file):
			os.remove(tts_file)
	except Exception as e:
		print(f"Error in generate_tts_and_play: {e}")
		traceback.print_exc()


async def speak(voice_client: discord.VoiceClient, filename: str):
	audio_source = discord.FFmpegPCMAudio(filename)

	# If something else is playing, stop it
	if voice_client.is_playing():
		voice_client.stop()

	voice_client.play(audio_source)


async def setup(bot):
	await bot.add_cog(VoiceCog(bot))
