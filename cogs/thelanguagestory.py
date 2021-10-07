import discord
from discord.ext import commands
from typing import Optional
import shutil
import os
from external_cons import the_drive

class TheLanguageStory(commands.Cog):
    """ Category for TheLanguageStory game. """

    def __init__(self, client: commands.Bot) -> None:
        self.client = client


    @commands.Cog.listener()
    async def on_ready(self) -> None:
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


    
def setup(client) -> None:
    client.add_cog(TheLanguageStory(client))