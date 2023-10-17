import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data.constants import SERVER_ID

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_timer = None  
    
        
        
    group = app_commands.Group(name="timer", description="Countdown from any time (minutes)", default_permissions=discord.Permissions(administrator=True))
    

    @group.command(name = "status") 
    async def status(self, interaction):
        if self.active_timer is not None:
            await interaction.response.send_message(f"A timer is already running. Use `/timer stop` to stop it.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Use `/timer start <minutes>` to start a timer.", ephemeral=True)

    async def timer_countdown(self, interaction, minutes):
        
        channel = interaction.channel
        await channel.send(f"{interaction.user.mention} has started the timer.\n{minutes} minutes is on the clock, starting... **NOW!**")
        counter =0
        timers =  [5, 4, 3, 2, 1]
        
        while counter != len(timers):
            if minutes in timers:
                counter +=1
                await channel.send(f"{minutes} minutes remaining.")
                
            await asyncio.sleep(60)
            minutes -=1
                
        await asyncio.sleep(60)
        await channel.send("Time is up!")
        self.active_timer = None
        

    @group.command(name="start")
    async def start(self, interaction: discord.Interaction, minutes :int) -> None:
        author_id = interaction.user.id
        
        if self.active_timer is not None:
            await interaction.response.send_message(f"A timer is already running. Use `/timer stop` to stop it.", ephemeral=True)
        else:
            await interaction.response.send_message("Starting the timer.", ephemeral=True)
            self.active_timer = asyncio.create_task(self.timer_countdown(interaction, minutes))
            

    @group.command(name="stop")
    async def stop(self, interaction: discord.Interaction) -> None:
        author_id = interaction.user.id
        
        if self.active_timer is not None:
            self.active_timer.cancel()
            await interaction.response.send_message("Timer stopped.", ephemeral=True)
            self.active_timer = None
        else:
            await interaction.response.send_message("No timer is currently running.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TimerCog(bot), guild=discord.Object(id=SERVER_ID))