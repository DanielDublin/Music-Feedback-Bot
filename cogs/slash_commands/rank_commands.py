import discord
import asyncio
import logging
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
from database.google_sheet import GoogleSheet
from data.constants import GENERAL_CHAT_CHANNEL_ID
from data.config import RANK_ORDER, LOWER_RANKS
from cogs.member_cards.add_rank_member_card import AddRankMemberCard
from cogs.feedback_threads.modules.check_rank_embed import PaginationView

logger = logging.getLogger(__name__)


class RankCommands(commands.Cog):
    def __init__(self, bot, google_sheet):
        self.bot = bot
        self.google_sheet = google_sheet
        self.add_rank_member_card = AddRankMemberCard(bot)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        return True

    # able to be used by admins + mods
    group = app_commands.Group(name="ranks", description="View the rank interface and commands", guild_only=True)

    # return current rank + when assigned
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    @group.command(name="current", description="Return the member's current rank and date given")
    @app_commands.describe(user="The member to look up")
    async def current_rank(self, interaction: discord.Interaction, user: discord.Member):
        
        await interaction.response.defer(thinking=True)
        # sort the roles from highest to lowest

        sorted_roles = sorted(user.roles, key=lambda role: role.position, reverse=True)

        top_role = sorted_roles[0]
        # checks that member has at least 2 roles
        second_role = sorted_roles[1] if len(sorted_roles) > 1 else None

        try:
            last_updated_date = await asyncio.to_thread(self.google_sheet.retrieve_time, user.id)
            # If AOTW is top, return second role
            # If no AOTW, return top role
            if top_role.name == "Artist of the Week" or top_role.name == "Moderators":
                if second_role:
                    calc_time = await asyncio.to_thread(self.google_sheet.calculate_time, user.id)
                    await interaction.followup.send(f"{user.mention} has the {second_role.mention} role. This role was added on: {last_updated_date} *({calc_time} days ago)*.", ephemeral=True)
                else:
                    await interaction.followup.send("This member has only one role.", ephemeral=True)
            else:
                calc_time = await asyncio.to_thread(self.google_sheet.calculate_time, user.id)
                await interaction.followup.send(f"{user.mention} has the {top_role.mention} role. This role was added on: {last_updated_date} *({calc_time} days ago)*.", ephemeral=True)
        except Exception:
            logger.error("Error in current_rank for %s", user.id, exc_info=True)
            await interaction.followup.send("An error occurred while fetching rank data.", ephemeral=True)

    # adds role to member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
    @group.command(name="add", description="Add role to member")
    @app_commands.describe(user="The member to rank up", role="The rank role to assign")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        await interaction.response.defer(thinking=True)

        try:
            # add to Google Sheet
            await asyncio.to_thread(self.google_sheet.add_user_spreadsheet, user.id, user.name)

            # define lower ranks
            # exclude Headliners/UF/Gilded/TRMFRs because they stay along with Headliners
            lower_rank_names = LOWER_RANKS

            if role in user.guild.roles:
                # check if the member already has the role
                if role in user.roles:
                    # get date role was added
                    last_updated_date = await asyncio.to_thread(self.google_sheet.retrieve_time, user.id, role.name)
                    calc_time = await asyncio.to_thread(self.google_sheet.calculate_time, user.id)
                    await interaction.followup.send(
                        f"{user.mention} already has {role.mention}. This role was added on: {last_updated_date} *({calc_time} days ago)*.")
                else:
                    # add the new role to the user
                    await user.add_roles(role, atomic=True)
                    # add role update to spreadsheet
                    await asyncio.to_thread(self.google_sheet.update_rank_spreadsheet, user.id, role.name, True)
                    await interaction.followup.send(f"{role.mention} was added to {user.mention}.")

                    # remove lower-ranked roles
                    roles_to_remove = [r for r in user.roles if r.name in lower_rank_names]
                    # checks if the roles to remove list is empty, and removes if present
                    if roles_to_remove:
                        await user.remove_roles(*roles_to_remove)

                    # send the member card with info in gen chat
                    try:
                        # needed to refresh user else it takes last role
                        user = await user.guild.fetch_member(user.id)
                        await self.add_rank_member_card.send_rank_member_card(user, role)
                        try:
                            await self.add_rank_member_card.rank_message(user, role)
                        except Exception:
                            logger.error("Error sending rank message", exc_info=True)
                    except Exception:
                        logger.error("Error sending rank member card", exc_info=True)
        except Exception:
            logger.error("Error in add_role for %s / %s", user.id, role.name, exc_info=True)
            await interaction.followup.send("An error occurred while adding the role.", ephemeral=True)


    # removes role from member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
    @group.command(name="remove", description="Remove role from member")
    @app_commands.describe(user="The member to rank down", role="The rank role to remove")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        await interaction.response.defer(thinking=True)

        try:
            # add to Google Sheet
            await asyncio.to_thread(self.google_sheet.add_user_spreadsheet, user.id, user.name)

            # define higher ranks
            higher_rank_names = RANK_ORDER

            if role in user.guild.roles:
                # check if member has role first
                if role not in user.roles:
                    await interaction.followup.send(f"{user.mention} does not have {role.mention}.")
                else:
                    await user.remove_roles(role, atomic=True)
                    # iterate through roles
                    if role.name in higher_rank_names:
                        index = higher_rank_names.index(role.name)
                        if index > 0:
                            new_role_name = higher_rank_names[index - 1]
                            new_role = discord.utils.get(user.guild.roles, name=new_role_name)
                            if new_role:
                                # add -1 from index of role
                                await user.add_roles(new_role)
                                # update spreadsheet
                                await asyncio.to_thread(self.google_sheet.update_rank_spreadsheet, user.id, new_role.name, False)
                                await interaction.followup.send(
                                    f"{role.mention} was removed from {user.mention}. They are now {new_role.mention}.")
                            else:
                                await interaction.followup.send(f"{role.mention} was removed from {user.mention}.")
                        else:
                            await interaction.followup.send(f"{role.mention} was removed from {user.mention}.")
                    else:
                        await interaction.followup.send(f"{role.mention} was removed from {user.mention}.")
            else:
                await interaction.followup.send(f"{role.mention} does not exist in this server.")
        except Exception:
            logger.error("Error in remove_role for %s / %s", user.id, role.name, exc_info=True)
            await interaction.followup.send("An error occurred while removing the role.", ephemeral=True)

    # gets rank history for member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: i.user.id)
    @group.command(name="history", description="Get rank history for member")
    @app_commands.describe(user="The member whose rank history to retrieve")
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        try:
            history = await asyncio.to_thread(self.google_sheet.get_history, user.id)
            if history:
                # format the history into a string
                history_message = '\n'.join(history)
                # embed formatting
                embed = discord.Embed(title="Rank History", color=0x7e016f)
                embed.add_field(name=f"{user.name}", value=f"{history_message}", inline=False)
                calc_time = await asyncio.to_thread(self.google_sheet.calculate_time, user.id)
                embed.add_field(name=f"Last Role Added: {calc_time} days ago.", value="", inline=False)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("User not in the database.")
        except Exception:
            logger.error("Error in history for %s", user.id, exc_info=True)
            await interaction.followup.send("An error occurred while fetching rank history.", ephemeral=True)

        # check for ranks added more than a week ago
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="check", description="Check for users with ranks that need updating")
    async def check_ranks(self, interaction: discord.Interaction):
        
        await interaction.response.defer(thinking=True)

        try:
            outdated_users = await self.google_sheet.get_outdated_for_all_users(interaction.guild)

            if outdated_users:
                today = datetime.now()

                # Categorize users by rank type with different time thresholds
                stagehands = []  # 1 week
                supporting_acts = []  # 3 weeks
                headliners = []  # 6 months
                ranked_down = []  # 1 month

                for user_data in outdated_users:
                    user_id = user_data['user_id']
                    last_role = user_data['last_role']
                    last_date_str = user_data['last_date']

                    # Calculate days since update
                    last_date = datetime.strptime(last_date_str, "%m/%d/%Y")
                    days = (today - last_date).days

                    # Get the member object for mention
                    member = interaction.guild.get_member(int(user_id))
                    user_mention = member.mention if member else user_data['username']

                    line = f"• {user_mention} - {last_role} ({days}d ago)"

                    # Categorize based on role and time threshold
                    if "Ranked up to Stagehands" in last_role and days >= 7:
                        stagehands.append(line)
                    elif "Ranked up to Supporting Acts" in last_role and days >= 21:  # 3 weeks
                        supporting_acts.append(line)
                    elif "Ranked up to Headliners" in last_role and days >= 180:  # 6 months
                        headliners.append(line)
                    elif "Ranked down" in last_role and days >= 30:  # 1 month
                        ranked_down.append(line)

                # Create pages for each category
                pages = []

                if stagehands:
                    embed = discord.Embed(
                        title="🎭 Stagehands (1+ week old)",
                        description='\n'.join(stagehands),
                        color=0x7e016f
                    )
                    embed.set_footer(text=f"Page 1 • {len(stagehands)} users")
                    pages.append(embed)

                if supporting_acts:
                    embed = discord.Embed(
                        title="🎸 Supporting Acts (3+ weeks old)",
                        description='\n'.join(supporting_acts),
                        color=0x7e016f
                    )
                    embed.set_footer(text=f"Page {len(pages) + 1} • {len(supporting_acts)} users")
                    pages.append(embed)

                if headliners:
                    embed = discord.Embed(
                        title="⭐ Headliners (6+ months old)",
                        description='\n'.join(headliners),
                        color=0x7e016f
                    )
                    embed.set_footer(text=f"Page {len(pages) + 1} • {len(headliners)} users")
                    pages.append(embed)

                if ranked_down:
                    embed = discord.Embed(
                        title="⬇️ Ranked Down (1+ month old)",
                        description='\n'.join(ranked_down),
                        color=0x7e016f
                    )
                    embed.set_footer(text=f"Page {len(pages) + 1} • {len(ranked_down)} users")
                    pages.append(embed)

                if pages:
                    # Create pagination view
                    view = PaginationView(pages)
                    message = await interaction.followup.send(embed=pages[0], view=view)
                    view.message = message
                else:
                    await interaction.followup.send("No users with ranks that need updating.")

            else:
                await interaction.followup.send("No users with ranks that need updating.")
        except Exception:
            logger.error("Error in check_ranks", exc_info=True)
            await interaction.followup.send("An error occurred while checking ranks.", ephemeral=True)

async def setup(bot):
    key_file_path = 'mf-bot-402714-b394f37c96dc.json'
    sheet_name = "MF BOT"
    google_sheet = GoogleSheet(key_file_path, sheet_name)
    await bot.add_cog(RankCommands(bot, google_sheet))