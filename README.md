A Discord chatbot based on the discord.py library with features for the Survivor online reality game (ORG) community. Capable of interfacing with ndimforums.com to automate tedious ORG-related admin tasks, and also contains general and fun features for community Discord servers.
Continuation of https://github.com/Maaxis/Newo

Features:
- General slash commands for customizing role color and icon, random choices, etc.
- Optional AI chatbot based on OpenAI schema, with tool calls for setting reminders, saving memories, or searching through a knowledge database; can communicate over text or via Discord voice chat
- Automatic management of threads in ORG servers (e.g. alliance threads)
- SQL-based ORG database management which can be leveraged to handle the Discord role/permission changes needed when tribes are swapped or a player is booted
- AI-powered transcription of voice memos via faster-whisper
- NDIMTools, a WIP suite for interacting with ndimforums.com through an automated browser via Selenium, which allows:
- Site activity logging and IP checks
- Mass management of word filters to add/remove/import/export word filters quickly
- Automatic reposting of board confessionals to a Discord viewers lounge channel
- Exporting entire threads to a .csv file (useful for grading challenges)
- More to come!
