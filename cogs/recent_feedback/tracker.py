# create an id for each mfr and mfs - do we need mfs? - tracker of how many points requested
# includes message linkas PK? and created time of insert


import discord
from discord.ext import commands
from discord import app_commands


class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


