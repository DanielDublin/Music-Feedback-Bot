import discord
import database.db as db
from discord.ext import commands
import json


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # add to db.py reset_points

    # Mod give points
    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def add(self, ctx: discord.Message, user: discord.Member, points: int = 1):

        await db.add_points(str(user.id), points)
        current_points = int(await db.fetch_points(str(user.id)))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"You have given {user.mention} {points} MF point."
                              f" They now have **{current_points}** MF point(s).",
                        inline=False)
        await ctx.send(embed=embed)

        # Mod remove points

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def remove(self, ctx: discord.Message, user: discord.Member, points: int = 1):
        current_points = int(await db.fetch_points(str(user.id)))

        if current_points - points >= 0:
            await db.reduce_points(str(user.id), points)
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"You have taken {points} MF point from {user.mention}."
                                  f" They now have **{current_points - points}** MF point(s).",
                            inline=False)
            await ctx.channel.send(embed=embed)

        else:
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"Can't remove points, This member already has **{current_points}** MF points.",
                            inline=False)
            await ctx.channel.send(embed=embed)

            # Mod clear points

    @commands.command(name="clear")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def clear(self, ctx: discord.Message, user: discord.Member):

        await db.reset_points(str(user.id))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{user.mention} has lost all their MF points. They now have **0** MF points.",
                        inline=False)
        await ctx.channel.send(embed=embed)

        # Mod migrate json

    @commands.command()
    @commands.is_owner()
    async def migrate(self, ctx: discord.Message):

        await ctx.channel.send("starting migration process")

        # Load the JSON file with nested dictionaries
        with open('MF Points.json', 'r') as json_file:
            data = json.load(json_file)

        await db.json_migration(data)
        await ctx.channel.send("finished migration process")

    # Mod migrate json
    @commands.command()
    @commands.is_owner()
    async def migrate_warnings(self, ctx: discord.Message):

        await ctx.channel.send("starting warning migration process")
        await db.migrate_warnings()
        await ctx.channel.send("finished warning migration process")


print("Processing complete")


async def setup(bot):
    await bot.add_cog(Admin(bot))
