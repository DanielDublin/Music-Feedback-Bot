import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from cogs.aotw.create_poll import CreatePoll
from cogs.aotw.configure_channel import ConfigureChannel
from data.constants import AOTW_CHANNEL, AOTW_SUBMISSIONS


class AOTWEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name = "aotw_voting", description = "Setup poll and channels for AOTW voting")
    async def aotw_voting(self, interaction):

        channel_id = 1383539110945489070

        await interaction.response.defer()
        config = ConfigureChannel(self.bot)

        await config.initialize_channels()

        # check aotw_channel announcement and post
        formatted_six_months = await config.calculate_six_months()
        await config.check_aotw_channel_announcement(formatted_six_months)

        # change perms for aotw submissions
        await config.change_voting_perms()

        # change name + topic to aotw_voting
        await config.change_name()

        # delete any messages with a file
        await config.check_for_not_links()

        # see if i can see the date of the files with metadata of link?

        # create the poll in aotw submissions
        poll = CreatePoll(self.bot)
        names = await poll.scrape_channel_for_names(interaction, channel_id)
        embed, emojis = await poll.create_embed(interaction, names)
        await poll.react_to_embed(interaction, embed, emojis, names)

        # send announcement under poll
        await config.send_voting_announcement()

        # create event for voting
        await config.schedule_voting_event()

        # reminders for gen chat
        await config.schedule_general_chat_reminders()


    @app_commands.command(name = "aotw_submissions", description = "Setup poll and channels for AOTW submissions")
    async def aotw_submissions(self, interaction):

        await interaction.response.defer()
        config = ConfigureChannel(self.bot)

        channel_id = 1103427357781528597

        config = ConfigureChannel(self.bot)
        await config.configure_channel(interaction, channel_id)

        poll = CreatePoll(self.bot)
        names = await poll.scrape_channel_for_names(interaction, channel_id)
        embed, emojis = await poll.create_embed(interaction, names)
        await poll.react_to_embed(interaction, embed, emojis, names)




async def setup(bot):
    await bot.add_cog(AOTWEvent(bot))

