# Generate TTS (used in voice chat)

import asyncio
import edge_tts
from playsound3 import playsound
import datetime

start_time = None
finish_time = None


class TTSConfiguration:
	def __init__(self, voice: str = "zh-CN-XiaoyiNeural", rate: str = "+25%", volume: str = "+0%",
	             pitch: str = "+20Hz"):
		self.voice = voice
		self.rate = rate
		self.volume = volume
		self.pitch = pitch


class TTS:
	def __init__(self, config: TTSConfiguration):
		self.config = config

	async def tts(self, text: str, filename: str = None):
		global start_time
		start_time = datetime.datetime.now()
		if filename is None:
			filename = f"output.mp3"

		communicate = edge_tts.Communicate(
			text,
			voice=self.config.voice,
			rate=self.config.rate,
			volume=self.config.volume,
			pitch=self.config.pitch,
		)

		await communicate.save(filename)
		global finish_time
		finish_time = datetime.datetime.now()
		return filename
		# playsound(filename)


config = TTSConfiguration()
tts = TTS(config)


async def generate(phrase: str):
	filename = await tts.tts(phrase)
	return filename


async def play(filename: str):
	playsound(filename)
