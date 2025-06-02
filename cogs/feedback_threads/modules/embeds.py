import discord
from .helpers import DiscordHelpers

class Embeds:

    def __init__(self, bot, user_thread):
        self.bot = bot
        self.helpers = DiscordHelpers(bot)
        self.user_thread = user_thread

    async def mfs_with_zero_points(self, ctx, ticket_counter, thread=None):

        embed = discord.Embed(
        title=f"Ticket #{ticket_counter}",
        description=f"{self.helpers.get_formatted_time()}",
        color=discord.Color.yellow()
        )

        embed.add_field(name="<MFS", value=f"Used <MFS with no points available in <#{ctx.channel.id}>.", inline=True)
        embed.set_footer(text="Some Footer Text")

        return embed
    