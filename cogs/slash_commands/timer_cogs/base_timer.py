import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data.constants import SERVER_ID


class BaseTimer(commands.Cog):
    def __init__(self, bot, name):
        self.bot = bot
        self.name = name
        self.active_timer = {}
        self.minutes = {}


    # used to create an object for other events

    # start timer will check if other timers are running/input is valid and call the run_timer function
    async def start_timer(self, interaction: discord.Interaction, event: str, minutes: int):

        if event in self.active_timer:
            await interaction.response.send_message(f"A {event} Timer is already running.",
                                                    ephemeral=True)
            return

        if minutes <= 0:
            await interaction.response.send_message(f"You can start the timer only with positive values",
                                                    ephemeral=True)
            return

        self.minutes[event] = minutes
        self.active_timer[event] = asyncio.create_task(self._run_timer(interaction, event))
        await interaction.response.send_message(f"Starting the {event} Timer for {minutes} minutes.", ephemeral=True)

    # run_timer will start the countdown and provide time updates
    async def _run_timer(self, interaction: discord.Interaction, event: str, minutes: int):
        channel = interaction.channel
        await channel.send(f"{interaction.user.mention} has started the {event} Timer for {self.minutes[event]} minutes.")

        intervals = [1, 15, 30, 45]

        while self.minutes[event] > 0:
            # staggers while loop for every minute and reduces minutes of event
            await asyncio.sleep(60)
            self.minutes[event] -= 1

            if self.minutes[event] in intervals:
                await channel.send(f"There are {self.minutes[event]} remaining in the {event} event!")

        await channel.send(f"Time is up! {event} is now over.")
        self._stop_timer(event)

    # internal stop helper function used above to stop the event in list
    async def _stop_timer(self, event: str):
        if event in self.active_timer:
            self.active_timer[event].pop()
        if event in self.minutes:
            self.minutes[event].pop()

    # get status of timer
    async def timer_status(self, interaction: discord.Interaction, event: str):
        if event in self.active_timer:
            await interaction.response.send_message(f"{event} has {self.minutes} left.")
        else:
            await interaction.response.send_message("There are no active timers.")

    # stop the timer manually
    async def stop_timer(self, interaction: discord.Interaction, event: str):

        if event in self.active_timer:
            await self.active_timers[event].cancel()
            await self._stop_timer(event)
            await interaction.response.send_message(f"{event} Timer stopped.", ephemeral=True)
        else:
            await interaction.response.send_message(f"The {event} Timer is currently running.", ephemeral=True)
