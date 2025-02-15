import discord
from discord.ext import commands
from discord import app_commands


class ThreadSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url = ""

    # return thread of user
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @app_commands.command(name="thread", description="Find the feedback thread for the users")
    async def search_rank(self, interaction: discord.Interaction, user: discord.Member):
        # Try to fetch the user from the guild using the user ID
        user = interaction.guild.get_member(user.id)

        if not user:
            await interaction.response.send_message(
                f"Could not find a user with ID {user}. Please ensure the ID is correct.")
            return

        # load the user_thread dict
        feedback_threads_cog = self.bot.get_cog("FeedbackThreads")
        if feedback_threads_cog:
            user_thread = await feedback_threads_cog.get_user_thread(user.id)
            thread_id = user_thread[0]

            if thread_id:
                await interaction.response.send_message(f"The thread for <@{user.id}> is <#{thread_id}>")
            else:
                # INCLUDE LOGIC FOR WHAT TO DO IF THREAD NOT FOUND
                await interaction.response.send_message(f"No active thread for <@{user.id}>.")


async def setup(bot):
    await bot.add_cog(ThreadSearch(bot))
