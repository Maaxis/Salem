# Commands for a general community hub server
# /icon: set role icon
# /color: set role color

from datetime import datetime

from discord import app_commands, Attachment
from discord.ext import commands

import aiohttp

import traceback

import discord
from discord import Guild, Permissions, Colour, Role
from typing import Union, Optional, Dict, Any, Literal
from discord.utils import MISSING, _bytes_to_base64_data
from db.config import servers, bot_admin

from PIL import Image
from io import BytesIO

SERVER_ID = servers["void"].get("id")
LOG_CHANNEL_ID = servers["void"].get("log_channel_id")

MAX_ICON_SIZE = 256 * 1024  # 256 KB



# overridden create_role with new role gradient feature
async def patched_create_role(
        self: Guild,
        *,
        name: str = MISSING,
        permissions: Permissions = MISSING,
        color: Union[Colour, int] = MISSING,
        colour: Union[Colour, int] = MISSING,
        hoist: bool = MISSING,
        display_icon: Union[bytes, str] = MISSING,
        mentionable: bool = MISSING,
        reason: Optional[str] = None,
        colors: Optional[Dict[str, Optional[int]]] = None  # New field
) -> Role:
    fields: Dict[str, Any] = {}

    if permissions is not MISSING:
        fields["permissions"] = str(permissions.value)
    else:
        fields["permissions"] = "0"

    actual_colour = colour or color or Colour.default()
    fields["color"] = actual_colour if isinstance(actual_colour, int) else actual_colour.value

    if hoist is not MISSING:
        fields["hoist"] = hoist

    if display_icon is not MISSING:
        if isinstance(display_icon, bytes):
            fields["icon"] = _bytes_to_base64_data(display_icon)
        else:
            fields["unicode_emoji"] = display_icon

    if mentionable is not MISSING:
        fields["mentionable"] = mentionable

    if name is not MISSING:
        fields["name"] = name

    if colors is not None:
        fields["colors"] = {
            "primary_color"  : colors.get("primary_color", fields["color"]),
            "secondary_color": colors.get("secondary_color"),
            "tertiary_color" : colors.get("tertiary_color"),
        }

    data = await self._state.http.create_role(self.id, reason=reason, **fields)
    return Role(guild=self, data=data, state=self._state)


Guild.create_role = patched_create_role #TODO: undo custom patch



def is_valid_hex(hex_value):
    hex_value = hex_value.replace("#","")
    try:
        int(hex_value, 16)  # Attempt to convert the value to an integer, base 16
        return True
    except ValueError:
        return False


def resize_image_bytes(image_bytes: bytes, size=(100, 100)) -> bytes:
    with Image.open(BytesIO(image_bytes)) as img:
        img = img.convert("RGBA")
        img = img.resize(size, Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

async def log(message, bot, warning=0, dump=None, mention=False):
    guild = bot.get_guild(SERVER_ID)
    if guild is None:
        try:
            guild = await bot.fetch_guild(SERVER_ID)
        except discord.NotFound:
            print(f"Guild with ID {SERVER_ID} not found.")
            return
        except discord.Forbidden:
            print(
                f"Bot does not have permission to access guild with ID {SERVER_ID}."
            )
            return
        except discord.HTTPException as e:
            print(f"Failed to fetch guild: {e}")
            return

    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        try:
            channel = await guild.fetch_channel(LOG_CHANNEL_ID)
        except discord.NotFound:
            print(f"Channel with ID {LOG_CHANNEL_ID} not found.")
            return
        except discord.Forbidden:
            print(
                f"Bot does not have permission to access channel with ID {LOG_CHANNEL_ID}."
            )
            return
        except discord.HTTPException as e:
            print(f"Failed to fetch channel: {e}")
            return
    print(message)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    warning_label = ''
    if warning == 0:
        warning_label = "[INFO]"
    elif warning == 1:
        warning_label = "[WARNING]"
    elif warning == 2:
        warning_label = "[ERROR]"
    if dump:
        bot_admin_m = guild.get_member(bot_admin)
        traceback_str = dump.replace("C:\\SalemVOID", "...\\").replace("C:\\Users\\Max\\AppData\\Local\\Programs", "...\\")
        await channel.send(f"`{warning_label}` `[{now}]` {message}\n```{traceback_str}```\n{bot_admin_m.mention}")
    elif mention:
        bot_admin_m = guild.get_member(bot_admin)
        await channel.send(f"`{warning_label}` `[{now}]` {message}\n{bot_admin_m.mention}")
    else:
        await channel.send(f"`{warning_label}` `[{now}]` {message}")

async def not_void(interaction):
    if interaction.guild.id != SERVER_ID:
        await interaction.followup.send("This command is only available in the VOID server.", ephemeral=True)
        return True
    return False

class Void(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="icon",
                          description="Change your role icon with an emoji, file or image URL. Leave everything blank to reset.")
    @app_commands.describe(label="Text to display when hovered.", emoji="Emoji to use as icon.",
                           image_url="Image URL to use as icon.", image_file="Image file to use as icon.")
    async def icon(self, interaction: discord.Interaction, label: str = None, emoji: str = None, image_url: str = None,
                   image_file: Attachment = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        await log(f"{interaction.user.name} used /icon", self.bot, 0)
        if await not_void(interaction):
            await log(
                f"/icon: returned because the interaction was not in the VOID server (server id: {interaction.guild.id})",
                self.bot, 0)
            return
        for role in interaction.user.roles:
            if role.name.endswith("[icon]"):
                await interaction.user.remove_roles(role)
                await log(f"/icon: Removed role {role.name} from {interaction.user.name}", self.bot)
                if not role.members:
                    await role.delete()
                    await log(f"/icon: Deleted role {role.name} because it has no users anymore", self.bot)
        if not emoji and not image_url and not image_file:
            await interaction.followup.send("✨POOF!✨ Your role icon has VANISHED like tuna at a cat convention!",
                                            ephemeral=True)
            await log("/icon: User didn't provide an icon; existing icon removed successfully", self.bot)
            return
        if image_file and not image_file.content_type.startswith("image/"):
            await interaction.followup.send("Gimme a REAL IMAGE, silly hooman! (PNG or JPG, or the spell FIZZLES!)",
                                            ephemeral=True)
            await log(f"/icon: User tried to upload an image file but the file doesn't seem to be valid (filename: {image_file.filename})", self.bot, 1)
            return

        icon_bytes = None
        unicode_emoji = None

        # Try emoji input
        if emoji:
            await log(f"/icon: User provided an emoji: {emoji}", self.bot, 0)
            try:
                emoji_obj = discord.PartialEmoji.from_str(emoji)
                if emoji_obj.id:
                    # Custom emoji – download its image
                    async with aiohttp.ClientSession() as session:
                        async with session.get(str(emoji_obj.url)) as resp:
                            if resp.status != 200:
                                await interaction.followup.send(
                                    f"WHOOPSIES—couldn’t snatch the emoji image! Maybe try uploading the image instead? (status {resp.status})",
                                    ephemeral=True)
                                return
                            icon_bytes = await resp.read()
                else:
                    unicode_emoji = str(emoji_obj)
            except Exception as e:
                await interaction.followup.send(
                    "That emoji is as FAKE as a Day 1 alliance! Use format `:emoji:` or face my wrath.", ephemeral=True)
                await log(f"/icon: Something went wrong with emoji input: {e}", self.bot, 1)
                return


        elif image_url:
            await log(f"/icon: User provided an image URL: <{image_url}>", self.bot, 0)
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; DiscordBot/1.0; +https://discord.com)"
                }
                connector = aiohttp.TCPConnector(limit_per_host=2)
                async with aiohttp.ClientSession(headers=headers, connector=connector) as session:
                    async with session.get(image_url) as resp:
                        print(f"🔍 Fetching image from: {image_url}")
                        print(f"📦 Status: {resp.status}")
                        print(f"📑 Headers: {dict(resp.headers)}")

                        if resp.status != 200:
                            await interaction.followup.send(
                                f"I TRIED to nab the image from {image_url}, but even my nine lives couldn’t manage that chaos! Maybe try uploading instead? (status {resp.status})",
                                ephemeral=True
                            )
                            await log(f"/icon: User provided image URL but something went wrong trying to access the URL (URL <{image_url}>, status code {resp.status})", self.bot, 1)
                            return

                        img_data = await resp.read()

                icon_bytes = resize_image_bytes(img_data)

            except Exception as e:
                print(f"Exception while downloading image: {e}")
                import traceback  # TODO: why doesn't this work if traceback is outside? lmao
                traceback.print_exc()

                await interaction.followup.send(f"UH, is this URL possessed? Check it and try again! {image_url}",
                                                ephemeral=True)
                await log(f"/icon: Exception while downloading image: {e}", self.bot, warning=2, dump=traceback.print_exc(), mention=True)
                return

        elif image_file:
            await log(f"/icon: User provided an image file", self.bot, 0)
            try:
                image_bytes = await image_file.read()
                icon_bytes = resize_image_bytes(image_bytes)
            except Exception as e:
                await interaction.followup.send(
                    "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                    ephemeral=True)
                await log(f"/icon: Something went wrong with the image file: {e}", self.bot, warning=1)
                return

        try:
            if label:
                name = f"{label} [icon]"
            else:
                name = "[icon]"
            kwargs = {
                "name"       : f"{name}",
                "mentionable": False,
            }

            if unicode_emoji:
                kwargs["display_icon"] = unicode_emoji
            elif icon_bytes:
                kwargs["display_icon"] = icon_bytes

            # Role creation
            r = await interaction.guild.create_role(**kwargs)
            await log(f"/icon: Successfully created role {r.name}", self.bot, 0)
            # Move role above bot’s highest role
            highest_bot_role_position = 0
            highest_bot_role = None
            bot_member = interaction.guild.get_member(self.bot.user.id)
            for role in bot_member.roles:
                if role.position > highest_bot_role_position:
                    highest_bot_role_position = role.position
                    highest_bot_role = role
            await r.move(above=highest_bot_role)
            await log(f"/icon: Moved role {r.name} to highest possible position", self.bot, 0)

            # Apply to user
            await interaction.user.add_roles(r)
            await interaction.followup.send("YAAAASSS! Your new role icon is ON POINT! (≧▽≦)✨", ephemeral=True)
            await log(f"/icon: Added role {r.name} to {interaction.user.name}", self.bot, 0)

        except Exception as e:
            await interaction.followup.send(
                "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)", ephemeral=True)
            import traceback  # TODO: why doesn't this work if traceback is outside? lmao
            traceback.print_exc()
            await log(f"/icon: Something went wrong while creating the icon role: {e}", self.bot, warning=2, dump=traceback.print_exc(), mention=True)
            return
        await log(f"/icon: Done", self.bot)
        return

    @app_commands.command(name="color", description="Change your name color.")
    @app_commands.describe(
        color="Color in hexadecimal (leave blank to revert to default, OR \"holographic\" for the holographic variant.",
        second_color="Color in hexadecimal (for gradient only, leave blank to use a solid color.)")
    async def color(self, interaction: discord.Interaction, color: str = None, second_color: str = None):
        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            await log(f"{interaction.user.name} used /color: {color} | {second_color}", self.bot, 0)
            if await not_void(interaction):
                await log(f"/color: returned because the interaction was not in the VOID server (server id: {interaction.guild.id})", self.bot, 0)
                return
            if (color and not is_valid_hex(color)) or (second_color and not is_valid_hex(second_color)):
                await interaction.followup.send(
                    "HEX CODE ONLY, darling! If it ain’t something like #FF69B4, I can’t conjure that color!",
                    ephemeral=True)
                await log(
                    f"{interaction.user.name} tried to use /color, but one of the hex codes is not valid: {color}, {second_color}",
                    self.bot, 1)
                return
            for role in interaction.user.roles:
                if role.name.startswith("#"):
                    await interaction.user.remove_roles(role)
                    await log(f"/color: Removed role {role.name} from {interaction.user.name}", self.bot, 0)
                    if not role.members:
                        await log(f"/color: Deleted role {role.name} because it has no users anymore", self.bot, 0)
                        await role.delete()
            if not color:
                await log(f"/color: User provided no color; cleared existing colors successfully", self.bot, 0)
                await interaction.followup.send("Your color? VANQUISHED like the smallest tribe in a swap.", ephemeral=True)
                return
            color = color.replace("#", "")
            if second_color:
                second_color = second_color.replace("#", "")
            if "holo" in color.lower():
                holo_role = discord.utils.get(interaction.guild.roles, name="#holographic")
                await interaction.user.add_roles(holo_role)
                await log(f"/color: Added #holographic to {interaction.user.name}", self.bot, 0)
            else:
                discord_color = discord.Color(int(color, 16))
                if second_color:
                    second_discord_color = discord.Color(int(second_color, 16))
                try:
                    await log(f"/color: Trying to create color role...", self.bot, 0)
                    if second_color: #TODO: update to use non overwritten version
                        r = await interaction.guild.create_role(name="#" + color.upper() + " to #" + second_color.upper(),
                                                                color=discord_color,
                                                                colors={"primary_color"  : discord_color.value,
                                                                        "secondary_color": second_discord_color.value})
                    else:
                        r = await interaction.guild.create_role(name="#" + color.upper(), color=discord_color)
                    await log(f"/color: Successfully created role {r.name}", self.bot, 0)
                    highest_bot_role_position = 0
                    highest_bot_role = None
                    bot_member = interaction.guild.get_member(self.bot.user.id)
                    for role in bot_member.roles:
                        if role.position > highest_bot_role_position:
                            highest_bot_role_position = role.position
                            highest_bot_role = role
                    await r.move(above=highest_bot_role)
                    await log(f"/color: Moved role {r.name} to highest possible position", self.bot, 0)
                    await interaction.user.add_roles(r)
                    await log(f"/color: Added role {r.name} to {interaction.user.name}", self.bot, 0)
                except Exception as e:
                    await interaction.followup.send(
                        "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                        ephemeral=True)
                    await log(f"An error occurred in color(): {e}", self.bot, 2, traceback.format_exc(), True)
                    traceback.print_exc()
            await interaction.followup.send(f"SLAAAY, new color! It’s giving ~Final Tribal glow up!~", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                ephemeral=True)
            await log(f"An error occurred in color(): {e}", self.bot, 2, traceback.format_exc(), True)
            traceback.print_exc()
        await log(f"/color: Done", self.bot, 0)
        return

'''
    @app_commands.command(name="upload", description="Upload a custom emoji, sticker, or soundboard to the server.")
    async def upload(self, interaction: discord.Interaction, name: str, type: Literal['Emoji', 'Sticker', 'Soundboard'], file: Attachment):
        GENERAL_CHANNEL_ID = 713863517786079366 # TODO: don't hardcode lol
        GENERAL_CHANNEL = await interaction.guild.fetch_channel(GENERAL_CHANNEL_ID)
        # TODO: keep track of soft limits
        # TODO: test, validate input
        await log(f"{interaction.user.name} used /upload", self.bot, 0)
        guild = interaction.guild
        if await not_void(interaction):
            await log(f"{interaction.user.name} tried to use upload outside of the VOID server.", self.bot, 1)
            return
        if type == 'Emoji':
            if not file.content_type.startswith("image/"):
                await interaction.followup.send("Upload an image file!", ephemeral=True)
                await log(f"/upload: User selected emoji but didn't provide an image.", self.bot, 0)
                return
            try:
                image_bytes = await file.read()
                icon_bytes = resize_image_bytes(image_bytes)
                print("Got image bytes, trying to upload...")
                await guild.create_custom_emoji(name=name, image=icon_bytes)
                print("Uploaded image!")
                await interaction.followup.send(f"Uploaded emoji!", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(
                    "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                    ephemeral=True)
                await log(f"/upload: Something went wrong with the emoji image file: {e}", self.bot, warning=1)
                return
        elif type == 'Sticker': # TODO: it dont work
            stickers = await guild.fetch_stickers()
            if len(stickers) >= guild.sticker_limit:
                await interaction.followup.send("This server has reached its sticker limit.", ephemeral=True)
                return
            if not file.content_type.startswith("image/"):
                await interaction.followup.send("Upload an image file!", ephemeral=True)
                await log(f"/upload: User selected sticker but didn't provide an image.", self.bot, 0)
                return
            try:
                image_bytes = await file.read()
                print("Got image bytes, trying to convert...")
                d_file = discord.File(BytesIO(image_bytes), filename=file.filename)
                print("Got file, trying to upload...") # stuck here
                await guild.create_sticker(name=name, file=d_file, description=f"Uploaded by {interaction.user.name}", emoji="✨")
                await interaction.followup.send(f"Uploaded sticker!", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(
                    "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                    ephemeral=True)
                await log(f"/upload: Something went wrong with the sticker upload: {e}", self.bot, warning=1)
                return
        elif type == 'Soundboard': # TODO: it dont work
            if not file.content_type.startswith("audio/"):
                await interaction.followup.send("Upload an audio file!", ephemeral=True)
                await log(f"/upload: User selected sticker but didn't provide an audio file.", self.bot, 0)
                return
            try:
                file_bytes = await file.read()
                print("Got file bytes, trying to upload...")
                await guild.create_soundboard_sound(name=name, sound=file_bytes, volume=50, emoji="✨") # stuck here
                await interaction.followup.send(f"Uploaded soundboard!", ephemeral=True)
                return
            except Exception as e:
                await interaction.followup.send(
                    "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                    ephemeral=True)
                await log(f"/upload: Something went wrong with the soundboard: {e}", self.bot, warning=1)
                return
        else:
            await interaction.followup.send(
                "Something went WRONG! Spam Max’s DMs! (Or just try again. Maybe offer tuna for luck?)",
                ephemeral=True)
            await log(f"/upload: User didn't provide type (somehow?)", self.bot, warning=2, mention=True)
            return
        #await GENERAL_CHANNEL.send(f"This newest thingy brought to you by: {interaction.user.mention}! YAY!!! ~(≧▽≦)~✨")
        #return
'''

async def setup(bot):
    await bot.add_cog(Void(bot))
