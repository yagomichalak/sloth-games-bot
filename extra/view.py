import discord
from discord.ext import commands
from typing import Optional

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

        print('Red team')
        red_team = self.cog.multiplayer['teams']['red'][0]
        blue_team = self.cog.multiplayer['teams']['blue'][0]
        # Checks whether user is in the blue team
        if member.id in blue_team:
            return await interaction.followup.send(f"**You cannot join the blue team because you're in the red team already, {member.mention}!**", ephemeral=True)

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
            return await interaction.followup.send(f"**You cannot join the red team because you're in the bçie team already, {member.mention}!**", ephemeral=True)

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

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # if not member_state or member_state.channel.id != self.cog.vc.id:
        # 	return await interaction.response.send(f"**You are not in the VC, {interaction.user.mention}!**")
        return await super().interaction_check(interaction)
