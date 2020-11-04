import discord
from discord.ext import commands
import os

def get_token():
	with open('token.txt', 'r') as f:
		lines = f.readlines()
		return lines[0].strip()



intents = discord.Intents.all()
client = commands.Bot(command_prefix='zg!', intents=intents)
token = get_token()

@client.event
async def on_ready():
	print("Bot is ready!")

# Handles the errors
@client.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You can't do that!")

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please, inform all parameters!')

    
    if isinstance(error, commands.CommandOnCooldown):
        secs = error.retry_after
        if int(secs) >= 60:
            await ctx.send(f"You are on cooldown! Try again in {secs/60:.1f} minutes!")
        else:
            await ctx.send(error)

    if isinstance(error, commands.MissingAnyRole):
        await ctx.send(error)

    print(error)


@client.command()
@commands.has_permissions(administrator=True)
async def logout(ctx):
	await ctx.send("**Bye!**")
	await client.close()


@client.command()
@commands.has_permissions(administrator=True)
async def load(ctx, extension: str = None):
    '''
    Loads a cog.
    :param extension: The cog.
    '''
    if not extension:
        return await ctx.send("**Inform the cog!**")
    client.load_extension(f'cogs.{extension}')
    return await ctx.send(f"**{extension} loaded!**")


@client.command()
@commands.has_permissions(administrator=True)
async def unload(ctx, extension: str = None):
    '''
    Unloads a cog.
    :param extension: The cog.
    '''
    if not extension:
        return await ctx.send("**Inform the cog!**")
    client.unload_extension(f'cogs.{extension}')
    return await ctx.send(f"**{extension} unloaded!**")


@client.command()
@commands.has_permissions(administrator=True)
async def reload(ctx, extension: str = None):
    '''
    Reloads a cog.
    :param extension: The cog.
    '''
    if not extension:
        return await ctx.send("**Inform the cog!**")
    client.unload_extension(f'cogs.{extension}')
    client.load_extension(f'cogs.{extension}')
    return await ctx.send(f"**{extension} reloaded!**")


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')


client.run(token)