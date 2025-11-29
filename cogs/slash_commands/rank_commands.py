import discord
import asyncio
import datetime
from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
from database.google_sheet import GoogleSheet
from data.constants import GENERAL_CHAT_CHANNEL_ID
from cogs.member_cards.add_rank_member_card import AddRankMemberCard

class RankCommands(commands.Cog):
    def __init__(self, bot, google_sheet):
        self.bot = bot
        self.pfp_url = ""
        self.google_sheet = google_sheet
        self.add_rank_member_card = AddRankMemberCard(bot)

    # able to be used by admins + mods
    group = app_commands.Group(name="ranks", description="View the rank interface and commands")

    # return current rank + when assigned
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="current", description="Return the member's current rank and date given")
    async def current_rank(self, interaction: discord.Interaction, user: discord.Member):
        
        await interaction.response.defer(thinking=True)
        # sort the roles from highest to lowest

        sorted_roles = sorted(user.roles, key=lambda role: role.position, reverse=True)

        top_role = sorted_roles[0]
        # checks that member has at least 2 roles
        second_role = sorted_roles[1] if len(sorted_roles) > 1 else None

        # get the date the role was added
        last_updated_date = self.google_sheet.retrieve_time(user.id)
        # If AOTW is top, return second role
        # If no AOTW, return top role
        if top_role.name == "Artist of the Week" or top_role.name == "Moderators":
            if second_role:
                await interaction.followup.send(f"{user.mention} has the {second_role.mention} role. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.", ephemeral=True)
            else:
                await interaction.followup.send("This member has only one role.", ephemeral=True)
        else:
            await interaction.followup.send(f"{user.mention} has the {top_role.mention} role. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.", ephemeral=True)

    # adds role to member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="add", description="Add role to member")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        await interaction.response.defer(thinking=True)
        
        # add to Google Sheet
        self.google_sheet.add_user_spreadsheet(user.id, user.name)

        # define lower ranks
        # exclude Headliners/UF/Gilded/TRMFRs because they stay along with Headliners
        lower_rank_names = {"Groupies", "Stagehands", "Supporting Acts"}

        rank_options = ["Groupies", "Stagehands", "Supporting Acts", "Ultimate Fans", "Headliners", "MF Gilded", "The Real MFrs"]
        if role in user.guild.roles:
            # check if the member already has the role
            if role in user.roles:
                # get date role was added
                last_updated_date = self.google_sheet.retrieve_time(user.id, role.name)
                await interaction.followup.send(
                    f"{user.mention} already has {role.mention}. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.")
            else:
                # add the new role to the user
                await user.add_roles(role, atomic=True)
                # add role update to spreadsheet
                self.google_sheet.update_rank_spreadsheet(user.id, role.name, is_rankup = True)
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
                    except Exception as e:      
                        print(f"Error sending rank message: {e}")
                except Exception as e:
                    print(f"Error sending rank member card: {e}")


    # removes role from member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="remove", description="Remove role from member")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        await interaction.response.defer(thinking=True)

        # add to Google Sheet
        self.google_sheet.add_user_spreadsheet(user.id, user.name)

        # define higher ranks
        higher_rank_names = ["Groupies", "Stagehands", "Supporting Acts", "Headliners", "MF Gilded", "The Real MFrs"]

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
                            self.google_sheet.update_rank_spreadsheet(user.id, new_role, is_rankup = False)
                            await interaction.followup.send(
                                f"{role.mention} was removed from {user.mention}. They are now {new_role.mention}.")

    # gets rank history for member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="history", description="Get rank history for member")
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True)
        history = self.google_sheet.get_history(user.id)
        if history:
            # format the history into a string
            history_message = '\n'.join(history)
            # embed formatting
            embed = discord.Embed(title="Rank History", color=0x7e016f)
            embed.add_field(name=f"{user.name}", value=f"{history_message}", inline=False)
            embed.add_field(name=f"Last Role Added: {self.google_sheet.calculate_time(user.id)} days ago.", value="", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("User not in the database.")

    # check for ranks added more than a week ago
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="check", description="Check for users with ranks older than a week")
    async def check_ranks(self, interaction: discord.Interaction):
        
        await interaction.response.defer(thinking=True)

        # Get debug channel
        debug_channel = self.bot.get_channel(1137143797361422458)
        
        outdated_users = await self.google_sheet.get_outdated_for_all_users(interaction.guild)

        # Send debug info
        if debug_channel:
            await debug_channel.send(f"**Debug Info:**\nTotal outdated users found: {len(outdated_users)}")
            
            # Send the raw data
            for user_data in outdated_users[:10]:  # First 10 to avoid spam
                await debug_channel.send(f"```python\n{user_data}\n```")

        if outdated_users:
            embed = discord.Embed(title="Users that might need to be updated", color=0x7e016f)
            
            user_list = []
            today = datetime.now()
            
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
                
                user_list.append(f"• {user_mention} - {last_role} ({days}d ago)")
            
            # Split into chunks if too long
            combined_text = '\n'.join(user_list)
            
            if len(combined_text) <= 1024:
                embed.add_field(name="Outdated Ranks", value=combined_text, inline=False)
            else:
                # Split into multiple fields
                chunk = []
                chunk_length = 0
                field_num = 1
                
                for line in user_list:
                    if chunk_length + len(line) + 1 > 1024:  # +1 for newline
                        embed.add_field(name=f"Outdated Ranks (Part {field_num})", value='\n'.join(chunk), inline=False)
                        chunk = [line]
                        chunk_length = len(line)
                        field_num += 1
                    else:
                        chunk.append(line)
                        chunk_length += len(line) + 1
                
                # Add remaining chunk
                if chunk:
                    embed.add_field(name=f"Outdated Ranks (Part {field_num})", value='\n'.join(chunk), inline=False)
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("No users with ranks older than a week were found.")
            # Debug when nothing found
            if debug_channel:
                await debug_channel.send("⚠️ No outdated users found - checking why...")

async def setup(bot):
    key_file_path = 'mf-bot-402714-b394f37c96dc.json'
    sheet_name = "MF BOT"
    google_sheet = GoogleSheet(key_file_path, sheet_name)
    await bot.add_cog(RankCommands(bot, google_sheet))