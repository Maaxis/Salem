# AI personality instructions

import os


class Character:
	def __init__(self, name: str, knowledge_directory: str, instructions_path: str):
		self.name = name
		self.knowledge_directory = knowledge_directory
		with open(instructions_path, 'r', encoding='utf-8') as file:
			self.instructions = file.read()


def init_salem_character(voice=False):
	base_dir = os.path.dirname(__file__)
	if not voice:
		return Character(
			name="Salem",
			knowledge_directory=os.path.join(base_dir, "salem", "knowledge"),
			instructions_path=os.path.join(base_dir, "salem", "character_instructions.txt")
		)
	else:
		return Character(
			name="Salem",
			knowledge_directory=os.path.join(base_dir, "salem", "knowledge"),
			instructions_path=os.path.join(base_dir, "salem", "voice_instructions.txt")
		)


def init_org_character():
	base_dir = os.path.dirname(__file__)
	return Character(
		name="Salem",
		knowledge_directory=os.path.join(base_dir, "org", "knowledge"),
		instructions_path=os.path.join(base_dir, "org", "character_instructions.txt")
	)


def init_vl_character():
	base_dir = os.path.dirname(__file__)
	return Character(
		name="Salem",
		knowledge_directory=os.path.join(base_dir, "org_vl", "knowledge"),
		instructions_path=os.path.join(base_dir, "org_vl", "character_instructions.txt")
	)


def main():
	salem = init_salem_character()
	print(f"{salem.name} instructions loaded. Length: {len(salem.instructions)} characters.")


if __name__ == "__main__":
	main()
