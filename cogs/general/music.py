"""Band lookups for the General cog: <MFgenres and <MFsimilar."""

import logging

import discord
from discord.ext import commands

from modules.genres import fetch_band_genres
from modules.similar_bands import fetch_similar_bands

logger = logging.getLogger(__name__)


class MusicLookupImpl:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def show_genres(self, ctx: commands.Context, band_name: str):
        result, thumbnail_url = await fetch_band_genres(band_name)

        embed = discord.Embed(color=0x7e016f)
        embed.title = 'Genre Check'
        embed.add_field(name=f"{band_name.title()}:", value=result, inline=False)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await ctx.channel.send(embed=embed)

    async def show_similar(self, ctx: commands.Context, band_name: str):
        result, thumbnail_url = await fetch_similar_bands(band_name)

        embed = discord.Embed(color=0x7e016f)
        embed.title = 'Similar bands'
        embed.add_field(name=f"{band_name.title()}:", value=result, inline=False)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await ctx.channel.send(embed=embed)
