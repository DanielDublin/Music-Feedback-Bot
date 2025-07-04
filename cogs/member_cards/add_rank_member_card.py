import discord
from discord.ext import commands
from cogs.slash_commands.get_member_card import GetMemberCard
from data.constants import GENERAL_CHAT_CHANNEL_ID, AOTW_SUBMISSIONS, FINISHED_MUSIC, RELEASE_PARTY, MODERATORS_CHANNEL_ID
import aiohttp
from PIL import Image, ImageDraw
import io
import emoji
from datetime import datetime

class AddRankMemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.get_member_card = GetMemberCard(bot)

    async def generate_mf_card(self, member: discord.Member, guild: discord.Guild):
        """Generate a member card file and view without sending it."""
        cog = self.bot.get_cog("MemberCards")
        if not cog:
            raise Exception("MemberCards cog is not loaded.")

        discord_username = member.display_name
        pfp_url = await cog.get_pfp(member)
        join_date = await cog.get_join_date(member)

        if isinstance(join_date, str):
            try:
                join_date = datetime.strptime(join_date, "%Y-%m-%d")
            except ValueError:
                join_date = datetime.now()

        rank_str = await cog.get_rank(member)
        is_top_feedback, numeric_points = False, 0
        try:
            is_top_feedback, numeric_points = await cog.get_points(member)
        except Exception as e:
            print(f"Error calling get_points for {member.display_name}: {str(e)}")

        all_main_genres_roles, all_daw_roles, all_instruments_roles = await cog.get_roles_by_colors(member)
        message_count = await cog.get_message_count(member)

        random_msg_content = "A true MFR"
        random_msg_url = None
        try:
            retrieved_msg_data = await cog.get_random_message(member)
            if retrieved_msg_data and isinstance(retrieved_msg_data, (tuple, list)) and len(retrieved_msg_data) >= 2:
                random_msg_content, random_msg_url = retrieved_msg_data[:2]
            else:
                print(f"Debug: Invalid retrieved_msg_data for {member.display_name}: {retrieved_msg_data}")
        except Exception as e:
            print(f"Error fetching random message for {member.display_name}: {str(e)}")
            random_msg_content = "An unexpected error occurred while looking for a message."

        last_music = await cog.get_last_finished_music(member)

        server_name = guild.name
        release_link = last_music if last_music and (last_music.startswith("http://") or last_music.startswith("https://")) else None

        img_width, img_height = 600, 300

        async with aiohttp.ClientSession() as session:
            async with session.get(pfp_url) as resp:
                if resp.status != 200:
                    print(f"Failed to fetch PFP for {member.display_name}. Status: {resp.status}")
                    pfp = Image.new("RGBA", (120, 120), (100, 100, 100, 255))
                else:
                    pfp_data = io.BytesIO(await resp.read())
                    pfp = Image.open(pfp_data).convert("RGBA").resize((120, 120), Image.Resampling.LANCZOS)

        mask = Image.new("L", pfp.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, *pfp.size), fill=255)
        pfp.putalpha(mask)

        animated = True
        card_buffer, file_ext, log_collector = self.get_member_card.generate_card(  # Updated unpacking
            pfp, discord_username, server_name, rank_str, numeric_points, message_count, join_date,
            (img_width, img_height), self.get_member_card.font_path, animated=animated, random_msg=random_msg_content,
            is_top_feedback=is_top_feedback,
            relevant_roles=[role.name for role in member.roles],
            all_genres_roles=all_main_genres_roles,
            all_daws_roles=all_daw_roles,
            all_instruments_roles=all_instruments_roles
        )

        filename = f"{discord_username}_mf_card.{file_ext}"
        file = discord.File(card_buffer, filename=filename)

        view = discord.ui.View()
        if release_link:
            view.add_item(discord.ui.Button(label=f"{discord_username}'s Latest Release", style=discord.ButtonStyle.link, url=release_link))
        if random_msg_url and random_msg_content not in ["A true MFR", "An unexpected error occurred while looking for a message."]:
            view.add_item(discord.ui.Button(label=emoji.emojize(":rocket:"), style=discord.ButtonStyle.link, url=random_msg_url))

        # Send logs to Discord if LOG_CHANNEL_ID is set
        if log_collector:
            await self.get_member_card.send_log_to_discord(log_collector, guild)

        return file, view

    async def view_mf_card(self, interaction: discord.Interaction, member: discord.Member = None):
        """Send a member card as a followup to the interaction."""
        if member is None:
            member = interaction.user
        guild = interaction.guild
        file, view = await self.generate_mf_card(member, guild)
        await interaction.followup.send(file=file, view=view)

    async def send_rank_member_card(self, user: discord.Member, role: discord.Role):
        """Send a member card to the general chat channel."""
        guild = user.guild  # Use user's guild instead of relying on interaction
        file_to_send, view_to_send = await self.generate_mf_card(user, guild)
        general_chat_channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)
        if general_chat_channel:
            await general_chat_channel.send(file=file_to_send, view=view_to_send)
            print(f"Member card sent to general chat for {user.display_name}")
        else:
            print("General chat channel not found.")

    async def rank_message(self, user, role):

        general_chat_channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)

        if role.name == "Stagehands":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **Stagehands** role!",
                color=discord.Color.from_rgb(178, 222, 236)
            )
            embed.add_field(
                name="",
                value="""
                You've been an active member for at least 2-3 days in the server.

                You can now:
                ♫ - Submit your music to <#{}>
                ♫ - Have full access to <#{}>

                """.format(AOTW_SUBMISSIONS, FINISHED_MUSIC),
                inline=False
            )
            embed.set_footer(text="MF Ranks are based on activity in the server. Deranking occurs after 1 month of inactivity.")

            await general_chat_channel.send(embed=embed)

        if role.name == "Supporting Acts":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **Supporting Acts** role!",
                color=discord.Color.from_rgb(250, 220, 170)
            )
            embed.add_field(
                name="", 
                value="""
                You've been an active member for at least 1-2 weeks and have participated in events in the server.

                You can now:
                ♫ - Submit your music to <#{}>
                ♫ - Have full access to <#{}>
                ♫ - Submit your new music to <#{}>
                """.format(AOTW_SUBMISSIONS, FINISHED_MUSIC, RELEASE_PARTY),
                inline=False
            )
            embed.set_footer(text="MF Ranks are based on activity in the server. Deranking occurs after 1 month of inactivity.")

            await general_chat_channel.send(embed=embed)

        if role.name == "Ultimate Fans":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **Ultimate Fans** role!",
                color=discord.Color.from_rgb(202, 114, 144)
            )
            embed.add_field(
                name="", 
                value="""
                You've been an active member for at least 1-2 weeks and have participated in events in the server, but do not make music.
                """,
                inline=False
            )
            embed.set_footer(text="MF Ranks are based on activity in the server. Deranking occurs after 1 month of inactivity.")

            await general_chat_channel.send(embed=embed)

        if role.name == "Headliners":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **Headliners** role!",
                color=discord.Color.from_rgb(179, 153, 212)
            )
            embed.add_field(
                name="", 
                value="""
                Thank you for making this server what it is! You've been an active member for at least 3-4 weeks and have participated in events and feedback in the server.

                You have full access to the server and can now:
                ♫ - Submit your music to <#{}>
                ♫ - Have full access to <#{}>
                ♫ - Submit your new music to <#{}>
                """.format(AOTW_SUBMISSIONS, FINISHED_MUSIC, RELEASE_PARTY),
                inline=False
            )
            embed.set_footer(text="MF Ranks are based on activity in the server. Deranking occurs after 1 month of inactivity.")

            await general_chat_channel.send(embed=embed)

        if role.name == "MF Gilded":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **MF Gilded** role!",
                color=discord.Color.from_rgb(140, 50, 230)
            )
            embed.add_field(
                name="",
                value="""
                Thank you for making this server what it is! You've been an active member for at least 6 months and have participated in events and feedback in the server.

                You have full access to the server and can now:
                ♫ - Submit your music to <#{}>
                ♫ - Have full access to <#{}>
                ♫ - Submit your new music to <#{}>
                """.format(AOTW_SUBMISSIONS, FINISHED_MUSIC, RELEASE_PARTY),
                inline=False
            )
            embed.set_footer(text="This is a permanent role. You will be given the rank again if you leave the server.")

            await general_chat_channel.send(embed=embed)


        if role.name == "The Real MFrs":
            embed = discord.Embed(
                title=f"🎉 Congrats, {user.display_name}!",
                description=f"Leveled up to the **The Real MFrs** role!",
                color=discord.Color.from_rgb(62, 53, 255)
            )
            embed.add_field(
                name="", 
                value="""
                Thank you for making this server what it is! You're an active member that truly embodies the mission of the server to help and teach music. You make an impact by being involved in events and feedback, as well as answering questions and welcoming new members.

                You have full access to the server and can now:
                ♫ - Submit your music to <#{}>
                ♫ - Have full access to <#{}>
                ♫ - Submit your new music to <#{}>
                """.format(AOTW_SUBMISSIONS, FINISHED_MUSIC, RELEASE_PARTY),
                inline=False
            )
            embed.set_footer(text="MF Ranks are based on activity in the server. Deranking occurs after 1 month of inactivity.")

            await general_chat_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AddRankMemberCard(bot))