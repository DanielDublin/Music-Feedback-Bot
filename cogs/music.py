import discord
from discord.ext import commands, menus
# Define a dictionary to store key information


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bot.command()
async def notes(ctx):
    menu = NotesMenu()
    await menu.start(ctx)

class NotesMenu(menus.Menu):
    def __init__(self):
        super().__init__()

    async def send_initial_message(self, ctx, channel):
        # Define the initial message and embed
        embed = discord.Embed(title="Select a category:", color=0x7e016f)
        embed.add_field(name="1. Majors", value="Select majors", inline=False)
        embed.add_field(name="2. Sharp/Flat Majors", value="Select Sharp/Flat majors", inline=False)
        embed.add_field(name="3. Minors", value="Select minors", inline=False)
        embed.add_field(name="4. Sharp/Flat Minors", value="Select Sharp/Flat minors", inline=False)
        embed.add_field(name="5. Triads", value="Select triads", inline=False)
        embed.set_footer(text="React with the corresponding number to select a category.")

        return await channel.send(embed=embed)

    async def send_menu(self, ctx, page):
        categories = [
            "Majors",
            "Sharp/Flat Majors",
            "Minors",
            "Sharp/Flat Minors",
            "Triads",
        ]

        # Define the options for each category
        options = {
            "Majors": {
                "C major": ("C D E F G A B", "A minor", "C minor"),
                "D major": ("D E F# G A B C#", "B minor", "D minor"),
                # Add more majors here...
            },
            "Sharp/Flat Majors": {
                "C# major": ("C# D# E# F# G# A# B#", "A# minor", "C# minor"),
                "Db major": ("Db Eb F Gb Ab Bb C", "Bb minor", "Db minor"),
                # Add more Sharp/Flat majors here...
            },
            "Minors": {
                "C minor": ("C D Eb F G Ab Bb", "Eb major", "C major"),
                "D minor": ("D E F G A Bb C", "F major", "D major"),
                # Add more minors here...
            },
            "Sharp/Flat Minors": {
                "C# minor": ("C# D# E F# G# A B", "E major", "C# (Db) major"),
                "Db minor": ("Db Eb Fb Gb Ab Bbb Cb", "Ebb (D#) major", "Db major"),
                # Add more Sharp/Flat minors here...
            },
            "Triads": {
                "C major": (
                    "C major\nD minor\nE minor\nF major\nG major\nA minor\nB dim",
                    "I\nii\niii\nIV\nV\nvi\nvii°",
                    "C E G (B)\nD F A (C)\nE G B (D)\nF A C (E)\nG B D (F)\nA C E (G)\nB D F (A)"
                ),
                "D major": (
                    "D major\nE minor\nF# minor\nG major\nA major\nB minor\nC# dim",
                    "I\nii\niii\nIV\nV\nvi\nvii°",
                    "D F# A (C#)\nE G B (D)\nF# A C# (E)\nG B D (F#)\nA C# E (G)\nB D F# (A)\nC# E G (B)"
                ),
                # Add more triads here...
            },
        }

        category = categories[page]
        options_embed = discord.Embed(title=f"Select a {category} category:", color=0x7e016f)
        options_embed.set_footer(text=f"Page {page + 1}/{len(categories)}")

        # Add options for the selected category
        for key, value in options[category].items():
            options_embed.add_field(name=key, value=value[0], inline=False)

        return await ctx.send(embed=options_embed)

    @menus.button('\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f')
    async def on_arrow_left(self, payload):
        # Go to the previous page
        if self.current_page > 0:
            self.current_page -= 1
            await self.show_page(self.current_page)

    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f')
    async def on_arrow_right(self, payload):
        # Go to the next page
        if self.current_page < len(self.categories) - 1:
            self.current_page += 1
            await self.show_page(self.current_page)

    @menus.button('\N{CROSS MARK}\ufe0f')
    async def on_stop(self, payload):
        # Stop the menu
        self.stop()

    def reaction_check(self, payload):
        # Check if the reaction is from the original author
        return payload.user_id == self.message.author.id

def setup(bot):
    bot.add_cog(Music(bot))