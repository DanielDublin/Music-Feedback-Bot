import discord
from discord.ext import commands, menus

# Define the available categories and options
categories = ["Info", "Chords"]

options = {
    "Info": {
        "Categories": {
            "Majors": {
                "C major": "`C D E F G A B`\n\nThe relative minor is A minor. \nThe parallel minor is C minor.",
                "D major": "`D E F# G A B C#`\n\nThe relative minor is B minor. \nThe parallel minor is D minor.",
                "E major": "`E F# G# A B C# D#`\n\nThe relative minor is C# minor. \nThe parallel minor is E minor.",
                "F major": "`F G A Bb C D E`\n\nThe relative minor is D minor. \nThe parallel minor is F minor.",
                "G major": "`G A B C D E F#`\n\nThe relative minor is E minor. \nThe parallel minor is G minor.",
                "A major": "`A B C# D E F# G#`\n\nThe relative minor is F# minor. \nThe parallel minor is A minor.",
                "B major": "`B C# D# E F# G# A#`\n\nThe relative minor is G# minor. \nThe parallel minor is B minor."
            },
            "Sharp/Flat Majors": {
                "C# major": "`C# D# E# F# G# A# B#`\n\nThe relative minor is A# minor. \nThe parallel minor is C# minor.",
                "Db major": "`Db Eb F Gb Ab Bb C`\n\nThe relative minor is Bb minor. \nThe parallel minor is C# minor.",
                "D# major": "Most commonly notated as Eb major.",
                "Eb major": "`Eb F G Ab Bb C D`\n\nThe relative minor is C minor. \nThe parallel minor is Eb minor.",
                "F# major": "`F# G# A# B C# D# E#`\n\nThe relative minor is D# minor. \nThe parallel minor is F# minor.",
                "Gb major": "`Gb Ab Bb Cb Db Eb F`\n\nThe relative minor is Eb minor. \nThe parallel minor is Gb minor.",
                "G# major": "Most commonly notated as Ab major.",
                "Ab major": "`Ab Bb C Db Eb F G`\n\nThe relative minor is F minor. \nThe parallel minor is Ab minor (more often G# minor).",
                "A# major": "Most commonly notated as Bb major.",
                "Bb major": "`Bb C D Eb F G A`\n\nThe relative minor is G minor. \nThe parallel minor is Bb minor.",
                "B# major": "Most commonly notated as Cb major.",
                "Cb major": "`Cb Db Eb Fb Gb Ab Bb`\n\nThe relative minor is Ab minor. \nThe parallel minor is Cb minor (more often as B minor)."
            },
            "Minors": {
                "C minor": "`C D Eb F G Ab Bb`\n\nThe relative major is Eb major. \nThe parallel major is C major.",
                "D minor": "`D E F G A Bb C`\n\nThe relative major is F major. \nThe parallel major is D major.",
                "E minor": "`E F# G A B C D`\n\nThe relative major is G major. \nThe parallel major is E major.",
                "F minor": "`F G Ab Bb C Db Eb`\n\nThe relative major is Ab major. \nThe parallel major is F major.",
                "G minor": "`G A Bb C D Eb F`\n\nThe relative major is Bb major. \nThe parallel major is G major.",
                "A minor": "`A B C D E F G`\n\nThe relative major is C major. \nThe parallel major is A major.",
                "B minor": "`B C# D E F# G A`\n\nThe relative major is D major. \nThe parallel major is B major."
                },
            "Sharp/Flat Minors": {
                "C# minor": "`C# D# E F# G# A B`\n\nThe relative major is E major. \nThe parallel major is C# (more often as Db major).",
                "Db minor": "Most commonly notated as C# minor.",
                "D# minor": "`D# E# F# G# A# B# C##`\n\nThe relative major is F# major. \nThe parallel major is D# major (most often as Eb major).",
                "Eb minor": "`Eb F Gb Ab Bb Cb Db`\n\nThe relative major is Gb major. \nThe parallel major is Eb major.",
                "F# minor": "`F# G# A B C# D E`\n\nThe relative major is A major. \nThe parallel major is F# major.",
                "Gb minor": "Most commonly notated as F# minor.",
                "G# minor": "`G# A# B C# D# E F##`\n\nThe relative major is B major. \nThe parallel major is G# major (more often as Ab major).",
                "Ab minor": "`Ab Bb Cb Db Eb Fb Gb`\n\nThe relative major is Cb major. \nThe parallel major is Ab major.",
                "A# minor": "`A# B# C# D# E# F# G#`\n\nThe relative major is C# major. \nThe parallel major is A# major (most often as Bb major).",
                "Bb minor": "`Bb C Db Eb F Gb Ab`\n\nThe relative major is Db major. \nThe parallel major is Bb major.",
                "B# minor": "Theoretical key.",
                "Cb minor": "Theoretical key."
                }
        }
    },
    "Chords": {
        "Categories": {
            "Majors": {
                "C major": "`C D E F G A B`\n\nThe relative minor is A minor. \nThe parallel minor is C minor.",
                "D major": "`D E F# G A B C#`\n\nThe relative minor is B minor. \nThe parallel minor is D minor.",
                "E major": "`E F# G# A B C# D#`\n\nThe relative minor is C# minor. \nThe parallel minor is E minor.",
                "F major": "`F G A Bb C D E`\n\nThe relative minor is D minor. \nThe parallel minor is F minor.",
                "G major": "`G A B C D E F#`\n\nThe relative minor is E minor. \nThe parallel minor is G minor.",
                "A major": "`A B C# D E F# G#`\n\nThe relative minor is F# minor. \nThe parallel minor is A minor.",
                "B major": "`B C# D# E F# G# A#`\n\nThe relative minor is G# minor. \nThe parallel minor is B minor."
            },
            "Sharp/Flat Majors": {
                "C# major": "`C# D# E# F# G# A# B#`\n\nThe relative minor is A# minor. \nThe parallel minor is C# minor.",
                "Db major": "`Db Eb F Gb Ab Bb C`\n\nThe relative minor is Bb minor. \nThe parallel minor is C# minor.",
                "D# major": "Most commonly notated as Eb major.",
                "Eb major": "`Eb F G Ab Bb C D`\n\nThe relative minor is C minor. \nThe parallel minor is Eb minor.",
                "F# major": "`F# G# A# B C# D# E#`\n\nThe relative minor is D# minor. \nThe parallel minor is F# minor.",
                "Gb major": "`Gb Ab Bb Cb Db Eb F`\n\nThe relative minor is Eb minor. \nThe parallel minor is Gb minor.",
                "G# major": "Most commonly notated as Ab major.",
                "Ab major": "`Ab Bb C Db Eb F G`\n\nThe relative minor is F minor. \nThe parallel minor is Ab minor (more often G# minor).",
                "A# major": "Most commonly notated as Bb major.",
                "Bb major": "`Bb C D Eb F G A`\n\nThe relative minor is G minor. \nThe parallel minor is Bb minor.",
                "B# major": "Most commonly notated as Cb major.",
                "Cb major": "`Cb Db Eb Fb Gb Ab Bb`\n\nThe relative minor is Ab minor. \nThe parallel minor is Cb minor (more often as B minor)."
            },
            "Minors": {
                "C minor": "`C D Eb F G Ab Bb`\n\nThe relative major is Eb major. \nThe parallel major is C major.",
                "D minor": "`D E F G A Bb C`\n\nThe relative major is F major. \nThe parallel major is D major.",
                "E minor": "`E F# G A B C D`\n\nThe relative major is G major. \nThe parallel major is E major.",
                "F minor": "`F G Ab Bb C Db Eb`\n\nThe relative major is Ab major. \nThe parallel major is F major.",
                "G minor": "`G A Bb C D Eb F`\n\nThe relative major is Bb major. \nThe parallel major is G major.",
                "A minor": "`A B C D E F G`\n\nThe relative major is C major. \nThe parallel major is A major.",
                "B minor": "`B C# D E F# G A`\n\nThe relative major is D major. \nThe parallel major is B major."
                },
            "Sharp/Flat Minors": {
                "C# minor": "`C# D# E F# G# A B`\n\nThe relative major is E major. \nThe parallel major is C# (more often as Db major).",
                "Db minor": "Most commonly notated as C# minor.",
                "D# minor": "`D# E# F# G# A# B# C##`\n\nThe relative major is F# major. \nThe parallel major is D# major (most often as Eb major).",
                "Eb minor": "`Eb F Gb Ab Bb Cb Db`\n\nThe relative major is Gb major. \nThe parallel major is Eb major.",
                "F# minor": "`F# G# A B C# D E`\n\nThe relative major is A major. \nThe parallel major is F# major.",
                "Gb minor": "Most commonly notated as F# minor.",
                "G# minor": "`G# A# B C# D# E F##`\n\nThe relative major is B major. \nThe parallel major is G# major (more often as Ab major).",
                "Ab minor": "`Ab Bb Cb Db Eb Fb Gb`\n\nThe relative major is Cb major. \nThe parallel major is Ab major.",
                "A# minor": "`A# B# C# D# E# F# G#`\n\nThe relative major is C# major. \nThe parallel major is A# major (most often as Bb major).",
                "Bb minor": "`Bb C Db Eb F Gb Ab`\n\nThe relative major is Db major. \nThe parallel major is Bb major.",
                "B# minor": "Theoretical key.",
                "Cb minor": "Theoretical key."
                }
        }
    }
}


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