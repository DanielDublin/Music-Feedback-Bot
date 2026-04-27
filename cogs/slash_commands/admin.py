from discord.ext import commands
from discord import app_commands
from cogs.feedback_threads.modules.helpers import DiscordHelpers
from cogs.feedback_threads.modules.embeds import Embeds
import discord


async def extension_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=ext, value=ext)
        for ext in interaction.client.extensions
        if current.lower() in ext.lower()
    ][:25]


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helpers = DiscordHelpers(self.bot)
        self.embeds = Embeds(self.bot, self.helpers)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False
        return True

    group = app_commands.Group(name="mfpoints", description="Alter any user's points.", default_permissions=discord.Permissions(administrator=True), guild_only=True)

    @group.command(name='add', description="Use to add more points to a user.\n```/mfpoints add @user/user_id amount(optional)```")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member to add points to", points="Number of points to add (default: 1)")
    async def add(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        await interaction.response.defer(ephemeral=True)

        if points <= 0:
            await interaction.followup.send("You can only use positive numbers.", ephemeral=True)
            return

        feedback_cog = self.bot.get_cog("FeedbackThreads")
        thread_for_target_user = await feedback_cog.record_admin_adjustment(interaction, user)
        if thread_for_target_user is None:
            await interaction.followup.send("Could not create or retrieve feedback thread for this user.", ephemeral=True)
            return
        thread_info = feedback_cog.user_thread.get(user.id)
        ticket_counter = thread_info[1] if thread_info else 0

        await self.bot.db.add_points(str(user.id), points)
        current_points = int(await self.bot.db.fetch_points(str(user.id)))

        await interaction.followup.send("Done! The thread is here: <#"+str(thread_for_target_user.id)+">", ephemeral=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"ℹ️ {interaction.user.mention} has given {user.mention} {points} MF point."
                              f" They now have **{current_points}** MF point(s).",
                        inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await interaction.channel.send(embed=embed)

        mod_embed = await self.embeds.mod_add_points(interaction, user, ticket_counter, points=points)
        await thread_for_target_user.send(embed=mod_embed)

    @group.command(name='remove', description="Use to remove points from a user.\n```/mfpoints remove @user/user_id amount(optional)```")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member to remove points from", points="Number of points to remove (default: 1)")
    async def remove(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        await interaction.response.defer(ephemeral=True)

        if points <= 0:
            await interaction.followup.send("You can only use positive numbers.", ephemeral=True)
            return

        feedback_cog = self.bot.get_cog("FeedbackThreads")
        thread_for_target_user = await feedback_cog.record_admin_adjustment(interaction, user)
        if thread_for_target_user is None:
            await interaction.followup.send("Could not create or retrieve feedback thread for this user.", ephemeral=True)
            return
        thread_info = feedback_cog.user_thread.get(user.id)
        ticket_counter = thread_info[1] if thread_info else 0

        current_points = int(await self.bot.db.fetch_points(str(user.id)))

        if current_points - points >= 0:
            await self.bot.db.reduce_points(str(user.id), points)
            await interaction.followup.send("Done! The thread is here: <#"+str(thread_for_target_user.id)+">", ephemeral=True)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"{interaction.user.mention} has taken {points} MF point from {user.mention}."
                                  f" They now have **{current_points - points}** MF point(s).",
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            await interaction.channel.send(embed=embed)

            mod_embed = await self.embeds.mod_remove_points(interaction, user, ticket_counter, points=points)
            await thread_for_target_user.send(embed=mod_embed)

        else:
            await interaction.followup.send(
                f"Can't remove — {user.mention} only has **{current_points}** MF point(s).", ephemeral=True
            )

    @group.command(name="clear", description="Use to reset all the points from a user.\n```/mfpoints clear @user/user_id```")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="The member whose points to clear")
    async def clear(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        feedback_cog = self.bot.get_cog("FeedbackThreads")
        thread_for_target_user = await feedback_cog.record_admin_adjustment(interaction, user)
        if thread_for_target_user is None:
            await interaction.followup.send("Could not create or retrieve feedback thread for this user.", ephemeral=True)
            return
        thread_info = feedback_cog.user_thread.get(user.id)
        ticket_counter = thread_info[1] if thread_info else 0

        cleared_points = int(await self.bot.db.fetch_points(str(user.id)))

        await self.bot.db.reset_points(str(user.id))

        await interaction.followup.send("Done! The thread is here: <#"+str(thread_for_target_user.id)+">", ephemeral=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{interaction.user.mention} has cleared all of {user.mention}'s MF points. They now have **0** MF points.",
                        inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())

        await interaction.channel.send(embed=embed)

        mod_embed = await self.embeds.mod_clear_points(interaction, user, ticket_counter, cleared_points=cleared_points)
        await thread_for_target_user.send(embed=mod_embed)

    @app_commands.command(name="reload", description="Reload a bot extension by name")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(extension="Extension path (e.g. cogs.general)")
    @app_commands.autocomplete(extension=extension_autocomplete)
    async def reload_extension(self, interaction: discord.Interaction, extension: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(extension)
            await interaction.followup.send(f"Reloaded `{extension}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to reload `{extension}`: {e}", ephemeral=True)

    @app_commands.command(name="status", description="Show bot status")
    @app_commands.checks.has_permissions(administrator=True)
    async def status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        latency = round(self.bot.latency * 1000)
        cog_names = "\n".join(self.bot.cogs.keys()) or "none"
        embed = discord.Embed(title="Bot Status", color=0x7e016f)
        embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Cogs loaded", value=str(len(self.bot.cogs)), inline=True)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Loaded cogs", value=cog_names, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    # await bot.add_cog(Admin(bot), guild=discord.Object(id=SERVER_ID)) # for debug
    await bot.add_cog(Admin(bot))