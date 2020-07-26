import discord
from discord.ext import commands, tasks
from gtts import gTTS
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import random
import asyncio
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from mysqldb import the_database

language_jungle_txt_id = 736734120998207589
language_jungle_vc_id = 736734244839227464

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
		self.round = 0
		self.lives = 3
		self.wrong_answers = 0
		self.right_answers = 0
		self.active = False
		self.questions = {}
		self.member_id = None


	@commands.Cog.listener()
	async def on_ready(self):
		print('Games cog is online!')
		await self.download_update()
		self.change_status.start()

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
	async def download_update(self, ctx=None, rall: str = 'no'):
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
			"Speech": "1lyP6tlNnTGOvFko5Zc6zVmIF-ijU12wP",
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


	# Leaves the channel
	@commands.command()
	@commands.has_permissions(administrator=True)
	async def leave(self, ctx):
		'''
		Makes the bot leave the voice channel.
		'''
		guild = ctx.message.guild
		voice_client = guild.voice_client

		if voice_client:
			await voice_client.disconnect()
			await ctx.send('**Disconnected!**')
		else:
			await ctx.send("**I'm not even in a channel, lol!**")


	@commands.cooldown(1, 7200, type=commands.BucketType.user)
	@commands.command(aliases=['language', 'language jungle', 'jungle', 'lj', 'play', 'p'])
	async def play_language(self, ctx):
		'''
		Plays the Language Jungle.
		'''
		member = ctx.author
		the_txt = discord.utils.get(member.guild.channels, id=language_jungle_txt_id)
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

		if self.active:
			self.client.get_command('play_language').reset_cooldown(ctx)
			return await ctx.send(f"**{member.mention}, someone is already playing!**")

		the_vc = discord.utils.get(member.guild.channels, id=language_jungle_vc_id)
		self.active = True
		self.member_id = member.id
		await self.start_game(member, the_txt)

	# Starts the Language Jungle game
	async def start_game(self, member: discord.Member, the_txt):
		
		voice = member.voice
		voice_client = member.guild.voice_client

		voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

		# Checks if the bot is in a voice channel
		if not voice_client:
			await voice.channel.connect()
			voice_client: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

		# Checks if the bot is in the same voice channel that the user
		if voice.channel == voice_client.channel:
			# get a random language audio
			path, language, audio = await self.get_random_language()

			# Plays the song
			if not voice_client.is_playing():
				audio_source = discord.FFmpegPCMAudio(path)
				await the_txt.send("**The round starts now!**")
				self.round += 1
				await the_txt.send(f"**`ROUND {self.round}`**")
				voice_client.play(audio_source, after=lambda e: self.client.loop.create_task(self.get_language_response(member, the_txt, language)))
		else:
			# (to-do) send a message to a specific channel
			await the_txt.send("**The bot is in a different voice channel!**")


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
	async def get_random_language(self) -> str:
		path = './language_jungle/Speech'
		all_languages = os.listdir(path)

		language = random.choice(all_languages)
		all_audios = os.listdir(f"{path}/{language}")
		audio = random.choice(all_audios)

		path = f"{path}/{language}/{audio}"
		return path, language, audio

	# Waits for a user response and checks whether it's right or wrong
	async def get_language_response(self, member: discord.Member, channel, language: str) -> str:
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
				we = '<:wrong:735625624714215588>'
				await channel.send(f"{we} **You got it `wrong`, {member.mention}!\nIt was {language}.** {we}")
				await channel.send("**-1 ❤️**")
				self.wrong_answers -= 1
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
					self.active = False
					self.round = 0
					await channel.send(f"💪 **End of the game, you did it, {member.mention}!** 💪")
					await channel.send(f"**__Your score__:\nRight answers: `{self.right_answers}`;\nWrong answers: `{self.wrong_answers}`.**")
					return await self.make_score_image(self.questions, channel)

			# Otherwise it ends the game and shows the score of the member
			else:
				self.active = False
				self.round = 0
				self.member_id = None
				await channel.send(f"☠️ **You lost, {member.mention}!** ☠️")
				await channel.send(f"**__Your score__:\nRight answers: `{self.right_answers}`;\nWrong answers: `{self.wrong_answers}`.**")
				return await self.make_score_image(self.questions, channel)


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
		background = Image.open("./language_jungle/Graphic/score.png")
		height = 160

		for k, v in questions.items():
		    try:
		        language = Image.open(f"./language_jungle/Graphic/answers/{v[0]}.png").resize((120, 40), Image.LANCZOS)
		        answer = Image.open(f"./language_jungle/Graphic/answers/{v[1]}.png").resize((120, 40), Image.LANCZOS)
		        #background.paste(language, (240, height), language)
		        #background.paste(answer, (410, height), answer)
		        background.paste(language, (240, height), language.convert('RGBA'))
		        background.paste(answer, (410, height), answer.convert('RGBA'))
		        #language
		        #answer
		    except Exception as error:
		        print(k)
		    finally:
		        height += 35

		draw = ImageDraw.Draw(background)
		draw.text((240, 130), "PC", (0, 196, 187), font=small)
		draw.text((410, 130), "YOU", (0, 196, 187), font=small)
		background.save('./language_jungle/Graphic/score_result.png')
		await channel.send(file=discord.File(path))
		self.questions.clear()
		try:
			await self.update_user_money(self.member_id, 20)
		except Exception:
			pass
		else:
			await channel.send(f"<:zslothmonopoly:705452184602673163> **20łł have been added into your account!** <:zslothmonopoly:705452184602673163>")
		finally:
			self.member_id = None			


	async def update_user_money(self, user_id: int, money: int):
		mycursor, db = await the_database()
		await mycursor.execute(f"UPDATE UserCurrency SET user_money = user_money + {money} WHERE user_id = {user_id}")
		await db.commit()
		await mycursor.close()

def setup(client):
	client.add_cog(Games(client))