import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data.constants import SERVER_ID
from .base_timer import BaseTimer

class TimerCog(commands.GroupCog, group_name = "timer"):
    """
    Inherits from commands.GroupCog and uses BaseTimer for timer logic.
    """
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.timer_handler = BaseTimer(bot)

    # start timer
    @app_commands.command(name="start", description="Start a timer for a specific event.")
    @app_commands.describe(event="The type of event timer to start.", minutes="Duration of the timer in minutes.")
    @app_commands.choices(event=[
        app_commands.Choice(name="Basic Timer", value="Basic"),
        app_commands.Choice(name="Double Points Timer", value="Double Points"),
    ])
    async def start(self, interaction: discord.Interaction, event: app_commands.Choice[str], minutes: int):
        await self.timer_handler.start_timer(interaction, event.value, minutes)

    # status
    @app_commands.command(name="status", description="Timer status for a specific event.")
    @app_commands.describe(event="The type of event timer to see the status for.")
    @app_commands.choices(event=[
        app_commands.Choice(name="Basic Timer", value="Basic"),
        app_commands.Choice(name="Double Points Timer", value="Double Points"),
    ])
    async def status(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        await self.timer_handler.timer_status(interaction, event.value)

    # stop
    @app_commands.command(name="stop", description="Stop the timer for a specific event.")
    @app_commands.describe(event="The type of event timer to stop.")
    @app_commands.choices(event=[
        app_commands.Choice(name="Basic Timer", value="Basic"),
        app_commands.Choice(name="Double Points Timer", value="Double Points"),
    ])
    async def stop(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        await self.timer_handler.stop_timer(interaction, event.value)


async def setup(bot):
    # await bot.add_cog(TimerCog(bot))
    await bot.add_cog(TimerCog(bot), guild=discord.Object(id=SERVER_ID))