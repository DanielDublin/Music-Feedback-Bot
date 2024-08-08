import discord
from discord.ext import commands
from discord import app_commands
from database.google_sheet import GoogleSheet

class RankCommands(commands.Cog):
    def __init__(self, bot, google_sheet):
        self.bot = bot
        self.pfp_url = ""
        self.google_sheet = google_sheet

    # able to be used by admins + mods
    group = app_commands.Group(name="ranks", description="View the rank interface and commands")

    # return current rank + when assigned
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="current", description="Return the member's current rank and date given")
    async def current_rank(self, interaction: discord.Interaction, user: discord.Member):
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
                await interaction.response.send_message(f"{user.mention} has the {second_role.mention} role. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.", ephemeral=True)
            else:
                await interaction.response.send_message("This member has only one role.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.mention} has the {top_role.mention} role. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.", ephemeral=True)

    # adds role to member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="add", description="Add role to member")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
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
                await interaction.response.send_message(
                    f"{user.mention} already has {role.mention}. This role was added on: {last_updated_date} *({self.google_sheet.calculate_time(user.id)} days ago)*.")
            else:
                # add the new role to the user
                await user.add_roles(role, atomic=True)
                # add role update to spreadsheet
                self.google_sheet.add_rank_spreadsheet(user.id, role)
                await interaction.response.send_message(f"{role.mention} was added to {user.mention}.")

                # remove lower-ranked roles
                roles_to_remove = [r for r in user.roles if r.name in lower_rank_names]
                # checks if the roles to remove list is empty, and removes if present
                if roles_to_remove:
                    await user.remove_roles(*roles_to_remove)

    # removes role from member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="remove", description="Remove role from member")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):

        # add to Google Sheet
        self.google_sheet.add_user_spreadsheet(user.id, user.name)

        # define higher ranks
        higher_rank_names = ["Groupies", "Stagehands", "Supporting Acts", "Headliners", "MF Gilded", "The Real MFrs"]

        if role in user.guild.roles:
            # check if member has role first
            if role not in user.roles:
                await interaction.response.send_message(f"{user.mention} does not have {role.mention}.")
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
                            self.google_sheet.remove_rank_spreadsheet(user.id, new_role)
                            await interaction.response.send_message(
                                f"{role.mention} was removed from {user.mention}. They are now {new_role.mention}.")

    # gets rank history for member
    @app_commands.checks.has_any_role('Admins', 'Moderators')
    @group.command(name="history", description="Get rank history for member")
    async def history(self, interaction: discord.Interaction, user: discord.Member):
        history = self.google_sheet.get_history(user.id)
        if history:
            # format the history into a string
            history_message = '\n'.join(history)
            # embed formatting
            embed = discord.Embed(title="Rank History", color=0x7e016f)
            embed.add_field(name=f"{user.name}", value=f"{history_message}", inline=False)
            embed.add_field(name=f"Last Role Added: {self.google_sheet.calculate_time(user.id)} days ago.", value="", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("User not in the database.")

async def setup(bot):
    key_file_path = '../Music-Feedback-Bot/mf-bot-402714-b394f37c96dc.json'
    sheet_name = "MF BOT"
    google_sheet = GoogleSheet(key_file_path, sheet_name)
    await bot.add_cog(RankCommands(bot, google_sheet))