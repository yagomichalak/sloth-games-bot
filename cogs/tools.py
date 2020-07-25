import discord
from discord.ext import commands
import asyncio
import inspect
import io
import textwrap
import traceback
from contextlib import redirect_stdout

class Tools(commands.Cog):

	def __init__(self, client):
		self.client = client


	@commands.Cog.listener()
	async def on_ready(self):
		print("Tools cog is online!")


	@commands.command()
	@commands.has_permissions(administrator=True)
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