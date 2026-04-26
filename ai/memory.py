# AI long-term memory handler

import random
import re

MEMORY_FILE = 'ai/salem/knowledge/memories.txt'

save_memory_tool = {
	"name"       : "save_memory",
	"description": "Saves the provided text and tags to a file called memories.txt",
	"parameters" : {
		"type"      : "object",
		"required"  : [
			"text"
		],
		"properties": {
			"text": {
				"type"       : "string",
				"description": "The text to be saved as memory"
			},
			"tags": {
				"type"       : "array",
				"description": "List of tags associated with the memory",
				"items"      : {
					"type"       : "string",
					"description": "A tag related to the memory"
				}
			}
		},
	}
}


def save_memory(text, tags=None):
	tags = tags or []
	with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
		f.write("\n[memory]\n")
		f.write(f"text: {text.strip()}\n")
		f.write(f"tags: {', '.join(tags).lower()}\n")


def load_memories(file_path):
	"""Parses the memories.txt file into a list of dicts."""
	memories = []
	with open(file_path, 'r', encoding='utf-8') as f:
		raw = f.read()

	memory_blocks = raw.split("[memory]")
	for block in memory_blocks:
		if not block.strip():
			continue
		text_match = re.search(r"text:\s*(.+)", block, re.DOTALL)
		tags_match = re.search(r"tags:\s*(.+)", block)
		if text_match:
			text = text_match.group(1).strip()
			tags = tags_match.group(1).strip().split(",") if tags_match else []
			tags = [t.strip().lower() for t in tags]
			memories.append({"text": text, "tags": tags})
	return memories


def select_memories(memories, user_message, n_random=1, n_filtered=2):
	"""Selects a mix of filtered and random memories based on user message."""
	message_words = set(user_message.lower().split())
	filtered = [m for m in memories if any(tag in message_words for tag in m['tags'])]

	selected = []

	# Pick filtered memories first
	if filtered:
		selected += random.sample(filtered, min(n_filtered, len(filtered)))

	# Fill in with random memories if needed
	remaining = [m for m in memories if m not in selected]
	if remaining and len(selected) < (n_filtered + n_random):
		selected += random.sample(remaining, min(n_random, len(remaining)))

	return selected


def select_random_memories(memories, n):
	selected = random.sample(memories, min(n, len(memories)))
	return selected


def format_random_memories_for_prompt(selected_memories):
	"""Formats memories nicely for injection into the prompt."""
	if not selected_memories:
		return ""
	memory_text = "You have many rich memories of VOID. Today, a few memories drift into your mind, influencing your responses:\n"
	for mem in selected_memories:
		memory_text += f"- {mem['text']}\n"
	return memory_text


def prompt_random_memories():
	memories = load_memories("/ai/salem/knowledge1/memories.txt")
	selected = select_random_memories(memories, 5)
	prompt = format_random_memories_for_prompt(selected)
	return prompt


def format_user_memories_for_prompt(selected_memories):
	"""Formats memories nicely for injection into the prompt."""
	if not selected_memories:
		return ""
	memory_text = "Here are memories you have related to the user(s) in the conversation:\n"
	for mem in selected_memories:
		memory_text += f"- {mem['text']}\n"
	return memory_text


def prompt_keyword_memories(keyword):
	memories = load_memories(MEMORY_FILE)
	keyword = keyword.lower()
	selected_memories = []

	for mem in memories:
		text_match = re.search(rf"\b{re.escape(keyword)}\b", mem["text"], re.IGNORECASE)
		tag_match = keyword in mem["tags"]
		if text_match or tag_match:
			selected_memories.append(mem)
	prompt = format_user_memories_for_prompt(selected_memories)
	return prompt
