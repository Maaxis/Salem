# Salem
A Discord chatbot and tool suite with features for the Survivor online reality game (ORG) community. Capable of interfacing with Discord and ndimforums.com to automate tedious ORG-related admin tasks, and also contains general features for community Discord servers.
Named after the fictional cat familiar character played by this bot.
Continuation of the now-legacy https://github.com/Maaxis/Newo.

## Features
### Discord chatbot
Server interactions within Discord via the discord.py library.
- General slash commands for customizing role color and icon, random choices, etc.
- Optional **AI chatbot** based on OpenAI schema, with tool calls for setting reminders, saving memories, or searching through a knowledge database; can communicate over text or via Discord voice chat
- Automatic management of threads in ORG servers (e.g. alliance threads)
- SQL-based **ORG database management** which can be leveraged to handle the Discord role/permission changes needed when tribes are swapped or a player is booted
- AI-powered **voice memo transcription** via faster-whisper

### NDIM-Tools
A WIP suite for interacting with ndimforums.com through an automated browser via Selenium. Note: this and related scripts will eventually be moved to its own repo/library.
- Site activity logging and IP checks
- Mass management of word filters to add/remove/import/export word filters quickly
- Automatic reposting of board confessionals to a Discord viewers lounge channel
- Exporting entire threads to a .csv file (useful for grading challenges)
- Many more general tools available, including remotely creating posts and managing forum masks and permissions

### More to come!
