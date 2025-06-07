import discord
import database.db as db
from discord.ext import commands
from discord import app_commands
import json
from data.constants import SERVER_ID
from cogs.feedback_threads.modules.helpers import DiscordHelpers
from cogs.feedback_threads.modules.ctx_class import ContextLike
from cogs.feedback_threads.modules.embeds import Embeds


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url = ""
        self.helpers = DiscordHelpers(self.bot)
        self.embeds = Embeds(self.bot, self.helpers)

    group = app_commands.Group(name="mfpoints", description="Alter any user's points.", default_permissions=discord.Permissions(administrator=True))
    
    # Mod give points
    @group.command(name='add', description="Use to add more points to a user.\n```/mfpoints add @user/user_id amount(optional)```")
    async def add(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            
        if points <=0:
            await interaction.response.send_message(f"You can only use positive numbers.", ephemeral=True)
            return 

        await db.add_points(str(user.id), points)
        current_points = int(await db.fetch_points(str(user.id)))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"ℹ️ {interaction.user.mention} has given {user.mention} {points} MF point."
                              f" They now have **{current_points}** MF point(s).",
                        inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await interaction.response.send_message("Done!", ephemeral=True)
        await interaction.channel.send(embed=embed)

        ctx_like = ContextLike(interaction, command=self.add)

        try:
            await ctx_like.interaction.channel.send("Loading threads...")
            feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx_like)
            await ctx_like.interaction.channel.send("load threads Done!")
        except Exception as e:
            await ctx_like.interaction.channel.send(e)
            return

        try:
            await ctx_like.interaction.channel.send("Checking if feedback thread...")
            await feedback_cog.threads_manager.check_if_feedback_thread(ctx_like, called_from_zero=False)
            await ctx_like.interaction.channel.send("check if feedback thread Done!")
        except Exception as e:
            await ctx_like.interaction.channel.send(e)
            return

        try:
            await ctx_like.interaction.channel.send("Loading feedback cog...")
            thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx_like)
            await ctx_like.interaction.channel.send("load feedback cog Done!")
        except Exception as e:
            await ctx_like.interaction.channel.send(e)
            return

        if thread.archived:
            await self.helpers.unarchive_thread(thread)
            mod_embed = await self.embeds.mod_add_points(ctx_like, user, ticket_counter, thread, points=points)
            await thread.send(embed=mod_embed)


        # Mod remove points

    @group.command(name='remove', description="Use to remove points from a user.\n```/mfpoints remove @user/user_id amount(optional)```")
    async def remove(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return
        
        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

        if points <=0:
            await interaction.response.send_message(f"You can only use positive numbers.", ephemeral=True)
            return
        
        current_points = int(await db.fetch_points(str(user.id)))

        if current_points - points >= 0:
            await db.reduce_points(str(user.id), points)
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"{interaction.user.mention} has taken {points} MF point from {user.mention}."
                                  f" They now have **{current_points - points}** MF point(s).",
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await interaction.response.send_message("Done!", ephemeral=True)
            await interaction.channel.send(embed=embed)

            ctx_like = ContextLike(interaction, command=self.add)

            feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx_like)
            await feedback_cog.threads_manager.check_if_feedback_thread(ctx_like, called_from_zero=False)

            thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx_like)

            mod_embed = await self.embeds.mod_remove_points(ctx_like, user, ticket_counter, thread, points=points)
            await thread.send(embed=mod_embed)

        else:
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Music Feedback",
                            value=f"Can't remove points, This member already has **{current_points}** MF points.",
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await interaction.response.send_message("Nope!", ephemeral=True)
            await interaction.channel.send(embed=embed)

            # Mod clear points

    @group.command(name="clear", description="Use to reset all the points from a user.\n```/mfpoints clear @user/user_id```")
    async def clear(self, interaction: discord.Interaction, user: discord.Member, points: int = 1):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("https://media.tenor.com/nEhFMtR35LQAAAAC/you-have-no-power-here-gandalf.gif")
            return

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

        cleared_points = int(await db.fetch_points(str(user.id)))

        await db.reset_points(str(user.id))
        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Music Feedback",
                        value=f"{interaction.user.mention} has cleared all of {user.mention}'s MF points. They now have **0** MF points.",
                        inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await interaction.response.send_message("Done!", ephemeral=True)
        await interaction.channel.send(embed=embed)

        ctx_like = ContextLike(interaction, command=self.add)

        feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx_like)
        await feedback_cog.threads_manager.check_if_feedback_thread(ctx_like, called_from_zero=False)

        thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx_like)

        mod_embed = await self.embeds.mod_clear_points(ctx_like, user, ticket_counter, thread, points=cleared_points)
        await thread.send(embed=mod_embed)

print("Processing complete")


async def setup(bot):
    # await bot.add_cog(Admin(bot), guild=discord.Object(id=SERVER_ID)) # for debug
    await bot.add_cog(Admin(bot))
