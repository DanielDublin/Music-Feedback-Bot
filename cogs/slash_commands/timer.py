import asyncio
import discord
from discord.ext import commands, tasks
from discord import app_commands
from data.constants import SERVER_ID

class TimerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_timer = None  
        self.minutes =0
    
        
        
    group = app_commands.Group(name="timer", description="Countdown from any time (minutes)", default_permissions=discord.Permissions(administrator=True))
    

    @group.command(name = "status",  description="Check how much time is left on the timer.") 
    async def status(self, interaction):
        if self.active_timer is not None:
            await interaction.response.send_message(f"# There are {self.minutes} minutes remaining.")
        else:
            await interaction.response.send_message(f"No timers are currently active, use `/timer start <minutes>` to start a timer.", ephemeral=True)

    async def timer_countdown(self, interaction):
        
        channel = interaction.channel
        
        await channel.send(f"{interaction.user.mention} has started the timer.\n{self.minutes} minutes is on the clock, starting... **NOW!**")
        counter =0
        timers =  [1, 5, 10, 15, 30]
        starting_time = self.minutes
        counter_stop = len([item for item in timers if item < starting_time])
        
        while counter != counter_stop:
            if self.minutes in timers:
                counter +=1
                await channel.send(f"# {self.minutes} minutes remaining.")
                
            await asyncio.sleep(60)
            self.minutes -=1
                
        await channel.send("# Time is up!")
        self.active_timer = None
        

    @group.command(name="start",  description="Start the timer.")
    async def start(self, interaction: discord.Interaction, minutes :int) -> None:
        author_id = interaction.user.id
      

        if self.active_timer is not None:
            await interaction.response.send_message(f"A timer is already running. Use `/timer stop` to stop it.", ephemeral=True)
        else:
            if minutes <=0:
                await interaction.response.send_message(f"You can start the timer only with positive values", ephemeral=True)
                return
            await interaction.response.send_message("Starting the timer.", ephemeral=True)
            self.minutes = minutes
            self.active_timer = asyncio.create_task(self.timer_countdown(interaction))
            

    @group.command(name="stop",  description="Stop the timer.")
    async def stop(self, interaction: discord.Interaction) -> None:
        author_id = interaction.user.id
        
        if self.active_timer is not None:
            self.active_timer.cancel()
            self.minutes = 0
            await interaction.response.send_message("Timer stopped.", ephemeral=True)
            self.active_timer = None
        else:
            await interaction.response.send_message("No timer is currently running.", ephemeral=True)


async def setup(bot):
    #await bot.add_cog(TimerCog(bot), guild=discord.Object(id=SERVER_ID))
    await bot.add_cog(TimerCog(bot))