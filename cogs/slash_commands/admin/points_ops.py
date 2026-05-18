"""Admin /mfpoints implementation: add, remove, clear.

Each entry point performs the DB mutation, posts a public channel embed, and
mirrors a moderation embed into the target user's feedback thread (created
on demand via FeedbackThreads.record_admin_adjustment).

The signature cog (cogs/slash_commands/admin/__init__.py) owns the
app_commands.Group and @group.command decorators and delegates here.
"""

import logging

import discord
from discord.ext import commands

from cogs.feedback_threads.modules.embeds import Embeds
from cogs.feedback_threads.modules.helpers import DiscordHelpers

logger = logging.getLogger(__name__)


class AdminPointsImpl:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.helpers = DiscordHelpers(bot)
        self.embeds = Embeds(bot, self.helpers)

    async def handle_add(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
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

        await interaction.followup.send("Done! The thread is here: <#" + str(thread_for_target_user.id) + ">", ephemeral=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"ℹ️ {interaction.user.mention} has given {user.mention} {points} MF point."
                              f" They now have **{current_points}** MF point(s).",
                        inline=False)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
        await interaction.channel.send(embed=embed)

        mod_embed = await self.embeds.mod_add_points(interaction, user, ticket_counter, points=points)
        await thread_for_target_user.send(embed=mod_embed)

    async def handle_remove(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
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
            await interaction.followup.send("Done! The thread is here: <#" + str(thread_for_target_user.id) + ">", ephemeral=True)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"{interaction.user.mention} has taken {points} MF point from {user.mention}."
                                  f" They now have **{current_points - points}** MF point(s).",
                            inline=False)
            embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())
            await interaction.channel.send(embed=embed)

            mod_embed = await self.embeds.mod_remove_points(interaction, user, ticket_counter, points=points)
            await thread_for_target_user.send(embed=mod_embed)

        else:
            await interaction.followup.send(
                f"Can't remove — {user.mention} only has **{current_points}** MF point(s).", ephemeral=True
            )

    async def handle_clear(self, interaction: discord.Interaction, user: discord.Member):
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

        await interaction.followup.send("Done! The thread is here: <#" + str(thread_for_target_user.id) + ">", ephemeral=True)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{interaction.user.mention} has cleared all of {user.mention}'s MF points. They now have **0** MF points.",
                        inline=False)
        embed.set_footer(text="Made by FlamingCore", icon_url=await self.bot.get_owner_pfp_url())

        await interaction.channel.send(embed=embed)

        mod_embed = await self.embeds.mod_clear_points(interaction, user, ticket_counter, cleared_points=cleared_points)
        await thread_for_target_user.send(embed=mod_embed)
