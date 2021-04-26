import discord
from discord.ext import commands
import asyncio
import inspect
import io
import textwrap
import traceback
from contextlib import redirect_stdout
import os
from treelib import Node, Tree

class Tools(commands.Cog):

	def __init__(self, client):
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self):
		print("Tools cog is online!")


	@staticmethod
	async def send_big_message(title, channel, message, color):
		""" Sends a big message to a given channel. """

		if (len(message) <= 2048):
			embed = discord.Embed(title=title, description=message, color=discord.Colour.green())
			await channel.send(embed=embed)
		else:
			embedList = []
			n = 2048
			embedList = [message[i:i + n] for i in range(0, len(message), n)]
			for num, item in enumerate(embedList, start=1):
				if (num == 1):
					embed = discord.Embed(title=title, description=item, color=discord.Colour.green())
					embed.set_footer(text=num)
					await channel.send(embed=embed)
				else:
					embed = discord.Embed(description=item, color=discord.Colour.green())
					embed.set_footer(text=num)
					await channel.send(embed=embed)

	@commands.command(aliases=['show_tree', 'file_tree', 'showtree', 'filetree', 'sft', 'listfiles'])
	@commands.has_permissions(administrator=True)
	@commands.cooldown(1, 5, commands.BucketType.user)
	async def show_file_tree(self, ctx, path: str = None) -> None:
		""" Shows the file tree. """

		if not path:
			path = './'

		path = path.replace('../', '')

		if not os.path.isdir(path):
			return await ctx.send(f"**Invalid path, {ctx.author.mention}!**")

		tree = Tree()

		ignore_files = ['venv', '__pycache__', '.git', '.gitignore']

		tree.create_node('Root' if path == './' else path, 'root')

		for file in os.listdir(path):
			if file in ignore_files:
				continue

			if os.path.isdir(file):
				tree.create_node(file, file, parent='root')
				for subfile in (directory := os.listdir(f'./{file}')):
					if subfile in ignore_files:
						continue
					tree.create_node(subfile, parent=file)

			else:
				tree.create_node(file, parent='root')

		await Tools.send_big_message('File Tree', ctx.channel, str(tree), discord.Color.green())


	@commands.command()
	@commands.is_owner()
	async def eval(self, ctx, *, body = None):
		'''
		(ADM) Executes a given command from Python onto Discord.
		:param body: The body of the command.
		'''
		if not body:
			return await ctx.send("**Please, inform the code body!**")

		"""Evaluates python code"""
		env = {
			'ctx': ctx,
			'client': self.client,
			'channel': ctx.channel,
			'author': ctx.author,
			'guild': ctx.guild,
			'message': ctx.message,
			'source': inspect.getsource
		}

		def cleanup_code(content):
			"""Automatically removes code blocks from the code."""
			# remove ```py\n```
			if content.startswith('```') and content.endswith('```'):
				return '\n'.join(content.split('\n')[1:-1])

			# remove `foo`
			return content.strip('` \n')

		def get_syntax_error(e):
			if e.text is None:
				return f'```py\n{e.__class__.__name__}: {e}\n```'
			return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

		env.update(globals())

		body = cleanup_code(body)
		stdout = io.StringIO()
		err = out = None

		to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

		def paginate(text: str):
			'''Simple generator that paginates text.'''
			last = 0
			pages = []
			for curr in range(0, len(text)):
				if curr % 1980 == 0:
					pages.append(text[last:curr])
					last = curr
					appd_index = curr
			if appd_index != len(text)-1:
				pages.append(text[last:curr])
			return list(filter(lambda a: a != '', pages))

		try:
			exec(to_compile, env)
		except Exception as e:
			err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
			return await ctx.message.add_reaction('\u2049')

		func = env['func']
		try:
			with redirect_stdout(stdout):
				ret = await func()
		except Exception as e:
			value = stdout.getvalue()
			err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
		else:
			value = stdout.getvalue()
			if ret is None:
				if value:
					try:

						out = await ctx.send(f'```py\n{value}\n```')
					except:
						paginated_text = paginate(value)
						for page in paginated_text:
							if page == paginated_text[-1]:
								out = await ctx.send(f'```py\n{page}\n```')
								break
							await ctx.send(f'```py\n{page}\n```')
			else:
				try:
					out = await ctx.send(f'```py\n{value}{ret}\n```')
				except:
					paginated_text = paginate(f"{value}{ret}")
					for page in paginated_text:
						if page == paginated_text[-1]:
							out = await ctx.send(f'```py\n{page}\n```')
							break
						await ctx.send(f'```py\n{page}\n```')

		if out:
			await ctx.message.add_reaction('\u2705')  # tick
		elif err:
			await ctx.message.add_reaction('\u2049')  # x
		else:
			await ctx.message.add_reaction('\u2705')

def setup(client):
	client.add_cog(Tools(client))