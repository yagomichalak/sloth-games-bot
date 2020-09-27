import discord
from discord.ext import commands, tasks
from gtts import gTTS
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import random
import asyncio
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from mysqldb import the_database, the_database2
from time import sleep, time
import aiohttp
from io import BytesIO

language_jungle_txt_id = 736734120998207589
language_jungle_vc_id = 736734244839227464
cosmos_id = 423829836537135108

gauth = GoogleAuth()
# gauth.LocalWebserverAuth()
gauth.LoadCredentialsFile("mycreds.txt")
if gauth.credentials is None:
	# This is what solved the issues:
	gauth.GetFlow()
	gauth.flow.params.update({'access_type': 'offline'})
	gauth.flow.params.update({'approval_prompt': 'force'})

	# Authenticate if they're not there
	gauth.LocalWebserverAuth()

elif gauth.access_token_expired:

	# Refresh them if expired
	gauth.Refresh()
else:

	# Initialize the saved creds
	gauth.Authorize()

# Save the current credentials to a file
gauth.SaveCredentialsFile("mycreds.txt")

drive = GoogleDrive(gauth)

class Games(commands.Cog):
	'''
	Some games related commands.
	'''

	def __init__(self, client):
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

		# on_initialization
		#self.client.loop.create_task(self.async_init())

		
		
	@commands.Cog.listener()
	async def on_ready(self):
		print('Games cog is online!')
		try:
			self.change_status.start()
		except:
			pass
		channel = self.client.get_channel(language_jungle_txt_id)
		self.txt = await self.client.fetch_channel(language_jungle_txt_id)
		self.vc = await self.client.fetch_channel(language_jungle_vc_id)
		await self.audio_update()
		await self.shop_update()
		self.ready = True
		await self.txt.send("**I'm ready to play!**")

	# async def async_init(self):
	# 	channel = self.client.get_channel(language_jungle_txt_id)
	# 	self.txt = await self.client.fetch_channel(language_jungle_txt_id)
	# 	self.vc = await self.client.fetch_channel(language_jungle_vc_id)
	# 	self.ready = True


	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, member):
		#guild = self.client.get_guild(payload.guild_id)
		#member = discord.utils.get(guild.members, id=payload.member_id)
		if not member or member.bot:
			return
		mid = self.multiplayer['message_id']
		if not mid:
			return
		if not reaction.message.id == mid:
			return
		if not self.setting_up:
			return
		msg = await self.txt.fetch_message(mid)

		emj = str(reaction.emoji)
		if emj in ['🔵', '🔴']:
			blue_team = self.multiplayer['teams']['blue'][0]
			red_team = self.multiplayer['teams']['red'][0]
			if member.id in blue_team or member.id in red_team:
				return await msg.remove_reaction(reaction, member)

			self.embed.clear_fields()
			if emj == '🔵':
				if len(blue_team) == 5:
					await msg.remove_reaction(reaction, member)
				else:
					blue_team.append(member.id)

			elif emj == '🔴':
				if len(red_team) == 5:
					await msg.remove_reaction(reaction, member)
				else:
					red_team.append(member.id)

			self.embed.add_field(name='🔴 __Red team__', value=f"{len(self.multiplayer['teams']['red'][0])}/5 players.", inline=True)
			self.embed.add_field(name='🔵 __Blue team__', value=f"{len(self.multiplayer['teams']['blue'][0])}/5 players.", inline=True)
			await msg.edit(embed=self.embed)
			
		else:
			await msg.remove_reaction(reaction, member)

		#print(msg.reactions)

	@commands.Cog.listener()
	async def on_reaction_remove(self, reaction, member):
		
		if not member or member.bot:
			return
		mid = self.multiplayer['message_id']
		if not mid:
			return
		if not reaction.message.id == mid:
			return
		if not self.setting_up:
			return
		msg = await self.txt.fetch_message(mid)

		emj = str(reaction.emoji)
		if emj in ['🔵', '🔴']:
			blue_team = self.multiplayer['teams']['blue'][0]
			red_team = self.multiplayer['teams']['red'][0]
			if member.id not in blue_team and member.id not in red_team:
				return
			self.embed.clear_fields()
			if emj == '🔵':
				try:
					blue_team.remove(member.id)
				except:
					pass

			elif emj == '🔴':
				try:
					red_team.remove(member.id)
				except:
					pass

			self.embed.add_field(name='🔴 __Red team__', value=f"{len(self.multiplayer['teams']['red'][0])}/5 players.", inline=True)
			self.embed.add_field(name='🔵 __Blue team__', value=f"{len(self.multiplayer['teams']['blue'][0])}/5 players.", inline=True)
			await msg.edit(embed=self.embed)

	@commands.Cog.listener()
	async def on_message(self, message):
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


	# Members status update
	@tasks.loop(seconds=10)
	async def change_status(self):
		if self.active:
			await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f'with someone.'))
		else:
			await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'new players.'))


	# Downloads all content for the Language Jungle game
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def audio_update(self, ctx=None, rall: str = 'no'):
		'''
		Downloads all shop images from the GoogleDrive and stores in the bot's folder
		:param ctx:
		:return:
		'''
		if rall.lower() == 'yes':
			try:
				os.removedirs('./language_jungle')
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
	async def shop_update(self, ctx=None):
		'''
		(ADM) Downloads all shop images from the Google Drive.
		'''
		if ctx:
			await ctx.message.delete()
		'''
		Downloads all shop images from the GoogleDrive and stores in the bot's folder
		:param ctx:
		:return:
		'''
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
	async def stop(self, ctx):
		'''
		Stops the game.
		'''
		if not self.active:
			return await ctx.send(f"**{ctx.author.mention}, I'm not even playing yet!**")

		perms = ctx.channel.permissions_for(ctx.author)
		if self.multiplayer_active:
			if perms.kick_members or perms.administrator:
				await self.reset_bot_status()
				guild = ctx.message.guild
				voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
				if voice_client and voice_client.is_playing():
					self.status = 'stop'
					voice_client.stop()
				return await ctx.send("**Multiplayer session ended!**")
			return await ctx.send(f"**{ctx.author.mention}, you cannot end a multiplayer session just like that!**")


		if perms.kick_members or perms.administrator or self.member_id == ctx.author.id:
			await self.reset_bot_status()
			guild = ctx.message.guild
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
			if voice_client and voice_client.is_playing():
				self.status = 'stop'
				voice_client.stop()
			await ctx.send("**Session ended!**")
		else:
			return await ctx.send(f"{ctx.author.mention}, you're not the one who's playing, nor is a staff member")

	async def stop_round(self, guild):
		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=guild)
		if voice_client and voice_client.is_playing():
			self.status = 'stop'
			voice_client.stop()
		#await self.txt.send("**Round ended!**")


	@commands.cooldown(1, 1800, type=commands.BucketType.user)
	@commands.command(aliases=['language', 'language jungle', 'jungle', 'lj', 'play', 'p'])
	async def play_language(self, ctx):
		'''
		Plays the Language Jungle.
		'''
		member = ctx.author
		the_txt = self.txt
		if ctx.channel.id != language_jungle_txt_id:
			self.client.get_command('play_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you can only use this command in {the_txt.mention}!**")

		# Checks if the user is in a voice channel
		voice = ctx.message.author.voice
		if voice is None:
			self.client.get_command('play_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you're not in the voice channel**")

		if voice.channel.id != language_jungle_vc_id:
			self.client.get_command('play_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you're not in the `Language Jungle` voice channel!**")

		if not self.ready:
			return await ctx.send("**I'm still downloading the audios, wait a bit!**")

		if self.active:
			self.client.get_command('play_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, someone is already playing!**")

		the_vc = discord.utils.get(member.guild.channels, id=language_jungle_vc_id)
		self.active = True
		self.member_id = member.id
		self.start_ts = time()
		await self.start_game(member, the_txt)

	# Starts the Language Jungle game
	async def start_game(self, member: discord.Member, the_txt):
		
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
			# get a random language audio
			path, language, audio = self.get_random_language()
			# Plays the song
			if not voice_client.is_playing():
				audio_source = discord.FFmpegPCMAudio(path)
				await the_txt.send("**The round starts now!**")
				self.round += 1
				await the_txt.send(f"**`ROUND {self.round}`**")
				voice_client.play(audio_source, after=lambda e: self.client.loop.create_task(self.get_language_response(member, the_txt, language)))

		else:
			# (to-do) send a message to a specific channel
			await the_txt.send("**The player left the voice channel, so it's game over!**")
			await self.reset_bot_status()


	@commands.command(aliases=['pmp', 'mp', 'multiplayer'])
	@commands.cooldown(1, 360, type=commands.BucketType.guild)
	async def play_multiplayer_language(self, ctx):
		'''
		Plays the Language Jungle (Multiplayer).
		'''
		member = ctx.author
		the_txt = self.txt
		if ctx.channel.id != language_jungle_txt_id:
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you can only use this command in {the_txt.mention}!**")

		# Checks if the user is in a voice channel
		voice = ctx.message.author.voice
		if voice is None:
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you're not in the voice channel**")

		if voice.channel.id != language_jungle_vc_id:
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, you're not in the `Language Jungle` voice channel!**")

		if not self.ready:
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send("**I'm still downloading the audios, wait a bit!**")

		if self.active:
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, someone is already playing!**")

		await self.reset_bot_status()
		self.active = True
		self.multiplayer_active = True
		self.setting_up = True

		embed = discord.Embed(
			title="Setting up the Game...",
			description='''
			```React to this message in order to participate in the multiplayer game session!```
			React 🔴 to enter red team;
			React 🔵 to enter the blue team.
			'''
			)
		embed.add_field(name='🔴 __Red team__', value=f"{len(self.multiplayer['teams']['red'][0])}/5 players.", inline=True)
		embed.add_field(name='🔵 __Blue team__', value=f"{len(self.multiplayer['teams']['blue'][0])}/5 players.", inline=True)
		embed.set_image(url='https://media1.tenor.com/images/81e68cca293ebd7656deec2bc582ef1c/tenor.gif?itemid=14484132')
		embed.set_footer(text=f"Queue started by {ctx.author}")
		msg = await ctx.send(embed=embed)
		self.multiplayer['message_id'] = msg.id

		await msg.add_reaction('🔴')
		await msg.add_reaction('🔵')
		self.embed = embed
		await asyncio.sleep(60)
		count_blue = len(self.multiplayer['teams']['blue'][0])
		count_red = len(self.multiplayer['teams']['red'][0])
		if not count_blue or not count_red:
			await self.reset_bot_status()
			self.active = False
			self.multiplayer_active = False
			self.client.get_command('play_multiplayer_language').reset_cooldown(ctx)
			return await ctx.send(
				"**Both teams must have at least 1 player to start a gaming session! Try again!**")

		await self.txt.send(f"**🔴 {count_red} red players and {count_blue} blue players!🔵**")
		self.setting_up = False
		await self.make_multiplayer_image()
		await asyncio.sleep(10)
		await self.start_multiplayer_game()
	
	async def start_multiplayer_game(self):
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
			await self.txt.send("**The round starts now!**")
			self.round += 1
			self.round_active = True
			await the_txt.send(f"**`ROUND {self.round}`**")
			voice_client.play(audio_source, 
			after=lambda e: self.client.loop.create_task(
				self.get_multiplayer_language_response_after(
					self.multiplayer['teams'], language)))


	async def make_multiplayer_image(self):
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
				member_icon = None
				if member:
					pfp = await self.get_user_pfp(member)

				if team_k == 'blue':
					try:
						board.paste(pfp, (bx, by), pfp)
					except:
						pass

					try:
						draw.text((bx-150, by+14), f"{str(member.name)[:9]}", (0, 0, 0), 
					font=small)
					except:
						draw.text((bx-150, by+14), f"Player", (0, 0, 0), 
					font=small)
					
					by += 70
				elif team_k == 'red':
					try:
						board.paste(pfp, (rx, ry), pfp)
					except:
						pass
					try:
						draw.text((rx+60, ry+14), f"{str(member.name)[:9]}", (0, 0, 0), 
					font=small)
					except:
						draw.text((rx+60, ry+14), f"Player", (0, 0, 0), 
					font=small)
					ry += 70
	
		
		board.save('language_jungle/multiplayer_session.png', 'png', quality=90)
		await self.txt.send(file=discord.File('language_jungle/multiplayer_session.png'))

	async def get_user_pfp(self, member):
		async with self.session.get(str(member.avatar_url)) as response:
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
		#im_thumb.save('png/user_pfp.png', 'png', quality=90)
		return im_thumb
	

	# Reproduces an audio by informing a path and a channel
	async def audio(self, audio: str, channel):
		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=channel.guild)
		if not voice_client:
			await channel.connect()
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=channel.guild)

		audio_source = discord.FFmpegPCMAudio(audio)
		if not voice_client.is_playing():
			voice_client.play(audio_source, after=lambda e: print('finished'))

	# Gets a random language audio
	def get_random_language(self) -> str:
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


	# (Singleplayer) Waits for a user response and checks whether it's right or wrong
	async def get_language_response(self, member: discord.Member, channel, language: str):
		if self.status == 'stop':
			self.status = 'normal'
			return
		await channel.send(f"🔰**`Answer!` ({member.mention})**🔰 ")
		def check(m):
			return m.author.id == member.id and m.channel.id == channel.id

		try:
			answer = await self.client.wait_for('message', timeout=30, check=check)
		except asyncio.TimeoutError:
			await channel.send(f"**{member.mention}, you took too long to answer!\nIt was {language}.**")
			await channel.send("**-1 ❤️**")
			self.wrong_answers += 1
			self.lives -= 1
			self.questions[self.round] = [str(language).lower(), None]
			await self.audio('language_jungle/SFX/Wrong Answer.mp3', channel)
		else:
			answer = answer.content
			print(answer)
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
				await channel.send(f"{we} **You got it `wrong`, {member.mention}!\nIt was {language}.** {we}")
				await channel.send("**-1 ❤️**")
				self.wrong_answers += 1
				self.lives -= 1
				await self.audio('language_jungle/SFX/Wrong Answer.mp3', channel)
		finally:
			# Checks if the member has remaining lives
			if self.lives > 0:				
				# Restarts the game if it's not the last round
				if self.round < 10:
					await channel.send(f"**New round in 10 seconds...**")
					await asyncio.sleep(10)
					return await self.start_game(member, channel)
				
				# Otherwise it ends the game and shows the score of the member
				else:
					#self.reproduced_languages = []
					await channel.send(f"💪 **End of the game, you did it, {member.mention}!** 💪")
					return await self.make_score_image(self.questions, channel)

			# Otherwise it ends the game and shows the score of the member
			else:
				await channel.send(f"☠️ **You lost, {member.mention}!** ☠️")
				return await self.make_score_image(self.questions, channel)


	# (Multiplayer) Waits for a user response and checks whether it's right or wrong
	async def get_multiplayer_language_response_after(self, teams, language: str):
		channel = self.txt

		if self.status == 'stop':
			self.status = 'normal'
			return

		await channel.send(f"🔰**`Audio played, GO!!`**🔰 ")

		def check(m):
			member = m.author
			if m.channel.id == channel.id:
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
							self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', channel))
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
							self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', channel))
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
			await self.audio('language_jungle/SFX/Wrong Answer.mp3', channel)
			self.round_active = False
			self.current_answer = None

		finally:
			# Restarts the game if it's not the last round
			if self.round < 10:
				await channel.send(f"**New round in 10 seconds...**")
				await asyncio.sleep(10)
				return await self.start_multiplayer_game()
			
			# Otherwise it ends the game and shows the score of the teams
			else:
				blue_points = self.multiplayer['teams']['blue'][1]
				red_points = self.multiplayer['teams']['red'][1]
				await channel.send(f"💪 **End of the game, good job, teams!** 💪")
				await channel.send(
					f"**🔴__Red team__:\nRight answers: `{red_points}`.🔴**")
				await channel.send(
					f"**🔵__Blue team__:\nRight answers: `{blue_points}`.🔵**")
				await self.check_winner(red_points, blue_points)

	# (Multiplayer) Waits for a user response and checks whether it's right or wrong
	async def get_multiplayer_language_response_before(self, teams, language: str, message):
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
				await self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', channel)

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
				await self.audio('language_jungle/SFX/Anime wow - sound effect.mp3', channel)


		if answer_right:
			# Restarts the game if it's not the last round
			if self.round < 10:
				await channel.send(f"**New round in 10 seconds...**")
				await asyncio.sleep(10)
				return await self.start_multiplayer_game()
			
			# Otherwise it ends the game and shows the score of the teams
			else:
				blue_points = self.multiplayer['teams']['blue'][1]
				red_points = self.multiplayer['teams']['red'][1]
				await channel.send(f"💪 **End of the game, good job, teams!** 💪")
				await channel.send(
					f"**__Red team__:\nRight answers: `{red_points}`.**")
				await channel.send(
					f"**__Blue team__:\nRight answers: `{blue_points}`.**")
				await self.check_winner(red_points, blue_points)
				

	async def make_score_image(self, questions: dict, channel):
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
		if not user_info:
			money = 0
		else:
			money = user_info[0][1]


		# Sloth image request
		sloth = Image.open(await self.get_user_specific_type_item(member.id, 'sloth')).resize((350, 250), Image.LANCZOS)
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
		draw.text((50, 145), f"{member.name}", (0, 0, 0), font=small)

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
				await self.update_user_money(self.member_id, 10)
			except Exception:
				pass
			else:
				await channel.send(f"<:zslothmonopoly:705452184602673163> **10łł have been added into your account!** <:zslothmonopoly:705452184602673163>")

		await channel.send(embed=discord.Embed(title=f"**If you can, please send an audio speaking to `Cosmos △#7757`, to expand our game, we'd be pleased to hear it!**"))
		await self.reset_bot_status()

	async def check_winner(self, redp, bluep):
		if redp > bluep:
			await self.txt.send("**🔴Red team won!🔴**")
			winners = self.multiplayer['teams']['red'][0]
			path = './language_jungle/Graphic/red wins.png'
			await self.make_multiplayer_score_image(winners, path)

		elif bluep > redp:
			await self.txt.send("**🔵Blue team won🔵!**")
			winners = self.multiplayer['teams']['blue'][0]
			path = './language_jungle/Graphic/blue wins.png'
			await self.make_multiplayer_score_image(winners, path)

		else:
			await self.txt.send("**It's a tie! No one wins!**")

		await self.reset_bot_status()


	async def make_multiplayer_score_image(self, winners, image_path):
		channel = self.txt

		#232, 595 326765585461411851 , [356, 970]
		coordinates = iter([[316, 482], [128, 510], [498, 512], [2, 425], 
		[614, 402]])
		sloth_coordinates = iter([[226, 284], [78, 312], [378, 314], [-78, 227], 
		[524, 204]])

		small = ImageFont.truetype("./Nougat-ExtraBlack.ttf", 25)
		
		background = Image.open(image_path)

		draw = ImageDraw.Draw(background)
		for i, winner in enumerate(winners):
			print(i)
			# Get user
			member = await self.client.fetch_user(winner)
			cords = next(coordinates)
			sloth_cords = next(sloth_coordinates)


			# Sloth image request
			sloth = Image.open(await self.get_user_specific_type_item(
				member.id, 'sloth')).resize((350, 250), Image.LANCZOS)
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

			name_cords = [cords[0]+55,  cords[1]+20]
			draw.text(name_cords, f"{str(member.name)[:9]}", (0, 0, 0), font=small)
			try:
				await self.update_user_money(member.id, 15)
			except Exception:
				pass


		score_path = './language_jungle/Graphic/multiplayer_score_result.png'
		background.save(score_path)
		await channel.send(file=discord.File(score_path))
		

	# Database method (1)
	async def update_user_money(self, user_id: int, money: int):
		mycursor, db = await the_database()
		await mycursor.execute(f"UPDATE UserCurrency SET user_money = user_money + {money} WHERE user_id = {user_id}")
		await db.commit()
		await mycursor.close()


	async def reset_bot_status(self):
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


	@commands.command(aliases=['refresh', 'rfcd', 'reset'])
	@commands.has_permissions(administrator=True)
	async def refresh_cooldown(self, ctx, member: discord.Member = None):
		'''
		(ADM) Resets the cooldown for a specific user.
		:param member: The member to reset the cooldown (Optional).
		'''
		if not member:
			member = ctx.author

		channel = ctx.channel
		for m in await channel.history(limit=100).flatten():
			if m.author == member and m.channel.id == channel.id:
				new_ctx = await self.client.get_context(m)
				self.client.get_command('play_language').reset_cooldown(new_ctx)
				return await ctx.send(f"**{member.mention}'s cooldown has been reset!**")
		else:
			await ctx.send("**For some reason I couldn't reset the cooldown for this member, lol!**")


	# Database methods (3)
	async def get_user_currency(self, user_id: int):
		mycursor, db = await the_database2()
		await mycursor.execute(f"SELECT * FROM UserCurrency WHERE user_id = {user_id}")
		user_currency = await mycursor.fetchall()
		await mycursor.close()
		return user_currency

	async def get_user_specific_type_item(self, user_id, item_type):
		mycursor, db = await the_database2()
		await mycursor.execute(
			f"SELECT * FROM UserItems WHERE user_id = {user_id} and item_type = '{item_type}' and enable = 'equipped'")
		spec_type_items = await mycursor.fetchall()
		if len(spec_type_items) != 0:
			registered_item = await self.get_specific_register_item(spec_type_items[0][1])
			return f'./sloth_custom_images/{item_type}/{registered_item[0][0]}'
		else:
			default_item = f'./sloth_custom_images/{item_type}/base_{item_type}.png'
			return default_item

	async def get_specific_register_item(self, item_name: str):
		mycursor, db = await the_database2()
		await mycursor.execute(f"SELECT * FROM RegisteredItems WHERE item_name = '{item_name}'")
		item = await mycursor.fetchall()
		await mycursor.close()
		return item


def setup(client):
	client.add_cog(Games(client))