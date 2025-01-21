# # import asyncio
# # import discord
# # from discord.ext import commands
# import asyncio
# import discord
# from discord.ext import commands, tasks
# from discord import app_commands
# from data.constants import SERVER_ID
# from .base_timer import BaseTimer
#
# class DoublePointsTimer(BaseTimer):
#     def __init__(self, bot):
#         super().__init__(bot, "Double MF Points")
#
#     group = app_commands.Group(name="double_points_timer", description="Countdown from any time (minutes)",
#                                default_permissions=discord.Permissions(administrator=True))
#
#     @group.command(name="start", description="Start the Double MF Points Timer")
#     async def start_timer(self, interaction: discord.Interaction, minutes: int):
#             await super().start_timer(interaction, minutes)
#
# async def setup(bot):
#     # await bot.add_cog(TimerCog(bot), guild=discord.Object(id=SERVER_ID))
#     await bot.add_cog(DoublePointsTimer(bot))
# #
# #     group = app_commands.Group(name="events", description="Special server event countdown from any time (minutes)",
# #                                default_permissions=discord.Permissions(administrator=True))
# #     @group.command(name="activate_double_points", description="Start the Double MF Points Special Event")
# #     async def start_double_points_timer(self, interaction: discord.Interaction, minutes: int) -> None:
# #
# #         if self.double_points_timer is not None:
# #             await interaction.response.send_message(f"A {self.name} timer is already running.",
# #                                                         ephemeral=True)
# #         else:
# #             if minutes <= 0:
# #                 await interaction.response.send_message(f"You can start the timer only with positive values",
# #                                                             ephemeral=True)
# #                 return
# #             await interaction.response.send_message(f"Starting the {self.name} timer.", ephemeral=True)
# #             self.double_points_minutes = minutes
# #             self.double_points_timer = asyncio.create_task(self.double_points_timer_countdown(interaction))
# #     async def double_points_timer_countdown(self, interaction):
# #         channel = interaction.channel
# #
# #         await channel.send(
# #             f"{interaction.user.mention} has started the timer.\n{self.double_points_minutes} minutes is on the clock, starting... **NOW!**")
# #         counter = 0
# #         timers = [1, 5, 10, 15, 30]
# #         starting_time = self.double_points_minutes
# #         counter_stop = len([item for item in timers if item < starting_time])
# #
# #         while counter != counter_stop:
# #             if self.double_points_minutes in timers:
# #                 counter += 1
# #                 await channel.send(f"# {self.double_points_minutes} minutes remaining.")
# #
# #             await asyncio.sleep(60)
# #             self.double_points_minutes -= 1
# #
# #         await channel.send("# Time is up!")
# #         self.double_points_timer = None
# #
# #     async def double_mf_points_functionality(self, interaction):
# #         while self.double_points_timer is not None:
# #             if ctx.message ==
# #             return 0
# #
# #
# # async def setup(bot):
# #     await bot.add_cog(DoublePoints(bot))
# #     print("DoublePoints cog has been loaded.")