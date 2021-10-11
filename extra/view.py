import discord
from discord.ext import commands
from typing import Optional, List, Union, Dict

class TheLanguageJungleMultiplayerView(discord.ui.View):
    """ Handles who joins and leaves the red/blue teams. """

    def __init__(self, cog, timeout: Optional[float]):
        super().__init__(timeout=timeout)
        self.cog = cog


    @discord.ui.button(label="Red Team", custom_id="red_team_id", emoji="🔴", style=discord.ButtonStyle.danger)
    async def red_team_button(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Makes the user join the red team. """

        member = interaction.user

        await interaction.response.defer()

        red_team = self.cog.multiplayer['teams']['red'][0]
        blue_team = self.cog.multiplayer['teams']['blue'][0]
        # Checks whether user is in the blue team
        if member.id in blue_team:
            if len(red_team) == 5:
                return await interaction.followup.send(
                    f"**You cannot join the red team because it's full, so you'll remain in the blue team, {member.mention}!**", ephemeral=True)

            else:
                try:
                    blue_team.remove(member.id)
                    red_team.append(member.id)
                except:
                    pass
                else:
                    await self.cog.update_multiplayer_message(interaction.message)
                    return await interaction.followup.send(f"**You switched to the red team, {member.mention}!**", ephemeral=True)

        # Checks whether user is in the red team
        if member.id in red_team:
            try:
                red_team.remove(member.id)
            except:
                pass
            else:
                await self.cog.update_multiplayer_message(interaction.message)
                return await interaction.followup.send(f"**You left the red team, {member.mention}!**", ephemeral=True)

        # member_state = member.voice
        # if not member_state or member_state.channel.id != self.vc.id:
        # 	return await msg.remove_reaction(reaction, member)

        if len(red_team) == 5:
            await interaction.followup.send(f"**The red team is already full, {member.mention}!**", ephemeral=True)
        else:
            red_team.append(member.id)
            await interaction.followup.send(f"**You joined the red team, {member.mention}!**", ephemeral=True)

        await self.cog.update_multiplayer_message(interaction.message)

    @discord.ui.button(label="Blue Team", custom_id="blue_team_id", emoji="🔵", style=discord.ButtonStyle.blurple)
    async def blue_team_button(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Makes the user join the blue team. """

        member = interaction.user

        await interaction.response.defer()

        blue_team = self.cog.multiplayer['teams']['blue'][0]
        red_team = self.cog.multiplayer['teams']['red'][0]
        # Checks whether user is in the red team

        if member.id in red_team:
            if len(blue_team) == 5:
                return await interaction.followup.send(
                    f"**You cannot join the red team because it's full, so you'll remain in the blue team, {member.mention}!**", ephemeral=True)

            else:
                try:
                    red_team.remove(member.id)
                    blue_team.append(member.id)
                except:
                    pass
                else:
                    await self.cog.update_multiplayer_message(interaction.message)
                    return await interaction.followup.send(f"**You switched to the blue team, {member.mention}!**", ephemeral=True)
                

        if member.id in blue_team:
            try:
                blue_team.remove(member.id)
            except:
                pass
            else:
                await self.cog.update_multiplayer_message(interaction.message)
                return await interaction.followup.send(f"**You left the blue team, {member.mention}!**", ephemeral=True)

        # member_state = member.voice
        # if not member_state or member_state.channel.id != self.vc.id:
        # 	return await msg.remove_reaction(reaction, member)

        if len(blue_team) == 5:
            await interaction.followup.send(f"**The blue team is already full, {member.mention}!**", ephemeral=True)
        else:
            blue_team.append(member.id)
            await interaction.followup.send(f"**You joined the blue team, {member.mention}!**", ephemeral=True)

        await self.cog.update_multiplayer_message(interaction.message)

    @discord.ui.button(label="See Teams", custom_id="see_teams_id", emoji="⬇️", style=discord.ButtonStyle.gray)
    async def see_teams_button(self, button: discord.ui.button, interaction: discord.Interaction) -> None:
        """ Shows all people in both teams """

        embed = discord.Embed(
            title="__Showing Both Teams:__",
            color=interaction.user.color
        )

        red_team = '\n'.join([f"<@{rm}>" for rm in self.cog.multiplayer['teams']['red'][0]])
        blue_team = '\n'.join([f"<@{bm}>" for bm in self.cog.multiplayer['teams']['blue'][0]])

        embed.add_field(name='🔴 __Red team__', value=red_team or 'No one.', inline=True)
        embed.add_field(name='🔵 __Blue team__', value=blue_team or 'No one.', inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

        

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # if not member_state or member_state.channel.id != self.cog.vc.id:
        # 	return await interaction.response.send(f"**You are not in the VC, {interaction.user.mention}!**")
        return await super().interaction_check(interaction)



class ChosenOptionButton(discord.ui.Button):
    """ Button of the soundboard. """

    def __init__(
        self, style: discord.ButtonStyle = discord.ButtonStyle.blurple, label: str = '\u200b', 
        emoji: Optional[Union[str, discord.Emoji, discord.PartialEmoji]] = None, custom_id: Optional[str] = None, row: Optional[int] = None) -> None:
        super().__init__(style=style, label=label, emoji=emoji, custom_id=custom_id, row=row, disabled=True)


    async def callback(self, interaction: discord.Interaction) -> None:
        """ Soundboard's button callback. """

        await interaction.response.defer()
        self.view.stop()
        new_story_path: str = f"{self.view.story_path}/{self.label}"
        await self.view.cog.start_ls_game_callback(new_story_path, self.view.member)

class ChooseOptionView(discord.ui.View):

    def __init__(self, cog: commands.Cog, member: discord.Member, story: Dict[str, str], story_path: str):
        super().__init__(timeout=None)
        self.cog = cog
        self.member = member
        self.story = story
        self.story_path = story_path

        for i, option in enumerate(self.story['options']):
            button: discord.ui.Button = ChosenOptionButton(style=discord.ButtonStyle.blurple, label=option, custom_id=f"option_{i+1}")
            self.add_item(button)