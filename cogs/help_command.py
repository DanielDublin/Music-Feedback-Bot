from discord.ext import commands, menus
import discord

class HelpMenu(menus.Menu):
    def __init__(self, bot):
        super().__init__(timeout=60.0, delete_message_after=True, clear_reactions_after=True)
        self.user = None
        self.main_menu = None
        self.is_main = True
        self.bot = bot
        self.bot.add_listener(self.on_raw_reaction_add)
        
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id and payload.emoji.name == '↩️' and not self.is_main:
            self.is_main = True
            await self.message.clear_reactions()
            await self.update_main_menu()
            

    async def send_initial_message(self, ctx, channel):
        self.user = ctx.author
        return await ctx.send(embed=self.get_main_menu())

    def get_main_menu(self):
        embed = discord.Embed(title="Help Menu", color=0x7e016f)
        embed.add_field(name="1️⃣ General", value="Show general commands", inline=False)
        embed.add_field(name="2️⃣ Admin", value="Show admin commands", inline=False)  
        return embed

    async def update_main_menu(self):
        await self.message.edit(embed=self.get_main_menu())
        await self.message.add_reaction("1️⃣")
        await self.message.add_reaction("2️⃣")


    @menus.button("1️⃣")
    async def on_general(self, payload):
        await self.message.clear_reactions()
        await self.message.add_reaction("↩️")
        self.is_main = False
        # Handle the "General" option here and display relevant commands

    @menus.button("2️⃣")
    async def on_admin(self, payload):
        await self.message.clear_reactions()
        await self.message.add_reaction("↩️")
        self.is_main = False
        # Handle the "Admin" option here and display relevant commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        self.menu = HelpMenu(self.bot)
        await self.menu.start(ctx)
async def setup(bot):
    await bot.add_cog(HelpCog(bot))
