import discord
import database.db as db
from discord.ext import commands
from discord import app_commands
import json
from discord.utils import get


class RankCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url = ""

    # able to be used by admins + mods ---- UPDATE TO MODS LATER
    group = app_commands.Group(name="ranks", description="View the rank interface and commands",
                               default_permissions=discord.Permissions(administrator=True))

    # return current rank + when assigned
    @group.command(name="current", description="Return the member's current rank and date given")
    async def current_rank(self, interaction: discord.Interaction, user: discord.Member):
        # sort the roles from highest to lowest
        sorted_roles = sorted(user.roles, key=lambda role: role.position, reverse=True)

        top_role = sorted_roles[0]
        # checks that member has at least 2 roles
        second_role = sorted_roles[1] if len(sorted_roles) > 1 else None

        # If AOTW is top, return second role
        # If no AOTW, return top role
        if top_role.name == "Artist of the Week":
            if second_role:
                await interaction.response.send_message(f"{second_role.mention}")
            else:
                await interaction.response.send_message("This member has only one role.")
        else:
            await interaction.response.send_message(f"{top_role.mention}")

    # adds role to member
    @group.command(name="add", description="Add role to member")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if role in user.guild.roles:
            # check if member has role first
            if role in user.roles:
                await interaction.response.send_message(f"{user.mention} already has {role.mention}. This role was added on: .")
            else:
                await user.add_roles(role, atomic=True)
                await interaction.response.send_message(f"{role.mention} was added to {user.mention} on .")



async def setup(bot):
    # await bot.add_cog(RankCommands(bot), guild=discord.Object(id=SERVER_ID)) # for debug
    await bot.add_cog(RankCommands(bot))