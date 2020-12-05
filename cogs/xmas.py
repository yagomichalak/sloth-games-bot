import discord
from discord.ext import commands, tasks
from mysqldb import *
import random
import asyncio
from typing import List, Any, Union, Dict
import os
from itertools import cycle

from extra.xmas import items, questions



class Xmas(commands.Cog):
	""" A category for the TLS' Christmas-themed game. """

	def __init__(self, client) -> None:
		""" Class initializing method. """

		self.client = client
		self.xmas_channel_id: int = 784529877038399528
		# self.all_questions = cycle(random.shuffle(questions['all']))


	@commands.Cog.listener()
	async def on_ready(self) -> None:
		""" Tells when the cog is ready to use. """

		print('Tests cog is online')
		await self.drop_item()


	@commands.command(aliases=['score'])
	async def rank(self, ctx) -> None:

		member = ctx.author

		top_ten = await self._get_top_10_users()

		embed = discord.Embed(
			title="__Top 10 People w/ More Items__",
			color=member.color,
			timestamp=ctx.message.created_at
		)
		for i, top_user in enumerate(top_ten):
			user = self.client.get_user(top_user[0])
			embed.add_field(
				name=f"{i+1} - {user}", 
				value=f"```css\n#Items: [{top_user[1]}]```", 
				inline=False
			)
		
		you_user = await self._get_user_amount_of_items(member.id)
		embed.set_thumbnail(url=ctx.guild.icon_url)
		embed.set_footer(text=f"You: {you_user[1]} items")
		await ctx.send(embed=embed)


	@commands.command(aliases=["inv"])
	async def inventory(self, ctx) -> None:

		member = ctx.author

		embed = discord.Embed(
			title=f"{member}'s inventory",
			color=ctx.author.color,
			timestamp=ctx.message.created_at
		)


		user_items = await self._get_user_items_counted(member.id)
		embed_text = ""
		print(user_items)
		for ui in user_items:
			embed_text += f"**`{ui[4]}` {ui[1]} {ui[2]} `{ui[3].upper()}`**\n"

		embed.description = f"{embed_text}"
		await ctx.send(embed=embed)

	async def drop_item(self) -> None:
		""" Drops an item into the channel, but it requires a right answer to a random question for that. """

		while True:
			try:
				item_type, item =  await self.get_random_item()
				item_image = await self.get_item_image(item_type)
				question = await self.get_random_question()

				embed = await self.get_embed(item, item_type, item_image, question)

				channel = await self.client.fetch_channel(self.xmas_channel_id)
				om = await channel.send(embed=embed)
				user_got_right = await self.get_user_response(embed, channel, question['answer'], om, item['emoji'])

				if user_got_right:
					await self._add_item_to_user(user_got_right.id, item['name'], item_type, item['emoji'])

				print('nice!')
			except Exception as e:
				print(e)

			the_time = random.randint(5, 15)*60
			print("Time to next drop: " + str(the_time))
			await asyncio.sleep(the_time)

	async def get_embed(self, item: Dict[str, str], item_type: str, item_image: str, question: Dict[str, str]) -> discord.Embed:
		""" Makes the embedded message containing the question and the item.
		:param item: The name of the item.
		:param item_type: The type of the item.
		:param item_image: The image of the item based on its type.
		:param question: The question."""

		embed = discord.Embed(
			title=f"A new {item_type} item appeared! {item['emoji']}",
			description=f"**Answer the following question to get your prize:**\n{question['question']}",
			color=discord.Color.gold()
		)

		embed.set_image(url=item_image)

		return embed

	async def get_random_item(self) -> List[Union[str, Dict[str, str]]]:
		""" Gets a random item. """

		random_type = random.choice(list(items.keys()))
		random_item = random.choice(items[random_type])
		return random_type, random_item

	async def get_random_question(self) -> Dict[str, str]:
		""" Gets a random question. """

		random_question = random.choice(questions['all'])
		# random_question = next(self.all_questions)

		return random_question

	async def get_item_image(self, item_type: str) -> str:
		""" Gets an image link for the embedded message based on its type.
		:param item_type: The type of the item for which the image is gonna be. """

		images = {
			"Very Common": "https://cdn.discordapp.com/attachments/675668962385723393/783998401800044544/rare_3.png",
			"Common": "https://cdn.discordapp.com/attachments/675668962385723393/783998366681006080/rare_1.png",
			"Rare": "https://cdn.discordapp.com/attachments/675668962385723393/783998381701726208/rare_2.png"
		}

		return images[item_type]


	async def get_user_response(self, embed: discord.Embed, channel: discord.TextChannel, answer: str, om: discord.Message, emoji: str) -> List[Union[discord.Member, str, None]]:
		""" Gets user response for the question. 
		:param embed: The embed of the question.
		:param channel: The channel in which the question is. """

		def check(m) -> bool:
			if m.author.bot:
				return False

			print(answer)
			if m.channel.id == channel.id:
				if m.content.lower() == answer.lower():
					self.client.loop.create_task(m.add_reaction('✅'))
					# self.client.loop.create_task(channel.send(f"**{m.author.mention} got it right!**"))
					return True
				else:
					self.client.loop.create_task(m.add_reaction('❌'))
					return False
			else:
				return False

		try:
			msg = await self.client.wait_for('message', timeout=240, check=check)
		except asyncio.TimeoutError:
			embed.title = "The item got lost in Brazil!"
			embed.description = "It looks like no one answered the question on time..."
			embed.set_image(url='')
			embed.color = discord.Color.red()
			await om.edit(embed=embed)
			return None
		else:
			member = msg.author
			embed.description += f"""\n\n{member.mention} got it right, it was `{answer}`"""
			embed.color = discord.Color.green()
			await om.edit(embed=embed)
			await channel.send(f"**{member.mention} that is correct! You have won 1 {emoji.lower()}!**")
			return member
					
	# Database stuff

	async def _add_item_to_user(self, user_id: int, item_name: str, item_type: str, item_emoji: str) -> None:
		""" Adds an item to the user. 
		:param user_id: The ID of the user to whom to give the item.
		:param item_name: The name of the item that the user is gonna get.
		:param item_type: The type of the item that the user is gonna get. 
		:param item_emoji: The emoji that represents the item that the user is gonna get. """

		mycursor, db = await the_database()
		await mycursor.execute("INSERT INTO Xmas (user_id, item_name, item_type, item_emoji) VALUES (%s, %s, %s, %s)", (user_id, item_name, item_type, item_emoji))
		await db.commit()
		await mycursor.close()

	async def _delete_item_from_user(self) -> None: pass

	async def _get_top_10_users(self) -> List[List[str]]:
		""" Gets the top 10 users with more items. """

		mycursor, db = await the_database()
		await mycursor.execute("""
			SELECT user_id, COUNT(*) AS count
			FROM Xmas
			GROUP BY user_id DESC
			ORDER BY count
			LIMIT 10
			"""
			)
		top_ten = await mycursor.fetchall()
		await mycursor.close()
		return top_ten

	async def _get_user_by_id(self, user_id: int) -> List[str]:
		""" Gets the a user from the database. """

		mycursor, db = await the_database()
		await mycursor.execute("SELECT * FROM Xmas WHERE user_id = %s", (user_id,))
		user = await mycursor.fetchall()
		await mycursor.close()
		return user

	async def _get_user_amount_of_items(self, user_id: int) -> List[str]:
		""" Gets the a user with the amount of items that they have. 
		:param user_id: The ID of the user whose items are gonna be amounted and retrieved. """

		mycursor, db = await the_database()
		await mycursor.execute("""
			SELECT user_id, COUNT(*) AS count
			FROM Xmas
			WHERE user_id = %s
			GROUP BY user_id
			""", (user_id,)
		)
		top_ten = await mycursor.fetchone()
		await mycursor.close()
		return top_ten

	async def _get_user_items_counted(self, user_id: int) -> List[List[Union[int, str]]]:
		""" Gets the user items counted and grouped by item_name. 
		:param user_id: The ID of the user whose items are gonna be counted and retrieved. """

		mycursor, db = await the_database()
		await mycursor.execute("""
			SELECT user_id, item_name, item_emoji, item_type, COUNT(item_name) AS count
			FROM Xmas WHERE user_id = %s
			GROUP BY item_name;
		""", (user_id,))
		user_items = await mycursor.fetchall()
		await mycursor.close()
		return user_items


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def create_xmas_table(self, ctx) -> None:
		""" Creates the Xmas table. """

		if await self._xmas_table_exists():
			return await ctx.send("**Table __Xmas__ already exists!**")

		mycursor, db = await the_database()
		await mycursor.execute("CREATE TABLE Xmas (user_id BIGINT NOT NULL, item_name VARCHAR(20), item_type VARCHAR(20), item_emoji VARCHAR(50))")
		await db.commit()
		await mycursor.close()

		await ctx.send("**Table __Xmas__ created!**")


	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def drop_xmas_table(self, ctx) -> None:
		""" Drops the Xmas table. """

		if await self._xmas_table_exists():
			return await ctx.send("**Table __Xmas__ doesn't exist!**")

		mycursor, db = await the_database()
		await mycursor.execute("DROP TABLE Xmas")
		await db.commit()
		await mycursor.close()

		await ctx.send("**Table __Xmas__ dropped!**")

	@commands.command(hidden=True)
	@commands.has_permissions(administrator=True)
	async def reset_xmas_table(self, ctx) -> None:
		""" Resets the Xmas table. """

		if not await self._xmas_table_exists():
			return await ctx.send("**Table __Xmas__ doesn't exist yet!**")

		mycursor, db = await the_database()
		await mycursor.execute("DELETE FROM Xmas")
		await db.commit()
		await mycursor.close()

		await ctx.send("**Table __Xmas__ reset!**")

	async def _xmas_table_exists(self) -> bool:
		""" Checks whether the Xmas table exists. """

		mycursor, db = await the_database()
		await mycursor.execute("SHOW TABLE STATUS LIKE `Xmas`")
		exists = await mycursor.fetchone()
		await mycursor.close()
		if exists:
			return True
		else:
			return False



def setup(client) -> None:
	""" Cog's setup function. """

	client.add_cog(Xmas(client))