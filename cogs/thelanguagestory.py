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

        await self.start_ls_game_callback(author)


    async def start_ls_game_callback(self, member: discord.Member) -> None:
        """ Starts the Language Story game.
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
            # Gets a random language audio
            story = await self.get_random_story()

            # Plays the song
            if not voice_client.is_playing():
                audio_source = f"{self.root_path}/Stories/{story['name']}/audio.mp3"

                embed = discord.Embed(
                    title=f"__`The Story starts now! ({story['name']})`__",
                    description=f"Text:\n\n{story['text']}",
                    color=discord.Color.green()
                )
                view: discord.ui.View = ChooseOptionView(member, story['options'])
                msg = await self.txt.send(content="\u200b", embed=embed, view=view)
                await utils.audio(self.client, voice_client.channel, member, audio_path=audio_source)
                print('am I being ran?')
                # voice_client.play(audio_source, after=lambda e: self.client.loop.create_task(self.get_choice_response(member, story)))
                print('teste')
                voice_client.play(audio_source, after=lambda e: view.stop())
                print('teste2')
                view.stop()
                print('teste3')
                await view.wait()
                print('teste4')
                utils.disable_buttons(view, False)
                await msg.edit(view=view)
                print('kekekek')

        else:
            # (to-do) send a message to a specific channel
            await self.txt.send("**The player left the voice channel, so it's game over!**")


    async def get_random_story(self) -> List[Any]:
        """ Gets a random story to play """

        story: Dict[str, str] = {
            'name': None,
            'text': None,
            'audio': None,
            'options': []
        }

        while True:
            story_name = choice(os.listdir(f"{self.root_path}/Stories/"))
            if story_name not in self.stories_played:
                with open(f"{self.root_path}/Stories/{story_name}/text.txt", encoding="utf-8") as f:
                    text = f.read()

                story['name'] = story_name
                story['text'] = text
                story['audio'] = f"{self.root_path}/Stories/{story_name}/audio.mp3"
                option_path: str = f"{self.root_path}/Stories/{story_name}"
                story['options'] = [
                    file for file in os.listdir(option_path)
                    if os.path.isdir(f"{option_path}/{file}")
                ]
                break
            continue

        return story


    async def get_choice_response(self, member: discord.Member, story: Dict[str, str]) -> None:
        """ Gets a choice response from the user.
        :param member: The member to get the response from.
        :param story: The story data. """

        pass

def setup(client) -> None:
    client.add_cog(TheLanguageStory(client))