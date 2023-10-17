import discord
import database.db as db
from discord.ext import commands
from discord import app_commands
import json
from data.constants import SERVER_ID


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    group = app_commands.Group(name="mfpoints", description="Alter any user's points.", default_permissions=discord.Permissions(administrator=True))
    
    # Mod give points
    @group.command(name='add')
    async def add(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return


        await db.add_points(str(user.id), points)
        current_points = int(await db.fetch_points(str(user.id)))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{interaction.user.mention} has given {user.mention} {points} MF point."
                              f" They now have **{current_points}** MF point(s).",
                        inline=False)
        await interaction.response.send_message("Done!", ephemeral=True)
        await interaction.channel.send(embed=embed)

        # Mod remove points

    @group.command(name='remove')
    async def remove(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return


        current_points = int(await db.fetch_points(str(user.id)))

        if current_points - points >= 0:
            await db.reduce_points(str(user.id), points)
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"{interaction.user.mention} has taken {points} MF point from {user.mention}."
                                  f" They now have **{current_points - points}** MF point(s).",
                            inline=False)
            await interaction.response.send_message("Done!", ephemeral=True)
            await interaction.channel.send(embed=embed)

        else:
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"Can't remove points, This member already has **{current_points}** MF points.",
                            inline=False)
            await interaction.response.send_message("Nope!", ephemeral=True)
            await interaction.channel.send(embed=embed)

            # Mod clear points

    @group.command(name="clear")
    async def clear(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return


        await db.reset_points(str(user.id))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{interaction.user.mention} has cleared all of {user.mention}'s MF points. They now have **0** MF points.",
                        inline=False)
        await interaction.response.send_message("Done!", ephemeral=True)
        await interaction.channel.send(embed=embed)

print("Processing complete")


async def setup(bot):
    await bot.add_cog(Admin(bot), guild=discord.Object(id=SERVER_ID))
