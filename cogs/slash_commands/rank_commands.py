import discord
from discord.ext import commands
from discord import app_commands
from database.google_sheet import GoogleSheet

class RankCommands(commands.Cog):
    def __init__(self, bot, google_sheet):
        self.bot = bot
        self.pfp_url = ""
        self.google_sheet = google_sheet

    # able to be used by admins + mods ---- UPDATE TO MODS LATER
    group = app_commands.Group(name="ranks", description="View the rank interface and commands",
                               default_permissions=discord.Permissions(administrator=True))

    # return current rank + when assigned
    @group.command(name="current", description="Return the member's current rank and date given")
    async def current_rank(self, interaction: discord.Interaction, user: discord.Member):
        # sort the roles from highest to lowest
        sorted_roles = sorted(user.roles, key=lambda role: role.position, reverse=True)

        top_role = sorted_roles[0]
        # checks that member has at least 2 roles
        second_role = sorted_roles[1] if len(sorted_roles) > 1 else None

        # If AOTW is top, return second role
        # If no AOTW, return top role
        if top_role.name == "Artist of the Week":
            if second_role:
                await interaction.response.send_message(f"{second_role.mention}")
            else:
                await interaction.response.send_message("This member has only one role.")
        else:
            await interaction.response.send_message(f"{top_role.mention}")

    # adds role to member
    @group.command(name="add", description="Add role to member")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        # add to Google Sheet
        self.google_sheet.add_user_spreadsheet(user.id, user.name)

        # define lower ranks
        lower_rank_names = {"groupies", "stagehands", "supporting acts"}

        if role in user.guild.roles:
            # check if the member already has the role
            if role in user.roles:
                await interaction.response.send_message(
                    f"{user.mention} already has {role.mention}. This role was added on: .")
            else:
                # add the new role to the user
                await user.add_roles(role, atomic=True)
                await interaction.response.send_message(f"{role.mention} was added to {user.mention} on .")
                # remove lower-ranked roles
                roles_to_remove = [r for r in user.roles if r.name in lower_rank_names]
                # checks if the roles to remove list is empty, and removes if present
                if roles_to_remove:
                    await user.remove_roles(*roles_to_remove)

    # removes role from member
    @group.command(name="remove", description="Remove role from member")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):

        # define higher ranks
        higher_rank_names = ["groupies", "stagehands", "supporting acts", "headliners", "TRMFRs"]

        if role in user.guild.roles:
            # check if member has role first
            # CHECK TO SEE IF THEY EVER HAD IT?
            if role not in user.roles:
                await interaction.response.send_message(f"{user.mention} does not have {role.mention}. This role was added on: .")
            else:
                await user.remove_roles(role, atomic=True)
                await interaction.response.send_message(f"{role.mention} was removed from {user.mention} on .")
                # iterate through roles
                if role.name in higher_rank_names:
                    index = higher_rank_names.index(role.name)
                    if index > 0:
                        new_role_name = higher_rank_names[index - 1]
                        new_role = discord.utils.get(user.guild.roles, name=new_role_name)
                        if new_role:
                            # add -1 from index of role
                            await user.add_roles(new_role)

async def setup(bot):
    key_file_path = '../Music-Feedback-Bot/mf-bot-402714-b394f37c96dc.json'
    sheet_name = "MF BOT"
    google_sheet = GoogleSheet(key_file_path, sheet_name)
    await bot.add_cog(RankCommands(bot, google_sheet))