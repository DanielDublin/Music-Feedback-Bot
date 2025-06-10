import discord
import database.db as db
from .helpers import DiscordHelpers

class Embeds:

    def __init__(self, bot, user_thread):
        self.bot = bot
        self.helpers = DiscordHelpers(bot)
        self.user_thread = user_thread

    async def mfr(self, ctx, ticket_counter, thread=None):

        points = int(await db.fetch_points(str(ctx.author.id)))
        
        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=discord.Color.green()
        )

        embed.add_field(name="🟢 <MFR", value=f"Gained **1** point and now has **{points}** MF points.", inline=True)
        embed.add_field(name=self.helpers.get_message_link(ctx), value="", inline=False)
        embed.set_footer(text=f"Feedback by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        return embed

    async def mfs(self, ctx, ticket_counter, thread=None):

        points = int(await db.fetch_points(str(ctx.author.id)))

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=discord.Color.red()
        )

        embed.add_field(name="🔴 <MFS", value=f"Used **1** point and now has **{points}** MF points.", inline=True)
        embed.add_field(name=self.helpers.get_message_link(ctx), value="", inline=False)
        embed.set_footer(text=f"Feedback by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        return embed

    async def mfs_with_zero_points(self, ctx, ticket_counter, thread=None):

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=discord.Color.yellow()
        )

        embed.add_field(name="⚠️ <MFS", value=f"Used <MFS with no points available in <#{ctx.channel.id}>.", inline=True)
        embed.set_footer(text=f"Feedback by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        return embed
    

    async def mod_add_points(self, interaction: discord.Interaction, user: discord.Member, ticket_counter, thread=None, points=0):

        total_points = int(await db.fetch_points(str(user.id)))

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=0x000099
        )

        embed.add_field(name="ℹ️ Added MF points", value=f"Added **{points}** points to {user.mention}. They now have **{total_points}** MF points.", inline=True)
        embed.set_footer(text=f"Added by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        return embed
    

    async def mod_remove_points(self, interaction: discord.Interaction, user: discord.Member, ticket_counter, thread=None, points=0):

        total_points = int(await db.fetch_points(str(user.id)))

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=0x000099
        )

        embed.add_field(name="ℹ️ Removed MF points", value=f"Removed **{points}** points from {user.mention}. They now have **{total_points}** MF points.", inline=True)
        embed.set_footer(text=f"Removed by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        return embed

    async def mod_clear_points(self, interaction: discord.Interaction, user: discord.Member, ticket_counter, thread=None, cleared_points=0):

        total_points = int(await db.fetch_points(str(user.id)))

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=0x000099
        )

        embed.add_field(name="ℹ️ Cleared MF points", value=f"Cleared **{cleared_points}** points from {user.mention}. They now have **{total_points}** MF points.", inline=True)
        embed.set_footer(text=f"Cleared by {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        return embed
        
    async def MFS_to_MFR_embed(self, original_message, shortened_message, ctx, thread, ticket_counter, points_added, total_points):

        embed = discord.Embed(
            title=f"Ticket #{ticket_counter} - Edit",
            description=f"{self.helpers.get_formatted_time()}",
            color=discord.Color.yellow()
        )

        embed.add_field(
            name="⚠️ `<MFS` edited to `<MFR`",
            value=f"Gained **{points_added}** points and now has **{total_points}** MF points.",
            inline=True
        )
        embed.add_field(name="Before", value=f"{original_message}", inline=False)
        embed.add_field(name="After", value=f"{shortened_message}", inline=False)

        return embed
    
    async def MFR_to_MFS_embed(self, original_message, shortened_message, ctx, thread, ticket_counter, points_removed, total_points):

        embed = discord.Embed(
            title=f"Ticket #{ticket_counter} - Edit",
            description=f"{self.helpers.get_formatted_time()}",
            color=discord.Color.yellow()
        )

        embed.add_field(
            name="⚠️ `<MFR` edited to `<MFS`",
            value=f"Used **{points_removed}** points and now has **{total_points}** MF points.",
            inline=True
        )
        embed.add_field(name="Before", value=f"{original_message}", inline=False)
        embed.add_field(name="After", value=f"{shortened_message}", inline=False)

        return embed
