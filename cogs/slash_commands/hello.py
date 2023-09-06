from discord.ext import commands
from discord_slash import cog_ext

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(
        name="hello",
        description="Say hello to the bot",
    )
    async def hello_command(self, ctx):
        await ctx.send("Hello!")

def setup(bot):
    bot.add_cog(Hello(bot))