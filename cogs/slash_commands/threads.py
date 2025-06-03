import discord
from discord.ext import commands
from discord import app_commands
from ..feedback_threads.modules.helpers import DiscordHelpers


class ThreadSearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url = ""

    ALLOWED_ROLES = {"Admins", "Moderators", "Chat Moderators"}

    @app_commands.command(name="thread", description="Find the feedback thread for the user")
    async def search_threads(self, interaction: discord.Interaction, user: discord.Member):

        # check roles
        invoker_roles = {role.name for role in interaction.user.roles}
        if not invoker_roles.intersection(self.ALLOWED_ROLES):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
            return

        thread_id = await DiscordHelpers.get_thread_id_no_ctx(self.bot, user.id)

        if thread_id:
            await interaction.response.send_message(f"The thread for <@{user.id}> is <#{thread_id}>")
        else:
            await interaction.response.send_message(f"No active thread for <@{user.id}>.")
        

    # @app_commands.command(name="delete_thread", description="Find the feedback thread for the user")
    # async def delete_threads(self, interaction: discord.Interaction, user: discord.Member):

    #     # check roles
    #     invoker_roles = {role.name for role in interaction.user.roles}
    #     if not invoker_roles.intersection(self.ALLOWED_ROLES):
    #         await interaction.response.send_message(
    #             "You don't have permission to use this command.",
    #             ephemeral=True
    #         )
    #         return
        
    #     await DiscordHelpers.delete_user_from_user_thread(user.id)
    #     await DiscordHelpers.delete_user_from_db(user.id)

    #     await interaction.response.send_message(f"Deleted thread in database and user_thread for <@{user.id}>")
            
    


async def setup(bot):
    await bot.add_cog(ThreadSearch(bot))
