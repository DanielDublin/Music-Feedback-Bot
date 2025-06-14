import discord
from discord.ext import commands
from discord import app_commands

class GetMemberCard(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    mf_card_group = app_commands.Group(name="mf", description="View your MF Card related commands.")

    @mf_card_group.command(name="card", description="View a member's MF Card.")
    @app_commands.describe(member="The member whose MF Card you want to view (defaults to you).")
    async def view_mf_card(self, interaction: discord.Interaction, member: discord.Member = None):


        await interaction.response.defer() 

        if member is None:
            member = interaction.user 

        member_cards_cog = self.bot.get_cog("MemberCards")
        if not member_cards_cog:
            await interaction.followup.send("Error: MemberCards cog is not loaded. Please contact an admin.", ephemeral=True)
            return

        username = await member_cards_cog.get_username(member)
        pfp = await member_cards_cog.get_pfp(member)
        join_date = await member_cards_cog.get_join_date(member)
        rank = await member_cards_cog.get_rank(member)
        points = await member_cards_cog.get_points(member)
        message_count = await member_cards_cog.get_message_count(member)
        random_message = await member_cards_cog.get_random_message(member)
        finished_music = await member_cards_cog.get_last_finished_music(member)

        response_text = f"--- **{username}'s MF Card** ---\n"
        response_text += f"**User ID:** {username}\n"
        response_text += f"**Profile Picture URL:** <{pfp}>\n" # Enclose URL in <> to make it clickable
        response_text += f"**Joined Discord:** {join_date}\n"
        response_text += f"**Rank:** {rank}\n"
        response_text += f"**Points:** {points}\n"
        response_text += f"**Message Count:** {message_count}\n"
        response_text += f"**Finished Music: {finished_music}\n"

        if random_message and random_message != "No random message available.":
            response_text += f"**Random Message:** \"{random_message}\"\n"
        else:
            response_text += f"**Random Message:** N/A\n"
        response_text += "------------------------"

        # Send the entire plain text message using interaction.followup.send().
        await interaction.followup.send(response_text)

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(GetMemberCard(bot))