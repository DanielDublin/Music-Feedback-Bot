import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from cogs.aotw.create_poll import CreatePoll


class AotwVoting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name = "voting", description = "Setup poll and channels for AOTW voting")
    async def hello_command(self, interaction):
        await interaction.response.send_message("Hello! take 2")

        channel_id = 1103427357781528597

        poll = CreatePoll(self.bot)
        names = await poll.scrape_channel_for_names(interaction, channel_id)
        embed, emojis = await poll.create_embed(interaction, names)
        await poll.react_to_embed(interaction, embed, emojis, names)




async def setup(bot):
    await bot.add_cog(AotwVoting(bot))

