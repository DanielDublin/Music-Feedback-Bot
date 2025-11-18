import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from data.constants import EVENT_VC  #submissions_channel_id = event-text
from cogs.event_vc_commands.start_in_the_mix import StartInTheMix


class EventVC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # in the mix
    # In your EventVC cog file
    @app_commands.command(name = "start-in-the-mix", description = "Start the In-The-Mix event")
    @app_commands.checks.has_permissions(administrator=True)
    async def start_in_the_mix(self, interaction):

        try:
            await interaction.response.defer(ephemeral=True)

            itm = StartInTheMix(self.bot)      
            await itm.send_announcement(interaction)

            await interaction.followup.send("✅ In The Mix started!", ephemeral=True)
        
        except discord.NotFound as e:
            print(f"NotFound error in start_in_the_mix: {e}")
            try:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except:
                pass
        
        except Exception as e:
            print(f"Error in start_in_the_mix: {e}")
            try:
                await interaction.followup.send(f"❌ Command failed: {e}", ephemeral=True)
            except:
                pass

        

async def setup(bot):
    await bot.add_cog(EventVC(bot))