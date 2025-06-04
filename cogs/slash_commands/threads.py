import discord
from discord.ext import commands
from discord import app_commands
from ..feedback_threads.modules.helpers import DiscordHelpers

class ThreadSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url = ""

    group = app_commands.Group(name="threads", description="View the threads commands")

    @app_commands.checks.has_any_role('Admins', 'Moderators', 'Chat Moderators')
    @group.command(name="search", description="Get the feedback thread for the user")
    async def search_threads(self, interaction: discord.Interaction, user: discord.Member):

        await interaction.response.defer(thinking=True)

        thread_id = await DiscordHelpers.get_thread_id_no_ctx(self.bot, user.id)

        if thread_id:
            await interaction.followup.send(f"The thread for <@{user.id}> is <#{thread_id}>")
        else:
            await interaction.followup.send(f"No active thread for <@{user.id}>.")
        
    @app_commands.checks.has_any_role('Admins', 'Moderators', 'Chat Moderators')
    @group.command(name="delete", description="Delete thread for the user")
    async def search_all_threads(self, interaction: discord.Interaction, user: discord.Member):

        await interaction.response.defer(thinking=True)

        thread_id = await DiscordHelpers.get_thread_id_no_ctx(self.bot, user.id)

        if thread_id:

            thread = await self.bot.fetch_channel(thread_id)
            await thread.delete()

            # Delete the original message that started the thread:
            parent_channel = thread.parent
            if parent_channel:
                message = await parent_channel.fetch_message(thread.id) 
                await message.delete()

            # Delete the user from the dictionary and db
            await DiscordHelpers.delete_user_from_user_thread(self.bot, user.id)
            await DiscordHelpers.delete_user_from_db(self.bot, user.id)

            await interaction.followup.send(f"The thread for <@{user.id}> has been deleted.")
        else:
            await interaction.followup.send(f"No active thread for <@{user.id}>.")

async def setup(bot):
    await bot.add_cog(ThreadSearch(bot))
