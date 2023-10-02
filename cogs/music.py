import discord
from discord.ext import commands, menus
import json

# Define the available categories and options
categories = ["Info", "Chords"]
degree = "\u00b0"

options ={}
# Load data from JSON file
with open('options.json', 'r') as json_file:
    options = json.load(json_file)



class NotesMenu(menus.Menu):
    def __init__(self, category=None, subcategory=None):
        super().__init__()
        self.category = category
        self.subcategory = subcategory

    async def send_initial_message(self, ctx, channel):
        if not self.category:
            # Show category selection if no category selected
            embed = discord.Embed(title="Select a category:", color=0x7e016f)
            for i, category in enumerate(categories, start=1):
                embed.add_field(name=f"{i}. {category}", value=f"Select {category}", inline=False)
            embed.set_footer(text="React with the corresponding number to select a category.")
            return await channel.send(embed=embed)
        else:
            # Show sub-category selection if a category is selected
            subcategories = options.get(self.category, {}).get("Categories", {})
            embed = discord.Embed(title="Select a subcategory:", color=0x7e016f)
            for i, subcategory in enumerate(subcategories, start=1):
                embed.add_field(name=f"{i}. {subcategory}", value=f"Select {subcategory}", inline=False)
            embed.set_footer(text="React with the corresponding number to select a subcategory.")
            return await channel.send(embed=embed)

    async def send_menu(self, ctx, page):
        if not self.subcategory:
            subcategories = options.get(self.category, {}).get("Categories", {})
            subcategory_names = list(subcategories.keys())
            subcategory_name = subcategory_names[page]
            subcategory_data = subcategories.get(subcategory_name, {})
            embed = discord.Embed(title=f"Select a {subcategory_name}:", color=0x7e016f)
            for key, value in subcategory_data.items():
                embed.add_field(name=key, value=value, inline=False)
            embed.set_footer(text=f"Page {page + 1}/{len(subcategory_names)}")
            return await ctx.send(embed=embed)

    @menus.button('\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f')
    async def on_arrow_left(self, payload):
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(self.current_page)

    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f')
    async def on_arrow_right(self, payload):
        subcategories = options.get(self.category, {}).get("Categories", {})
        if self.current_page < len(subcategories) - 1:
            self.current_page += 1
            await self.show_page(self.current_page)

    @menus.button('\N{CROSS MARK}\ufe0f')
    async def on_stop(self, payload):
        self.stop()

    def reaction_check(self, payload):
        return payload.user_id == self.message.author.id

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def notes(self, ctx):
        menu = NotesMenu()
        await menu.start(ctx)

def setup(bot):
    bot.add_cog(Music(bot))