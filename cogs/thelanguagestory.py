import discord
from discord.ext import commands
from external_cons import the_drive
import shutil
import os

from extra import utils
from extra.view import ChooseOptionView

import asyncio
from typing import Optional, List, Any, Dict
from random import choice

language_jungle_txt_id = int(os.getenv('LANGUAGE_JUNGLE_TXT_ID'))
language_jungle_vc_id = int(os.getenv('LANGUAGE_JUNGLE_VC_ID'))

class TheLanguageStory(commands.Cog):
    """ Category for TheLanguageStory game. """

    def __init__(self, client: commands.Bot) -> None:
        self.client = client
        self.stories_played: List[str] = []
        self.root_path: str = './language_story'
        self.round: int = 0
        self.story_name: str = None


    @commands.Cog.listener()
    async def on_ready(self) -> None:

        self.txt = await self.client.fetch_channel(language_jungle_txt_id)
        self.vc = await self.client.fetch_channel(language_jungle_vc_id)
        print("TheLanguageStory cog is online!")


    # Downloads all content for the Language Jungle game
    @commands.command(aliases=['sau'])
    @commands.has_permissions(administrator=True)
    async def story_audio_update(self, ctx: Optional[commands.Context] = None, rall: str = 'no') -> None:
        """ Downloads all audios from the GoogleDrive for The Language Story game
        and stores in the bot's folder.
        :param ctx: The context of the command. [Optional]
        :param rall: Whether the it should remove all folders before downloading files. """

        if rall.lower() == 'yes':
            try:
                shutil.rmtree('./language_story')
            except Exception:
                pass

        all_folders = {
            "Stories": "1MgRUwGW8Iw-ZROmqq0sYHcikwof2VG-3"
        }
        categories = ['Stories']
        for category in categories:
            try:
                os.makedirs(f'./language_story/{category}')
                print(f"{category} folder made!")
            except FileExistsError:
                pass

        drive = await the_drive()

        for folder, folder_id in all_folders.items():

            await self.download_recursively(drive, 'language_story', folder, folder_id)

        if ctx:
            await ctx.send("**Download update complete!**")

    async def download_recursively(self, drive, path: str, folder: str, folder_id: int) -> None:

        files = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder_id}).GetList()
        download_path = f'./{path}/{folder}'

        for file in files:
            try:
                #print(f"\033[34mItem name:\033[m \033[33m{file['title']:<35}\033[m | \033[34mID: \033[m\033[33m{file['id']}\033[m")
                output_file = os.path.join(download_path, file['title'])
                temp_file = drive.CreateFile({'id': file['id']})
                temp_file.GetContentFile(output_file)
                #print("File downloaded!")
            except Exception as error:
                new_category = file['title']
                try:
                    new_download_path = f"{download_path}/{new_category}"
                    os.makedirs(new_download_path)
                    print(f"{new_category} folder made!")
                except FileExistsError:
                    pass
                else:
                    await self.download_recursively(drive, download_path, new_category, file['id'])


    @commands.command(hidden=True, aliases=['story'])
    @commands.is_owner()
    async def start_ls_game_command(self, ctx) -> None:
        """ Starts the Language Story game. """

        author = ctx.author

        story_path: str = f"{self.root_path}/Stories"
        # Gets a random language audio
        await self.reset_bot_status()
        await self.start_ls_game_callback(story_path, author)


    async def start_ls_game_callback(self, story_path: str, member: discord.Member) -> None:
        """ Starts the Language Story game..
        :param story_path: The path of the current or next audio to be played.
        :param member: The member who started the game. """

        server_bot: discord.Member = member.guild.get_member(self.client.user.id)
        if (bot_voice := server_bot.voice) and bot_voice.mute:
            await server_bot.edit(mute=False)
        
        voice = member.voice
        voice_client = member.guild.voice_client

        voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

        # Checks if the bot is in a voice channel
        if not voice_client:
            await voice.channel.connect()
            await asyncio.sleep(1)
            voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

        # Checks if the bot is in the same voice channel that the user
        if voice and voice.channel == voice_client.channel:

            # Plays the song
            if not voice_client.is_playing():
            
                self.round += 1

                if self.round == 1:
                    story = await self.get_random_story(story_path, True)
                    story_path = f"{story_path}/{story['name']}"
                    text: str = story['text']
                else:
                    story = await self.get_random_story(story_path)
                    text: str = await self.get_new_text(story_path)

                embed = discord.Embed(
                    title=f"__`The Story starts now! ({story['name']})`__",
                    description=f"Text:\n\n{text}",
                    color=discord.Color.green()
                )
                view: discord.ui.View = ChooseOptionView(cog=self, member=member, story=story, story_path=story_path)
                msg = await self.txt.send(content="\u200b", embed=embed, view=view)
                voice_client.play(discord.FFmpegPCMAudio(f"{story_path}/audio.mp3"), after=lambda e: self.client.loop.create_task(self.enable_answers(msg, view)))

        else:
            # (to-do) send a message to a specific channel
            await self.txt.send("**The player left the voice channel, so it's game over!**")

    async def enable_answers(self, message: discord.Message, view: discord.ui.View) -> None:
        """ Enables the buttons from the view, so the user can continue the game. """

        await utils.disable_buttons(view, False)
        await message.edit(view=view)

    async def get_new_text(self, story_path: str) -> str:
        """ Gets a new text to display.
        :param story_path: The path from which to get the text. """

        with open(f"{story_path}/text.txt", 'r', encoding="utf-8") as f:
            text: str = f.read()

        return text


    async def get_random_story(self, folder: str, random: bool = False) -> List[Any]:
        """ Gets a random story to play.
        :param folder: The folder from which to start looking. """

        story: Dict[str, str] = {
            'name': None,
            'text': None,
            'audio': None,
            'options': []
        }

        while True:

            search_path: str = folder
            if random:
                story_name = choice(os.listdir(f"{self.root_path}/Stories/"))
                search_path = f"{folder}/{story_name}"
                if story_name in self.stories_played:
                    continue
                self.story_name = story_name
                
                story['name'] = story_name
                story['audio'] = f"{folder}/{story_name}/audio.mp3"
                option_path: str = f"{folder}/{story_name}"
                story['options'] = [
                    file for file in os.listdir(option_path)
                    if os.path.isdir(f"{option_path}/{file}")
                ]
            
            else:
                story_name = self.story_name
                story['name'] = story_name
                story['audio'] = f"{folder}/audio.mp3"
                option_path: str = f"{folder}/"
                story['options'] = [
                    file for file in os.listdir(option_path)
                    if os.path.isdir(f"{option_path}/{file}")
                ]

            with open(f"{search_path}/text.txt", encoding="utf-8") as f:
                text = f.read()
                story['text'] = text

            break

        return story


    async def get_choice_response(self, member: discord.Member, story: Dict[str, str]) -> None:
        """ Gets a choice response from the user.
        :param member: The member to get the response from.
        :param story: The story data. """

        pass

    async def reset_bot_status(self) -> None:
        """ Resets the bot's status to its original state. """

        self.stories_played: List[str] = []
        self.root_path: str = './language_story'
        self.round: int = 0
        self.story_name: str = None

def setup(client) -> None:
    client.add_cog(TheLanguageStory(client))