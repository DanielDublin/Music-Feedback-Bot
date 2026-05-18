"""Read-only MF Points queries for the General cog: <MFpoints and <MFtop."""

import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class QueriesImpl:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def show_points(self, ctx: commands.Context, user: discord.Member | None = None):
        if user is None:
            user = ctx.author

        guild = ctx.guild
        points = await self.bot.db.fetch_points(str(user.id))
        rank = await self.bot.db.fetch_rank(str(user.id))
        pfp = user.display_avatar.url

        msg_out1 = f"You have **{points}** MF point(s)."
        msg_out2 = f"Your MF Rank is **#{rank}** out of **{guild.member_count}**."
        if ctx.author.id != user.id:
            msg_out1 = f"{user.mention} has **{points}** MF point(s)."
            msg_out2 = f"Their MF Rank is **#{rank}** out of **{guild.member_count}**."

        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name=f"Music Feedback: {user.display_name}", icon_url=guild.icon.url)
        embed.set_thumbnail(url=pfp)
        embed.add_field(name="__MF Points__", value=msg_out1, inline=False)
        embed.add_field(name="__MF Rank__", value=msg_out2, inline=False)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await ctx.channel.send(embed=embed)

    async def show_top(self, ctx: commands.Context):
        top_users = await self.bot.db.fetch_top_users()
        guild = ctx.guild
        names = ''
        avatar = guild.icon.url

        for user_id, user_data in top_users.items():
            rank = user_data["rank"]
            points = user_data["points"]
            names += f"{rank} - <@{user_id}> | **{points}** MF point(s)\n"

            if rank == 1:
                user = discord.utils.get(guild.members, id=int(user_id))
                if user is not None:
                    avatar = user.display_avatar.url

        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name="Top Music Feedbackers", icon_url=guild.icon.url)
        embed.add_field(name="Members", value=names, inline=False)
        embed.set_thumbnail(url=avatar)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await ctx.channel.send(embed=embed)
