import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data.constants import SERVER_ID
import database.db as db
from data.constants import FEEDBACK_CHANNEL_ID, FEEDBACK_ACCESS_CHANNEL_ID, SERVER_OWNER_ID, FEEDBACK_CATEGORY_ID

class BaseTimer(commands.GroupCog, group_name = "timer"):
    def __init__(self, bot, name):
        self.bot = bot
        self.name = name
        self.active_timer = {}
        self.minutes = {}
        self.pfp_url = ""

    # used to create an object for other events

    # start timer will check if other timers are running/input is valid and call the run_timer function
    async def start_timer(self, interaction: discord.Interaction, event: str, minutes: int):

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

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

        if event == "Double Points":
            file = discord.File(
                "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/images/2x_MF_POINTS.gif",  # Use a relative path
                filename="2x_MF_POINTS.gif"
            )

            # Create the embed
            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="**2X MF POINTS**", value="", inline=False)
            embed.add_field(name="", value=f"For the next {minutes} minutes, every feedback given with **<MFR** in the feedback channels will reward 2 MF Points. \n\n For help using the feedback system, please read <#{FEEDBACK_ACCESS_CHANNEL_ID}>", inline=False)

            embed.set_image(url="attachment://2x_MF_POINTS.gif")
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)

            await interaction.followup.send(content="__# DOUBLE POINTS NOW ACTIVE__", embed=embed, file=file)

    # run_timer will start the countdown and provide time updates
    async def _run_timer(self, interaction: discord.Interaction, event: str):
        channel = interaction.channel
        await channel.send(f"{interaction.user.mention} has started the {event} Timer for {self.minutes[event]} minutes.")

        intervals = [1, 5, 10, 15, 30, 45]

        while self.minutes[event] > 0:
            # staggers while loop for every minute and reduces minutes of event
            await asyncio.sleep(60)
            self.minutes[event] -= 1

            if self.minutes[event] in intervals:
                await channel.send(f"{event} Timer has {self.minutes[event]} minutes remaining!")

        await channel.send(f"Time is up! {event} is now over.")
        # stop event
        await self._stop_timer(event)

    async def _double_points_logic(self, ctx: discord.Message, event: str):
        mention = ctx.author.mention
        if not await self.handle_feedback_command_validity(ctx, mention):
            return

        await db.add_points(str(ctx.author.id), 1)

        points = int(await db.fetch_points(str(ctx.author.id)))
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)  # feedback log channel

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Feedback Notice",
                        value=f"{mention} has **given feedback** and now has **{points}** MF point(s).", inline=False)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)

        await ctx.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).",
                               delete_after=4)
        await channel.send(embed=embed)  # Logs channel

    # internal stop helper function used above to stop the event in list
    async def _stop_timer(self, event: str):
        if event in self.active_timer:
            self.active_timer[event].cancel()
            del self.active_timer[event]
        if event in self.minutes:
            del self.minutes[event]

    # get status of timer
    async def timer_status(self, interaction: discord.Interaction, event: str):
        if event in self.active_timer:
            await interaction.response.send_message(f"{event} has {self.minutes[event]} minutes left.")
        else:
            await interaction.response.send_message("There are no active timers.")

    # stop the timer manually
    async def stop_timer(self, interaction: discord.Interaction, event: str):

        if event in self.active_timer:
            self.active_timer[event].cancel()
            await self._stop_timer(event)
            await interaction.response.send_message(f"{event} Timer stopped.", ephemeral=True)
        else:
            await interaction.response.send_message(f"The {event} Timer is currently running.", ephemeral=True)
