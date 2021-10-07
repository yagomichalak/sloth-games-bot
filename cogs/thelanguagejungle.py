import discord
from extra import utils
from discord.ext import commands, tasks
from extra.view import TheLanguageJungleMultiplayerView

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from mysqldb import the_database
from external_cons import the_drive

import os
import shutil
import random
import asyncio
import aiohttp

from typing import List, Optional, Callable, Any, Union
from PIL import Image, ImageFont, ImageDraw
from time import time
from io import BytesIO

language_jungle_txt_id = int(os.getenv('LANGUAGE_JUNGLE_TXT_ID'))
language_jungle_vc_id = int(os.getenv('LANGUAGE_JUNGLE_VC_ID'))
cosmos_id = int(os.getenv('COSMOS_ID'))
mod_role_id = int(os.getenv('MOD_ROLE_ID'))
server_id = int(os.getenv('SERVER_ID'))

class TheLanguageJungle(commands.Cog):
	""" Category for game related commands. """

	def __init__(self, client: commands.Bot) -> None:
		self.client = client
		self.session = aiohttp.ClientSession()
		self.round = 0
		self.lives = 3
		self.wrong_answers = 0
		self.right_answers = 0
		self.active = False
		self.questions = {}
		self.member_id = None
		self.reproduced_languages = []
		self.ready = False
		self.status = 'normal'
		self.start_ts = None
		# Multiplayer attributes
		self.multiplayer = {
		'teams': {
			'blue': [[], 0],
			'red': [[], 0]
			},
		'message_id': None
		}
		self.embed = None
		self.multiplayer_active = False
		self.round_active = False
		self.current_answer = None
		self.setting_up = False
		
	@commands.Cog.listener()
	async def on_ready(self) -> None:
		print('Games cog is online!')
		try:
			self.change_status.start()
		except:
			pass

		self.txt = await self.client.fetch_channel(language_jungle_txt_id)
		self.vc = await self.client.fetch_channel(language_jungle_vc_id)
		self.ready = True
		await self.txt.send("**I'm ready to play!**")

	@commands.Cog.listener()
	async def on_message(self, message) -> None:
		""" Handles messages. """

		member = message.author
		# Checks if it's a bot message
		if member.bot:
			return

		# Checks if a multiplayer game session is happening
		if not self.multiplayer_active:
			return

		# Check if it's the Language Jungle channel
		channel = message.channel
		if channel.id != self.txt.id:
			return
		
		# Checks if it's an active player
		red = self.multiplayer['teams']['red'][0]
		blue = self.multiplayer['teams']['blue'][0]
		if member.id not in red + blue:
			return

		# Checks if the round is active
		if self.round_active:

			# If so, checks if the user answer was right
			await self.get_multiplayer_language_response_before(
				self.multiplayer['teams'], self.current_answer, message)

	# @commands.Cog.listener()
	# async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
	# 	""" Checks whether team members are still in the voice channel. """

	# 	if member.bot:
	# 		return

	# 	# Check voice states
	# 	if before.mute != after.mute:
	# 		return
	# 	if before.deaf != before.deaf:
	# 		return
	# 	if before.self_mute != after.self_mute:
	# 		return
	# 	if before.self_deaf != after.self_deaf:
	# 		return
	# 	if before.self_stream != after.self_stream:
	# 		return
	# 	if before.self_video != after.self_video:
	# 		return
		
	# 	if self.setting_up:
			
	# 		# Checks if their previous state was the TLJ VC
	# 		if before.channel and before.channel.id == self.vc.id:

	# 			# Checks if the current state is not the TLJ vc anymore
	# 			if not after.channel or after.channel.id != self.vc.id:

	# 				# Checks if user was a red or blue team member.
	# 				blue_team = self.multiplayer['teams']['blue'][0]
	# 				red_team = self.multiplayer['teams']['red'][0]

	# 				if member.id in blue_team:
	# 					try:							
	# 						blue_team.remove(member.id)
	# 					except:
	# 						pass
	# 					mid = self.multiplayer['message_id']
	# 					msg = await self.txt.fetch_message(mid)
	# 					await self.update_multiplayer_message(msg)

	# 				elif member.id in red_team:
	# 					try:						
	# 						red_team.remove(member.id)
	# 					except:
	# 						pass
	# 					mid = self.multiplayer['message_id']
	# 					msg = await self.txt.fetch_message(mid)
	# 					await self.update_multiplayer_message(msg)

	async def update_multiplayer_message(self, msg: discord.Message) -> None:
		""" Updates the multiplayer message.
		:param msg: The message to update. """

		self.embed.clear_fields()
		self.embed.add_field(name='🔴 __Red team__', value=f"{len(self.multiplayer['teams']['red'][0])}/5 players.", inline=True)
		self.embed.add_field(name='🔵 __Blue team__', value=f"{len(self.multiplayer['teams']['blue'][0])}/5 players.", inline=True)
		await msg.edit(embed=self.embed)

	# Members status update
	@tasks.loop(seconds=10)
	async def change_status(self) -> None:
		""" Changes the bot's activity status when someone is playing with the bot. """

		if self.active:
			await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f'with someone.'))
		else:
			await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'new players.'))

	# Downloads all content for the Language Jungle game
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def audio_update(self, ctx: Optional[commands.Context] = None, rall: str = 'no') -> None:
		""" Downloads all shop images from the GoogleDrive and stores in the bot's folder.
		:param ctx: The context of the command. [Optional]
		:param rall: Whether the it should remove all folders before downloading files. """

		if rall.lower() == 'yes':
			try:
				shutil.rmtree('./language_jungle')
			except Exception:
				pass

		all_folders = {
			"Graphic": "1kfBh-OKe27CMOTCM2KL8mmELVMKo4koe",
			"Speech": "16NGDpT4pX6JqvCbgMLFuLRJudq40FJNi",
			"SFX": "1aI0ui6L9uVo8RorNkXjTRUWi9hIaXdul"
		}
		categories = ['Graphic', 'Speech', 'SFX']
		for category in categories:
			try:
				os.makedirs(f'./language_jungle/{category}')
				print(f"{category} folder made!")
			except FileExistsError:
				pass

		drive = await the_drive()

		for folder, folder_id in all_folders.items():
			files = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder_id}).GetList()
			#print(f"\033[35mCategory:\033[m {folder}")
			download_path = f'./language_jungle/{folder}'
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
						files = drive.ListFile({'q': "'%s' in parents and trashed=false" % file['id']}).GetList()
						#print(f"\033[35mCategory:\033[m {folder}")
						download_path = f'./language_jungle/{folder}'
						for file in files:
							try:
								output_file = os.path.join(new_download_path, file['title'])
								temp_file = drive.CreateFile({'id': file['id']})
								temp_file.GetContentFile(output_file)
							except Exception:
								print('bah!')
								pass

		if ctx:
			await ctx.send("**Download update complete!**")

	# Google Drive commands
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def shop_update(self, ctx: Optional[commands.Context] = None, rall: str = 'no') -> None:
		""" (ADM) Downloads all shop images from the Google Drive.
		:param ctx: The context of the command. [Optional]
		:param rall: Whether the it should remove all folders before downloading files. """

		if ctx:
			await ctx.message.delete()

		if rall.lower() == 'yes':
			try:
				shutil.rmtree('./sloth_custom_images')
			except Exception:
				pass

		all_folders = {"background": "1V8l391o3-vsF9H2Jv24lDmy8e2erlHyI",
					   "sloth": "16DB_lNrnrmvxu2E7RGu01rQGQk7z-zRy",
					   "body": "1jYvG3vhL32-A0qDYn6lEG6fk_GKYDXD7",
					   "hand": "1ggW3SDVzTSY5b8ybPimCsRWGSCaOBM8d",
					   "hud": "1-U6oOphdMNMPhPAjRJxJ2E6KIzIbewEh",
					   "badge": "1k8NRfwwLzIY5ALK5bUObAcrKr_eUlfjd",
					   "foot": "1Frfra1tQ49dKM6Dg4DIbrfYbtXadv9zj",
					   "head": "1Y9kSOayw4NDehbqfmvPXKZLrXnIjeblP"
					   }

		categories = ['background', 'sloth', 'body', 'hand', 'hud', 'badge', 'foot', 'head']
		for category in categories:
			try:
				os.makedirs(f'./sloth_custom_images/{category}')
				print(f"{category} folder made!")
			except FileExistsError:
				pass

		for folder, folder_id in all_folders.items():
			files = drive.ListFile({'q': "'%s' in parents and trashed=false" % folder_id}).GetList()
			download_path = f'./sloth_custom_images/{folder}'
			for file in files:
				isFile = os.path.isfile(f"{download_path}/{file['title']}")
				# print(isFile)
				if not isFile:
					# print(f"\033[34mItem name:\033[m \033[33m{file['title']:<35}\033[m | \033[34mID: \033[m\033[33m{file['id']}\033[m")
					output_file = os.path.join(download_path, file['title'])
					temp_file = drive.CreateFile({'id': file['id']})
					temp_file.GetContentFile(output_file)
					# print(f"File '{file['title']}' downloaded!")

		if ctx:
			return await ctx.send("**Download update is done!**", delete_after=5)

	# Leaves the channel
	@commands.command()
	async def stop(self, ctx: commands.Context) -> None:
		""" Stops the game. """

		author = ctx.author

		if not self.active:
			return await ctx.send(f"**{author.mention}, I'm not even playing yet!**")

		if self.multiplayer_active:
			if await utils.is_allowed([mod_role_id]).predicate(ctx) or await utils.is_allowed_members([287746936587419648]).predicate(ctx):
				await self.reset_bot_status()
				guild = ctx.message.guild
				voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
				try:
					self.status = 'stop'
					voice_client.stop()
				except Exception as e:
					pass
				return await ctx.send("**Multiplayer session ended!**")
			return await ctx.send(f"**{author.mention}, you cannot end a multiplayer session just like that!**")

		if self.member_id == author.id or await utils.is_allowed([mod_role_id]).predicate(ctx) or await utils.is_allowed_members([287746936587419648]).predicate(ctx):
			await self.reset_bot_status()
			guild = ctx.message.guild
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
			if voice_client and voice_client.is_playing():
				self.status = 'stop'
				voice_client.stop()
			await ctx.send("**Session ended!**")
		else:
			return await ctx.send(f"{author.mention}, you're not the one who's playing, nor is a staff member")

	async def stop_round(self, guild):
		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
		if voice_client and voice_client.is_playing():
			self.status = 'stop'
			voice_client.stop()

	@commands.command(name="play_singleplayer_language", aliases=['language', 'language_jungle', 'jungle', 'lj', 'play', 'p'])
	async def _play_singleplayer_language_command(self, ctx: commands.Context) -> None:
		""" Plays the Language Jungle. (Singleplayer) """

		await self._play_singleplayer_language_callback(ctx)

	async def _play_singleplayer_language_callback(self, ctx: Union[commands.Context, discord.ApplicationContext]) -> None:
		""" Plays the Language Jungle. (Singleplayer)(Callback) """

		member = ctx.author

		# Sorts out the messageable object
		answer: discord.PartialMessageable = None
		if isinstance(ctx, commands.Context):
			answer = ctx.send
		else:
			answer = ctx.respond

		the_txt = self.txt
		if ctx.channel.id != language_jungle_txt_id:
			return await answer(f"**{member.mention}, you can only use this command in {the_txt.mention}!**")

		# Checks if the user is in a voice channel
		voice = ctx.author.voice
		if voice is None:
			return await answer(f"**{member.mention}, you're not in the voice channel**")

		if voice.channel.id != language_jungle_vc_id:
			return await answer(f"**{member.mention}, you're not in the `Language Jungle` voice channel!**")

		if not self.ready:
			return await answer("**I'm still downloading the audios, wait a bit!**")

		if self.active:
			return await answer(f"**{member.mention}, someone is already playing!**")

		self.active = True
		self.member_id = member.id
		self.start_ts = time()
		await answer("__**`Singleplayer`**__")
		await self.start_game(member, the_txt)

	async def start_game(self, member: discord.Member, the_txt: discord.TextChannel) -> None:
		""" Starts the Language Jungle game.
		:param member: The member who started the game.
		:param the_txt: The game's main text channel. """

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
			path, language, audio = self.get_random_language()
			# Plays the song
			if not voice_client.is_playing():
				audio_source = discord.FFmpegPCMAudio(path)

				self.round += 1
				embed = discord.Embed(
					title=f"__`ROUND {self.round}`__",
					description="The round starts now.",
					color=discord.Color.green()
				)
				await the_txt.send(embed=embed)
				voice_client.play(audio_source, after=lambda e: self.client.loop.create_task(self.get_language_response(member, the_txt, language)))

		else:
			# (to-do) send a message to a specific channel
			await the_txt.send("**The player left the voice channel, so it's game over!**")
			await self.reset_bot_status()

	@commands.command(name="play_multiplayer_language", aliases=['pmp', 'mp', 'multiplayer', 'zugumupu'])
	async def _play_multiplayer_language_command(self, ctx: commands.Context) -> None:
		""" Plays the Language Jungle. (Multiplayer) """

		await self._play_multiplayer_language_callback(ctx)

	async def _play_multiplayer_language_callback(self, ctx: commands.Context) -> None:
		""" Plays the Language Jungle. (Multiplayer)(Callback) """

		# Sorts out the messageable object
		answer: discord.PartialMessageable = None
		if isinstance(ctx, commands.Context):
			answer = ctx.send
		else:
			answer = ctx.respond

		member = ctx.author

		the_txt = self.txt
		if ctx.channel.id != language_jungle_txt_id:
			return await answer(f"**{member.mention}, you can only use this command in {the_txt.mention}!**")

		# Checks if the user is in a voice channel
		voice = ctx.author.voice
		if voice is None:
			return await answer(f"**{member.mention}, you're not in the voice channel**")

		if voice.channel.id != language_jungle_vc_id:
			return await answer(f"**{member.mention}, you're not in the `Language Jungle` voice channel!**")

		if not self.ready:
			return await answer("**I'm still downloading the audios, wait a bit!**")

		if self.active:
			return await answer(f"**{member.mention}, someone is already playing!**")

		await self.reset_bot_status()
		self.active = True
		self.multiplayer_active = True
		self.setting_up = True

		embed = discord.Embed(
			title="Setting up the Game...",
			description="""
			```Click on the buttons of this message in order to participate in the multiplayer game session!```
			Click on 🔴 to enter red team;
			Click on 🔵 to enter the blue team.""",
			color=member.color,
			)
		embed.add_field(name='🔴 __Red team__', value=f"{len(self.multiplayer['teams']['red'][0])}/5 players.", inline=True)
		embed.add_field(name='🔵 __Blue team__', value=f"{len(self.multiplayer['teams']['blue'][0])}/5 players.", inline=True)

		wait_a_minutes: List[str] = [
			'https://media1.tenor.com/images/81e68cca293ebd7656deec2bc582ef1c/tenor.gif?itemid=14484132',
			'https://c.tenor.com/gPhmuKT6BBQAAAAS/wait-a-minute-steve-harvey.gif',
			'https://c.tenor.com/Gjgw3iUuqpwAAAAC/the-fresh-prince-of-bel-air-wait-a-minute.gif',
			'https://c.tenor.com/EYchkttDBEEAAAAS/wait-a-minute-wait.gif',
			'https://c.tenor.com/dx7g9bNGnEoAAAAS/wait-just-a-minute-hold-up.gif',
			'https://c.tenor.com/PqwOTw0bdf8AAAAS/wait-a-minute-chuck-nice.gif',
			'https://c.tenor.com/pGOjJeJgNlkAAAAC/wait-a-minute-wendy-testaburger.gif',
			'https://c.tenor.com/SBwwnEZ-I3cAAAAS/wait-a-minute-chuck-nice.gif',
			'https://c.tenor.com/DJtANMTd0ioAAAAS/wait-a-minute-wait.gif',
			'https://c.tenor.com/l5B-rrbKjL8AAAAS/wait-a-minute-betty-white.gif',
			'https://c.tenor.com/E3-YxwCts9sAAAAS/filthy-frank-wait.gif',
			'https://c.tenor.com/A5U44Ldj2x4AAAAC/wait-a-minute-steve-terreberry.gif',
			'https://c.tenor.com/ZQfQ5cyrgkYAAAAC/wait-a-minute-afkayt.gif',
			'https://c.tenor.com/xGeomYpj79kAAAAd/wait-a-minute-stop.gif',
			'https://c.tenor.com/87F0ABbdLLkAAAAC/wait-a-minute-imani.gif',
			'https://c.tenor.com/ixYJgUSNZqIAAAAd/wait-a-minute-anthony-mackie.gif',
			'https://c.tenor.com/0YTByZ5DkNwAAAAC/wait-a-minute-linda-stotch.gif',
			'https://c.tenor.com/nMl2o2BtaX8AAAAC/jknews-jkfilms.gif',
			'https://c.tenor.com/fPy3Gx4ePzkAAAAC/dragons-den-wait-a-minute.gif',
			'https://c.tenor.com/wNT-jBj0R5UAAAAC/hey-wait-a-minute-eric-cartman.gif',
			'https://c.tenor.com/V0i-8GUL0RIAAAAd/oh-wait-a-minute-now-ella-payne.gif',
			'https://c.tenor.com/ndo6dU7NRnkAAAAd/well-wait-a-minute-wait-a-minute.gif',
			'https://c.tenor.com/w3lNgIB6OgsAAAAC/wait-a-minute-kevin-hart.gif',
			'https://c.tenor.com/dUNNfdpuzhQAAAAC/trump-wait-a-minute.gif',
			'https://c.tenor.com/R2RzLheXamwAAAAC/cbb2-cbbus2.gif',
			'https://c.tenor.com/O6mtr_vCS0sAAAAC/oh-wait-a-minute-maggie-amato.gif',
			'https://c.tenor.com/W-p2KNbKg_kAAAAC/wait-a-minute-hold-up.gif',
			'https://c.tenor.com/e3NL0PJfK00AAAAd/what-shocked.gif',
			'https://c.tenor.com/wVlcPMmDXDwAAAAC/wait-a-minute-hang-on-a-minute.gif',
			'https://c.tenor.com/evjeXjRsYRsAAAAC/wait-a-minute-neil-degrasse-tyson.gif',
			'https://c.tenor.com/LvbGko0yNrwAAAAC/hold-up-wait-a-minute.gif',

		]

		embed.set_image(url=random.choice(wait_a_minutes))
		embed.set_footer(text=f"Queue started by {ctx.author}")
		await answer("__**`Multiplayer`**__")
		view = TheLanguageJungleMultiplayerView(self, 60)
		msg = await ctx.channel.send(content="<a:60_countdown:891432099834388542>", embed=embed, view=view)
		self.multiplayer['message_id'] = msg.id

		self.embed = embed
		await self.audio('language_jungle/SFX/multiplayerjoin.mp3', self.vc)
		await asyncio.sleep(60)
		view.stop()
		# await view.wait()
		count_blue = len(self.multiplayer['teams']['blue'][0])
		count_red = len(self.multiplayer['teams']['red'][0])

		if not count_blue or not count_red:
			await self.reset_bot_status()
			self.active = False
			self.multiplayer_active = False
			msg = await answer(
				"**Both teams must have at least 1 player to start a gaming session! Try again!**")
			ctx.message = msg
			return self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)

		await self.txt.send(f"**🔴 {count_red} red players and {count_blue} blue players!🔵**")
		self.setting_up = False
		await self.make_multiplayer_image()
		await self.audio('language_jungle/SFX/Correct Answer.mp3', self.vc, self.start_multiplayer_game)
	
	async def start_multiplayer_game(self) -> None:
		""" Starts the multiplayer game mode. """

		guild: discord.Guild = self.client.get_guild(server_id)
		server_bot: discord.Member = guild.get_member(self.client.user.id)
		if (bot_voice := server_bot.voice) and bot_voice.mute:
			await server_bot.edit(mute=False)

		the_txt = self.txt

		# Starts the game
		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=self.txt.guild)

		# Checks if the bot is in a voice channel
		if not voice_client:
			await self.vc.connect()
			await asyncio.sleep(1)
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=self.txt.guild)

		# Gets a random language audio
		path, language, audio = self.get_random_language()

		self.current_answer = language

		# Plays the song
		if not voice_client.is_playing():
			audio_source = discord.FFmpegPCMAudio(path)
			self.round += 1
			self.round_active = True
			embed = discord.Embed(
					title=f"__`ROUND {self.round}`__",
					description="The round starts now.",
					color=discord.Color.green()
				)
			await the_txt.send(embed=embed)
			voice_client.play(audio_source, 
			after=lambda e: self.client.loop.create_task(
				self.get_multiplayer_language_response_after(
					self.multiplayer['teams'], language)))


	async def make_multiplayer_image(self) -> None:
		""" Makes the multiplayer's session image. """

		msg = await self.txt.fetch_message(self.multiplayer['message_id'])
		ctx = await self.client.get_context(msg)
		template_image = 'language_jungle/Graphic/multiplayer lobby.png'
		board = Image.open(template_image)
		draw = ImageDraw.Draw(board)
		small = ImageFont.truetype("./Nougat-ExtraBlack.ttf", 25)
		rx, ry = [7, 200]
		bx, by = [734, 205]


		for team_k, team_v in self.multiplayer['teams'].items():
			for team_m in team_v[0]:
				member = discord.utils.get(ctx.guild.members, id=team_m)
				if member:
					pfp = await self.get_user_pfp(member)

				if team_k == 'blue':
					try:
						board.paste(pfp, (bx, by), pfp)
					except:
						pass

					name = None
					if member and member.name:
						name = str(member.name)[:9]
					elif member:
						name = str(member)[:9]

					draw.text((bx-150, by+14), f"{name}", (0, 0, 0), 
					font=small)
					
					by += 70

				elif team_k == 'red':
					try:
						board.paste(pfp, (rx, ry), pfp)
					except:
						pass

					name = None
					if member and member.name:
						name = str(member.name)[:9]
					elif member:
						name = str(member)[:9]

					draw.text((rx+60, ry+14), f"{name}", (0, 0, 0), 
					font=small)
					ry += 70
	
		
		board.save('language_jungle/multiplayer_session.png', 'png', quality=90)
		await self.txt.send(content="<a:10_countdown:891431770912858194>", file=discord.File('language_jungle/multiplayer_session.png'))

	async def get_user_pfp(self, member: discord.Member) -> Any:
		""" Get the user's profile picture.
		:param member: The user to get the profile picture from. """

		async with self.session.get(str(member.display_avatar)) as response:
			image_bytes = await response.content.read()
			with BytesIO(image_bytes) as pfp:
				image = Image.open(pfp)
				im = image.convert('RGBA')

		thumb_width = 59

		def crop_center(pil_img, crop_width, crop_height):
			img_width, img_height = pil_img.size
			return pil_img.crop(((img_width - crop_width) // 2,
									(img_height - crop_height) // 2,
									(img_width + crop_width) // 2,
									(img_height + crop_height) // 2))

		def crop_max_square(pil_img):
			return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

		def mask_circle_transparent(pil_img, blur_radius, offset=0):
			offset = blur_radius * 2 + offset
			mask = Image.new("L", pil_img.size, 0)
			draw = ImageDraw.Draw(mask)
			draw.ellipse((offset, offset, pil_img.size[0] - offset, pil_img.size[1] - offset), fill=255)

			result = pil_img.copy()
			result.putalpha(mask)

			return result

		im_square = crop_max_square(im).resize((thumb_width, thumb_width), Image.LANCZOS)
		im_thumb = mask_circle_transparent(im_square, 4)
		return im_thumb
	

	async def audio(self, audio: str, channel: discord.VoiceChannel, func: Optional[Callable[[Any], Any]] = None) -> None:
		""" Reproduces an audio by informing a path and a channel.
		:param audio: The name of the audio.
		:param channel: The voice channel in which the bot will reproduce the audio in.
		:param func: What the bot will do after the audio is done. """

		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=channel.guild)
		if not voice_client:
			await channel.connect()
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=channel.guild)

		audio_source = discord.FFmpegPCMAudio(audio)
		if not voice_client.is_playing():
			if not func:
				voice_client.play(audio_source, after=lambda e: print('finished'))
			else:
				voice_client.play(audio_source, after=lambda e: self.client.loop.create_task(func()))

	def get_random_language(self) -> str:
		""" Gets a random language audio. """

		while True:
			try:
				path = './language_jungle/Speech'
				all_languages = os.listdir(path)
				language = random.choice(all_languages)
				all_audios = os.listdir(f"{path}/{language}")
				audio = random.choice(all_audios)
				path = f"{path}/{language}/{audio}"
				if not str(language) in self.reproduced_languages:
					self.reproduced_languages.append(str(language))
					return path, language, audio
				else:
					continue
			except Exception:
				print('try harder')
				continue


	async def get_language_response(self, member: discord.Member, channel: discord.TextChannel, language: str) -> None:
		""" (Singleplayer) Waits for a user response and checks whether it's right or wrong.
		:param member: The user who's playing the game.
		:param channel: The channel in which the game is being played.
		:param language: The language/answer of the round. """

		if self.status == 'stop':
			self.status = 'normal'
			return

		await channel.send(f"🔰**`Answer!` ({member.mention})**🔰 ")
		def check(m):
			if m.author.id == member.id and m.channel.id == channel.id:
				# Checks whether user is in the VC to answer the question
				if m.content.startswith('zg!stop'):
					self.client.loop.create_task(self.stop_round(member.guild))
					return False

				return True
				# member_state = member.voice
				# return member_state and member_state.channel.id == self.vc.id

		try:
			answer = await self.client.wait_for('message', timeout=30, check=check)
		except asyncio.TimeoutError:
			await channel.send(f"**{member.mention}, you took too long to answer!\nIt was {language}.\n-1 ❤️**")
			self.wrong_answers += 1
			self.lives -= 1
			self.questions[self.round] = [str(language).lower(), None]
			await self.audio('language_jungle/SFX/Wrong Answer.mp3', channel)
		else:
			answer = answer.content
			self.questions[self.round] = [str(language).lower(), str(answer).lower()]
			if not answer:
				return

			# Checks if it's a right answer
			if str(answer).lower() == str(language).lower():
				await channel.send(f"🎉 **You got it `right`, {member.mention}!\nIt was {language}.** 🎉")
				self.right_answers += 1
				await self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', channel)

			# Otherwise it's a wrong answer
			else:
				we = '<:wrong:735204715415076954>'
				await channel.send(f"{we} **You got it `wrong`, {member.mention}!\nIt was {language}. {we}\n-1 ❤️**")
				self.wrong_answers += 1
				self.lives -= 1
				await self.audio('language_jungle/SFX/Wrong Answer.mp3', channel)
		finally:
			# Checks if the member has remaining lives
			if self.lives > 0:				
				# Restarts the game if it's not the last round
				if self.round < 10:
					await channel.send(f"**New round in 10 seconds... <a:10_countdown:891431770912858194>**")
					await asyncio.sleep(10)
					return await self.start_game(member, channel)
				
				# Otherwise it ends the game and shows the score of the member
				else:
					#self.reproduced_languages = []
					await channel.send(f"💪 **End of the game, you did it, {member.mention}!** 💪")
					try:
						return await self.make_score_image(self.questions, channel)
					except:
						await self.reset_bot_status()

			# Otherwise it ends the game and shows the score of the member
			else:
				await channel.send(f"☠️ **You lost, {member.mention}!** ☠️")
				try:
					return await self.make_score_image(self.questions, channel)
				except:
					await self.reset_bot_status()


	async def get_multiplayer_language_response_after(self, teams: dict, language: str) -> None:
		""" (Multiplayer) Waits for a user response and checks whether it's right or wrong.
		:param teams: The teams.
		:param language: The language/answer of the round. """

		channel = self.txt

		if self.status == 'stop':
			self.status = 'normal'
			return

		await channel.send(f"🔰**`Audio played, GO!!`**🔰 ")

		def check(m):
			member = m.author
			if m.channel.id == channel.id:

				# Checks whether user is in the VC to answer the question
				# member_state = member.voice
				# if not member_state or member_state.channel.id != self.vc.id:
				# 	return False

				if member.id in teams['blue'][0]:

					# Checks if it's a right answer
					if str(m.content).lower() == str(language).lower():
						self.round_active = False
						self.current_answer = None
						
						self.client.loop.create_task(self.stop_round(m.guild))

						self.client.loop.create_task(
							self.txt.send(
								f"🔵🎉 **Point for the blue team! You got it `right`, {member.mention}!\nIt was {language}.** 🎉🔵"
								)
							)
						self.multiplayer['teams']['blue'][1] += 1
						self.questions[self.round] = [None, str(language).lower()]
						self.client.loop.create_task(
							self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', self.vc))
						return True
					else:
						return False

				elif member.id in teams['red'][0]:
					# Checks if it's a right answer
					if str(m.content).lower() == str(language).lower():
						self.round_active = False
						self.current_answer = None

						self.client.loop.create_task(self.stop_round(m.guild))

						self.client.loop.create_task(
							self.txt.send(
								f"🔴🎉 **Point for the red team! You got it `right`, {member.mention}!\nIt was {language}.** 🎉🔴"
								)
							)
						self.multiplayer['teams']['red'][1] += 1
						self.questions[self.round] = [str(language).lower(), None]
						self.client.loop.create_task(
							self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', self.vc))
						return True
					else:
						return False

				else:
					return False
			else:
				return False

		try:
			answer = await self.client.wait_for('message', timeout=30, check=check)
		except asyncio.TimeoutError:
			await channel.send(f"🔴**Red and blue team🔵, you both took too long to answer!\nIt was {language}.**")
			await channel.send("**NO POINTS FOR YOU**")
			self.questions[self.round] = [str(language).lower(), None]
			await self.audio('language_jungle/SFX/Wrong Answer.mp3', self.vc)
			self.round_active = False
			self.current_answer = None

		finally:
			# Restarts the game if it's not the last round
			if self.round < 10:
				await channel.send(f"**New round in 10 seconds... <a:10_countdown:891431770912858194>**")
				await asyncio.sleep(10)
				return await self.start_multiplayer_game()
			
			# Otherwise it ends the game and shows the score of the teams
			else:
				blue_points = self.multiplayer['teams']['blue'][1]
				red_points = self.multiplayer['teams']['red'][1]
				try:
					await self.check_winner(red_points, blue_points)
				except:
					await self.reset_bot_status()

	async def get_multiplayer_language_response_before(self, teams: dict, language: str, message: discord.Message) -> None:
		""" (Multiplayer) Waits for a user response and checks whether it's right or wrong.
		:param teams: The teams.
		:param language: The language/answer of the round.
		:param message: The user message. """

		channel = self.txt
		m = message
		answer_right = False

		if self.status == 'stop':
			self.status = 'normal'
			return

		member = m.author
		#if m.channel.id == channel.id:
		if member.id in teams['blue'][0]:

			# Checks if it's a right answer
			if str(m.content).lower() == str(language).lower():
				answer_right = True
				self.round_active = False
				self.current_answer = None
				
				await self.stop_round(m.guild)

				await self.txt.send(
					f"🔵🎉 **Point for the blue team! You got it `right`, {member.mention}!\nIt was {language}.** 🎉🔵"
				)
				self.multiplayer['teams']['blue'][1] += 1
				self.questions[self.round] = [None, str(language).lower()]
				await self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', self.vc)

		elif member.id in teams['red'][0]:

			# Checks if it's a right answer
			if str(m.content).lower() == str(language).lower():
				answer_right = True
				self.round_active = False
				self.current_answer = None

				await self.stop_round(m.guild)

				await self.txt.send(
					f"🔴🎉 **Point for the red team! You got it `right`, {member.mention}!\nIt was {language}.** 🎉🔴"
				)
				self.multiplayer['teams']['red'][1] += 1
				self.questions[self.round] = [str(language).lower(), None]
				await self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', self.vc)


		if answer_right:
			# Restarts the game if it's not the last round
			if self.round < 10:
				await channel.send(f"**New round in 10 seconds... <a:10_countdown:891431770912858194>**")
				await asyncio.sleep(10)
				return await self.start_multiplayer_game()
			
			# Otherwise it ends the game and shows the score of the teams
			else:
				blue_points = self.multiplayer['teams']['blue'][1]
				red_points = self.multiplayer['teams']['red'][1]
				try:
					await self.check_winner(red_points, blue_points)
				except:
					return await self.reset_bot_status()
				

	async def make_score_image(self, questions: dict, channel: discord.TextChannel) -> None:
		""" Makes the score image.
		:param questions: The questions asked in the game.
		:param the channel to send the score image to. """

		path = './language_jungle/Graphic/score_result.png'
		def get_the_img(the_img: str):
			im = Image.open(the_img)

			thumb_width = 40

			def crop_center(pil_img, crop_width, crop_height):
				img_width, img_height = pil_img.size
				return pil_img.crop(((img_width - crop_width) // 2,
									 (img_height - crop_height) // 2,
									 (img_width + crop_width) // 2,
									 (img_height + crop_height) // 2))

			def crop_max_square(pil_img):
				return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

			im_square = crop_max_square(im).resize((thumb_width, thumb_width), Image.LANCZOS)
			return im_square

		small = ImageFont.truetype("./Nougat-ExtraBlack.ttf", 25)
		background = Image.open("./language_jungle/Graphic/Score_singleplayer.png")
		height = 160

		for k, v in questions.items():
			try:
				language = Image.open(f"./language_jungle/Graphic/answers/{v[0]}.png").resize((120, 40), Image.LANCZOS)
				background.paste(language, (240, height), language.convert('RGBA'))
			except Exception as error:
				pass
			
			try:
				answer = Image.open(f"./language_jungle/Graphic/answers/{v[1]}.png").resize((120, 40), Image.LANCZOS)
				background.paste(answer, (410, height), answer.convert('RGBA'))
			except Exception as error:
				pass


			height += 35

		
		# Get user
		member = await self.client.fetch_user(self.member_id)

		user_info = await self.get_user_currency(member.id)
		sloth_profile = await self.get_sloth_profile(member.id)
		if not user_info or not sloth_profile:
			await self.reset_bot_status()
			return await channel.send(embed=discord.Embed(description=f"**You don't have an account yet, {member.mention}. Click [here](https://thelanguagesloth.com/profile/update) to create one!**"))
			# money = 0
		else:
			money = user_info[0][1]


		# Sloth image request
		sloth = Image.open(f'sloth_custom_images/sloth/{sloth_profile[1].title()}.png').resize((350, 250), Image.LANCZOS)
		# sloth = Image.open(await self.get_user_specific_type_item(member.id, 'sloth')).resize((350, 250), Image.LANCZOS)
		body = Image.open(await self.get_user_specific_type_item(member.id, 'body')).resize((350, 250), Image.LANCZOS)
		hand = Image.open(await self.get_user_specific_type_item(member.id, 'hand')).resize((350, 250), Image.LANCZOS)
		foot = Image.open(await self.get_user_specific_type_item(member.id, 'foot')).resize((350, 250), Image.LANCZOS)
		head = Image.open(await self.get_user_specific_type_item(member.id, 'head')).resize((350, 250), Image.LANCZOS)


		# Sloth image pasting
		background.paste(sloth, (-65, 190), sloth.convert('RGBA'))
		background.paste(body, (-65, 190), body.convert('RGBA'))
		background.paste(hand, (-65, 190), hand.convert('RGBA'))
		background.paste(foot, (-65, 190), foot.convert('RGBA'))
		background.paste(head, (-65, 190), head.convert('RGBA'))

		draw = ImageDraw.Draw(background)

		# Sloth text printing
		if name := member.name:
			name = name[:9]

		draw.text((50, 145), f"{name}", (0, 0, 0), font=small)

		# Get playtime
		end_ts = time()
		playtime = f"{(end_ts - self.start_ts)/60:.1f} mins"

		# Status text printing
		draw.text((635, 220), f"{money}", (0, 0, 0), font=small)
		draw.text((635, 265), f"{playtime}", (0, 0, 0), font=small)
		draw.text((635, 315), f"{self.right_answers}", (0, 0, 0), font=small)
		draw.text((635, 370), f"{self.wrong_answers}", (0, 0, 0), font=small)

		background.save('./language_jungle/Graphic/score_result.png')

		await channel.send(file=discord.File(path))
		if self.lives:
			try:
				await self.update_user_money(self.member_id, 20)
			except Exception:
				pass
			else:
				await channel.send(f"<:zslothmonopoly:705452184602673163> **20łł have been added into your account!** <:zslothmonopoly:705452184602673163>")

		await channel.send(embed=discord.Embed(title=f"**If you can, please send an audio speaking to `Cosmos △#7757`, to expand our game, we'd be pleased to hear it!**"))
		await self.reset_bot_status()

	async def check_winner(self, redp: int, bluep: int) -> None:
		""" Checks the winner of the game.
		:param redp: Red team points.
		:param bluep: Blue team points. """

		
		embed = discord.Embed(
			title="__End of the Game__",
			description="💪 Good job for both teams! 💪"
		)

		embed.add_field(name="🔴 __Red team__:", value=f"Right answers: `{redp}`.", inline=True)
		embed.add_field(name="🔵 __Blue team__:", value=f"Right answers: `{bluep}`.", inline=True)

		channel = self.vc

		if redp > bluep:
			embed.add_field(name="🎊 __Winning Team__:", value="The red team won! 🔴", inline=False)
			embed.add_field(name="🎁 __Reward__:", value="Each player from the red team got 10łł! 🍃", inline=False)
			embed.color = discord.Color.red()
			winners = self.multiplayer['teams']['red'][0]
			path = './language_jungle/Graphic/red wins.png'
			await self.audio('language_jungle/SFX/Red wins.mp3', channel)

		elif bluep > redp:
			embed.add_field(name="🎊 __Winning Team__:", value="The blue team won! 🔵", inline=False)
			embed.add_field(name="🎁 __Reward__:", value="Each player from the blue team got 10łł! 🍃", inline=False)
			embed.color = discord.Color.blue()
			winners = self.multiplayer['teams']['blue'][0]
			path = './language_jungle/Graphic/blue wins.png'
			await self.audio('language_jungle/SFX/Blue wins.mp3', channel)

		else:
			winners = []
			embed.add_field(name="🎊 __Winning Team__:", value="It's a tie, no one won! 🙅", inline=False)
			embed.color = discord.Color.orange()

		try:
			if winners:
				score_path: str = await self.make_multiplayer_score_image(winners, path)
			else:
				if redp + bluep >= 2:
					embed.add_field(name="🎁 __Reward__:", value="Each player from both teams got 7łł! 🍃", inline=False)
					# Rewards both teams, in case of game drew itself
					both_teams: List[int] = self.multiplayer['teams']['blue'][0]
					both_teams.extend(self.multiplayer['teams']['red'][0])

					for user_id in both_teams:
						try:
							await self.update_user_money(user_id, 7)
						except Exception:
							pass

		except Exception as e:
			await self.txt.send("**Something went wrong when sending the Score picture!**")
			print('='*20)
			print(f"Score Picture Error: {e}")
			print('='*20)
		else:
			if winners:
				embed.set_image(url="attachment://multiplayer_score_image.png")
				await self.txt.send(embed=embed, file=discord.File(score_path, filename="multiplayer_score_image.png"))
			else:
				await self.txt.send(embed=embed)
		finally:
			await self.reset_bot_status()


	async def make_multiplayer_score_image(self, winners: List[int], image_path: str) -> str:
		""" Makes the multiplayer score image.
		:param winners: The people in the winning team.
		:param image_path: The path of the winning team's template image."""

		channel = self.txt

		#232, 595 326765585461411851 , [356, 970]
		coordinates = iter([[316, 482], [128, 510], [498, 512], [2, 425], 
		[614, 402]])
		sloth_coordinates = iter([[226, 284], [78, 312], [378, 314], [-78, 227], 
		[524, 204]])

		small = ImageFont.truetype("./Nougat-ExtraBlack.ttf", 25)
		
		background = Image.open(image_path)

		draw = ImageDraw.Draw(background)
		guild = self.client.get_guild(server_id)
		# Loops all winners
		for winner in winners:
			# Get user
			member = guild.get_member(winner)
			cords = next(coordinates)
			sloth_cords = next(sloth_coordinates)
			sloth_profile = await self.get_sloth_profile(winner)
			if not sloth_profile:
				await member.send(embed=discord.Embed(description=f"**You didn't appear in the Sloth Games score because you don't have an account yet. Click [here](https://thelanguagesloth.com/profile/update) to create one!**"))
				continue
			elif sloth_profile[1].lower() == 'default':
				await member.send(embed=discord.Embed(description=f"**You didn't appear in the Sloth Games score because you didn't choose a Sloth Class yet. Click [here](https://thelanguagesloth.com/profile/update) to create one!**"))
				continue

			# Gets their Sloth items
			sloth = Image.open(f'sloth_custom_images/sloth/{sloth_profile[1].title()}.png').resize((350, 250), Image.LANCZOS)
			body = Image.open(await self.get_user_specific_type_item(
				member.id, 'body')).resize((350, 250), Image.LANCZOS)
			hand = Image.open(await self.get_user_specific_type_item(
				member.id, 'hand')).resize((350, 250), Image.LANCZOS)
			foot = Image.open(await self.get_user_specific_type_item(
				member.id, 'foot')).resize((350, 250), Image.LANCZOS)
			head = Image.open(await self.get_user_specific_type_item(
				member.id, 'head')).resize((350, 250), Image.LANCZOS)

			# Sloth image pasting
			background.paste(sloth, sloth_cords, sloth.convert('RGBA'))
			background.paste(body, sloth_cords, body.convert('RGBA'))
			background.paste(hand, sloth_cords, hand.convert('RGBA'))
			background.paste(foot, sloth_cords, foot.convert('RGBA'))
			background.paste(head, sloth_cords, head.convert('RGBA'))

			# Sloth text printing and icon pasting
			try:
				member_icon = await self.get_user_pfp(member)
				background.paste(member_icon, cords, member_icon)
			except:
				pass

			# Writes their names
			name_cords = [cords[0]+55,  cords[1]+20]
			name = member.name
			if name:
				name = str(name)[:10]
			draw.text(name_cords, f"{name}", (0, 0, 0), font=small)

			# Updates money
			try:
				# Checks whether they are in the TLJ VC
				# member_state = member.voice
				# if not member_state or member_state.channel.id != self.vc.id:
				# 	continue

				await self.update_user_money(member.id, 10)
			except Exception as e:
				print(e)
				pass


		score_path = './language_jungle/Graphic/multiplayer_score_result.png'
		background.save(score_path)
		return score_path
		

	# Database method (1)
	async def update_user_money(self, user_id: int, money: int) -> None:
		""" Updates the user money.
		:param user_id: The ID of the user to update the money.
		:param money: The increment money value. (Can be negative) """

		mycursor, db = await the_database()
		await mycursor.execute("UPDATE UserCurrency SET user_money = user_money + %s WHERE user_id = %s", (money, user_id))
		await db.commit()
		await mycursor.close()


	async def reset_bot_status(self) -> None:
		""" Resets the bot's status. """

		self.questions.clear()
		self.round = 0
		self.lives = 3
		self.member_id = None
		self.wrong_answers = 0
		self.right_answers = 0
		self.active = False
		self.multiplayer_active = False
		self.reproduced_languages.clear()
		self.status = 'normal'
		self.start_ts = None
		self.round_active = False
		self.current_answer = None
		self.multiplayer = {
			'teams': {
				'blue': [[], 0],
				'red': [[], 0]
				},
			'message_id': None
		}


	# @commands.command(aliases=['refresh', 'rfcd', 'reset'])
	# @commands.has_permissions(administrator=True)
	# async def refresh_cooldown(self, ctx, member: Optional[discord.Member] = None) -> None:
	# 	""" (ADM) Resets the cooldown for a specific user.
	# 	:param member: The member to reset the cooldown (Optional). """

	# 	if not member:
	# 		member = ctx.author

	# 	channel = ctx.channel
	# 	for m in await channel.history(limit=100).flatten():
	# 		if m.author == member and m.channel.id == channel.id:
	# 			new_ctx = await self.client.get_context(m)
	# 			self.client.get_command('language').reset_cooldown(new_ctx)
	# 			self.client.get_command('play_multiplayer_language').reset_cooldown(new_ctx)
	# 			return await ctx.send(f"**{member.mention}'s cooldown has been reset!**")
	# 	else:
	# 		await ctx.send("**For some reason I couldn't reset the cooldown for this member, lol!**")


	# Database methods (3)
	async def get_user_currency(self, user_id: int) -> List[List[int]]:
		""" Gets the user's currency info.
		:param user_id: The ID of the user to get. """

		mycursor, _ = await the_database()
		await mycursor.execute("SELECT * FROM UserCurrency WHERE user_id = %s", (user_id,))
		user_currency = await mycursor.fetchall()
		await mycursor.close()
		return user_currency

	async def get_sloth_profile(self, user_id: int) -> List[Union[int, str]]:
		""" Gets the user's Sloth Profile information. """

		mycursor, _ = await the_database()
		await mycursor.execute("SELECT * FROM SlothProfile WHERE user_id = %s", (user_id,))
		user_currency = await mycursor.fetchone()
		await mycursor.close()
		return user_currency

	async def get_user_specific_type_item(self, user_id: int, item_type: str) -> str:
		""" Get a specific item type from the user.
		:param user_id: The ID of the user.
		:param item_type: The type of the item. """

		mycursor, _ = await the_database()
		await mycursor.execute(
			"SELECT item_name, image_name FROM UserItems WHERE user_id = %s AND item_type = %s AND enable = 'equipped'",
			(user_id, item_type))
		spec_type_items = await mycursor.fetchone()
		await mycursor.close()
		
		if spec_type_items and spec_type_items[1]:
			return f'./sloth_custom_images/{item_type}/{spec_type_items[1]}'

		else:
			return f'./sloth_custom_images/{item_type}/base_{item_type}.png'

	@commands.command(name="samples", aliases=['audios', 'languages', 'smpls', 'langs'])
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def _samples_command(self, ctx: commands.Context) -> None:
		""" Shows how many audio samples and languages we currently have in The Language Jungle game. """

		await self._samples_callback(ctx)

	async def _samples_callback(self, ctx: Union[commands.Context, discord.ApplicationContext]) -> None:
		""" Shows how many audio samples and languages we currently have in The Language Jungle game. (Callback) """

		answer: discord.PartialMessageable = None
		if isinstance(ctx, commands.Context):
			answer = ctx.send
		else:
			answer = ctx.respond

		path = './language_jungle/Speech'
		languages = [folder for folder in os.listdir(path)]
		audios = [1 for language in languages for _ in os.listdir(f"{path}/{language}")]

		current_time = await utils.get_time_now()

		embed = discord.Embed(
			title="__Samples__",
			description=f"We currently have **`{sum(audios)}`** different audio samples grouped into **`{len(languages)}`** different languages respectively.",
			color=ctx.author.color,
			timestamp=current_time
		)
		embed.set_author(name=self.client.user, icon_url=self.client.user.display_avatar)
		embed.set_thumbnail(url=ctx.guild.icon.url)
		embed.set_footer(text=f"Requested by: {ctx.author}", icon_url=ctx.author.display_avatar)
		await answer(embed=embed)


	@commands.command(aliases=["stfu", "shutup", "shut_up", "silent", "quiet", "shh"])
	@utils.is_allowed_members([287746936587419648], throw_exc=True)
	async def silence(self, ctx) -> None:
		""" Server mutes the bot until it starts reproducing language audio samples. """


		if not self.setting_up and self.active:
			return await ctx.reply("**I'm playing now, I can't just stop speaking!**")

		server_bot: discord.Member = ctx.guild.get_member(self.client.user.id)

		if (voice := server_bot.voice) and voice.mute:
			return await ctx.reply("***Whisper: I'm already silenced!***")

		if not voice:
			return await ctx.reply("**Hey, I'm not in a VC, call me first, and then I'll do it!**")

		await server_bot.edit(mute=True)
		await ctx.reply("**I'll keep in silence for a bit 🤐!**")

	@commands.command(aliases=["talk", "speak", "unsilent"])
	@utils.is_allowed_members([287746936587419648], throw_exc=True)
	async def unsilence(self, ctx) -> None:
		""" Server unmutes the bot. """

		server_bot: discord.Member = ctx.guild.get_member(self.client.user.id)

		if (voice := server_bot.voice) and not voice.mute:
			return await ctx.reply("**I'm not even silenced!**")

		if not voice:
			return await ctx.reply("**Hey, I'm not in a VC, call me first, and then I'll do it!**")

		await server_bot.edit(mute=False)
		await ctx.reply("**Shall I talk again 🤩!**")

def setup(client):
	client.add_cog(TheLanguageJungle(client))