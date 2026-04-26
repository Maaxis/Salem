import numpy as np
from faster_whisper import WhisperModel  # , download_model
import wave
# import torch
from datetime import datetime
from librosa import resample
from pydub import AudioSegment

start_time = None
wav_time = None


def _load_model(model_name):
	# return whisper.load_model(model_name)
	pass


# whisper_model = whisper.load_model("medium.en")

def load_model(model_name):
	return WhisperModel(model_name, compute_type="auto", local_files_only=True)


# print("trying to load model")
model = load_model("ai/tmp/medium")
# download_model("medium.en","tmp/medium")
# print("loaded model")
m_prompt = "Use natural, readable punctuation and casing. Terms that may appear include: ORG, Tribal Council, idol, alias, alliance, open ID, or other Survivor-related terms, series name Survival Horror (capitalized), player names Zephyra, Vaughn, Indira, Alma, Avril, Calahan, Janessa, Ivory, Yuko, Dionne, Emerald, Sharai, Odette, Constance, Midori, Sharlene, Svetlana, Pierre, Electra, Kalani, Cicero, Purna, Himari"


def transcribe_audio(audio_np, whisper_model, prompt=m_prompt):
	global wav_time
	now = wav_time
	segments, _ = whisper_model.transcribe(audio_np, language="en", initial_prompt=prompt)
	text = " ".join(segment.text.strip() for segment in segments)
	wav_time = datetime.now()
	print(f"Transcribed in {wav_time - now}")
	return text.strip()


def transcribe_audio_wav(file_path: str, model, prompt=m_prompt) -> str:
	# Open wave file
	global start_time
	global wav_time
	start_time = datetime.now()
	print("Beginning audio file transcription...")
	with wave.open(file_path, 'rb') as wf:
		sample_rate = wf.getframerate()
		n_channels = wf.getnchannels()
		sampwidth = wf.getsampwidth()
		n_frames = wf.getnframes()
		audio_data = wf.readframes(n_frames)
	# print(f"Opened WAV: {datetime.now() - start_time}")
	n1 = datetime.now()
	# Convert byte data to numpy array
	dtype = {1: np.int8, 2: np.int16, 4: np.int32}[sampwidth]
	audio_np = np.frombuffer(audio_data, dtype=dtype).astype(np.float32)
	# print(f"Converted byte data to numpy array: {datetime.now() - n1}")
	n2 = datetime.now()
	# If stereo, average to mono
	if n_channels > 1:
		audio_np = audio_np.reshape(-1, n_channels).mean(axis=1)
	# print(f"Reshaped and averaged: {datetime.now() - n2}")
	n3 = datetime.now()
	# Normalize to [-1.0, 1.0]
	audio_np /= np.iinfo(dtype).max
	# print(f"Normalized: {datetime.now() - n3}")
	# Whisper expects 16000 Hz
	n4 = datetime.now()
	if sample_rate != 16000:
		audio_np = resample(audio_np, orig_sr=sample_rate, target_sr=16000)
	wav_time = datetime.now()
	# print(f"Resampled: {wav_time - n4}")
	# print(f"Converted WAV to NP (Total): {wav_time - start_time}")
	return transcribe_audio(audio_np, model, prompt)


def convert_ogg_to_wav(ogg_path: str) -> str:
	# Load the .ogg file
	audio = AudioSegment.from_file(ogg_path, format="ogg")

	# Define the output .wav file path
	wav_path = ogg_path.rsplit(".", 1)[0] + ".wav"

	# Export to .wav
	audio.export(wav_path, format="wav")

	# Return the .wav file path
	return wav_path


def transcribe_audio_ogg(file_path: str, model, prompt=m_prompt) -> str:
	wav_path = convert_ogg_to_wav(file_path)
	return transcribe_audio_wav(wav_path, model, prompt)


def main():
	pass


if __name__ == "__main__":
	main()
