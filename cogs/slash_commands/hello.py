import discord
from discord.ext import commands
from discord import app_commands



class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name = "hello", description = "Greeting the user") #remove to get all guilds
    async def hello_command(self, interaction):
        await interaction.response.send_message("Hello! take 2")

async def setup(bot):
    await bot.add_cog(Hello(bot))

