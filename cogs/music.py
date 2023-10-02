import discord
from discord.ext import commands, menus

# Define the available categories and options
categories = ["Info", "Chords"]
degree = "\u00b0"

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
                    "C major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`C major\nD minor\nE minor\nF major\nG major\nA minor\nB dim`",
                        "Notes": "`C E G (B)\nD F A (C)\nE G B (D)\nF A C (E)\nG B D (F)\nA C E (G)\nB D F (A)`"
                    },
                    "D major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`D major\nE minor\nF# minor\nG major\nA major\nB minor\nC# dim`",
                        "Notes": "`D F# A (C#)\nE G B (D)\nF# A C# (E)\nG B D (F#)\nA C# E (G)\nB D F# (A)\nC# E G (B)`"
                    },
                    "E major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`E major\nF# minor\nG# minor\nA major\nB major\nC# minor\nD# dim`",
                        "Notes": "`E G# B (D#)\nF# B D# (E)\nG# B D# (F#)\nA C# E (G#)\nB D# F# (A)\nC# E G# (B)\nD# F# A (C#)`"
                    },
                    "F major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`F major\nG minor\nA minor\nBb major\nC major\nD minor\nE dim`",
                        "Notes": "`F A C (E)\nG Bb D (F)\nA C E (G)\nBb D F A\nC E G (Bb)\nD F A (C)\nE G Bb (D)`"
                    },
                    "G major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`G major\nA minor\nB minor\nC major\nD major\nE minor\nF# dim`",
                        "Notes": "`G B D (F#)\nA C E (G)\nB D F# (A)\nC E G (B)\nD F# A (C)\nE G B (D)\nF# A C (E)`"
                    },
                    "A major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`A major\nB minor\nC# minor\nD major\nE major\nF# minor\nG# dim`",
                        "Notes": "`A C# E (G#)\nB D F# (A)\nC# E G# (B)\nD F# A (C#)\nE G# B (D)\nF# A C# (E)\nG# B D (F#)`"
                    },
                    "B major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`B major\nC# minor\nD# minor\nE major\nF# major\nG# minor\nA# dim`",
                        "Notes": "`B D# F# (A#)\nC# E G# (B)\nD# F# A# (C#)\nE G# B (D#)\nF# A# C# (E)\nG# B D# (F#)\nA# C# E (G#)`"
                    }
                }
            },
            "Sharp/Flat Majors": {
                    "C# major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": f"`C# major\nD# minor\nE# minor\nF# major\nG# major\nA# minor\nB# dim`",
                        "Notes": f"`C# E# G# (B#)\nD# F# A# (C#)\nE# G# B# (D#)\nF# A# C# (E#)\nG# B# D# (F#)\nA# C# E# (G#)\nB# D# F# (A#)`"
                    },
                    "Db major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Db major\nEb minor\nF minor\nGb major\nAb major\nBb minor\nC dim`",
                        "Notes": "`Db F Ab (C)\nEb Gb Bb (Db)\nF Ab C (Eb)\nGb Bb Db (F)\nAb C Eb (Gb)\nBb Db F (Ab)\nC Eb Gb (Bb)`"
                    },
                    "D# major": "Most commonly notated as Eb major.",
                    "Eb major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Eb major\nF minor\nG minor\nAb major\nBb major\nC minor\nD dim`",
                        "Notes": "`Eb G Bb (D)\nF Ab C (Eb)\nG Bb D (F)\nAb C D (Ab)\nBb D F (Bb)\nC Eb G (C)\nD F Ab (Eb)`"
                    },
                    "F# major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": f"`F# minor\nG# minor\nA# minor\nB major\nC# major\nD# minor\nE# dim`",
                        "Notes": f"`F# A# C# (E#)\nG# B D# (F#)\nA# C# E# (G#)\nB D# F# (A#)\nC# E# G# (B)\nD# F# A# (C#)\nE# G# B (D#)`"
                    },
                    "Gb major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Gb major\nAb major\nBb minor\nCb major\nDb major\nEb minor\nF dim`",
                        "Notes": "`Gb Bb Db (F)\nAb Cb Eb (Gb)\nBb Db F (Ab)\nCb Eb Gb (Bb)\nDb F Ab (Cb)\nEb Gb Bb (Db)\nF Ab Cb (Eb)`"
                    },
                    "G# major": "Most commonly notated as Ab major.",
                    "Ab major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Ab major\nBb minor\nC minor\nDb major\nEb major\nF minor\nG dim`",
                        "Notes": "`Ab C Eb (G)\nBb Db F (Ab)\nC Eb G (Bb)\nDb F Ab (C)\nEb G Bb (Db)\nF Ab C (Eb)\nG Bb Db (F)`"
                    },
                    "A# major": "Most commonly notated as Bb major.",
                    "Bb major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Bb major\nC minor\nD minor\nEb major\nF major\nG minor\nA dim`",
                        "Notes": "`Bb D F (A)\nC Eb G (Bb)\nD F A (A)\nEb G Bb (D)\nF A C (Eb)\nG Bb D (F)\nA C Eb (G)`"
                    },
                    "B# major": "Most commonly notated as Cb major.",
                    "Cb major": {
                        "Degree": "`I\nii\niii\nIV\nV\nvi\nvii{degree}`",
                        "Chords": "`Cb major\nDb minor\nEb minor\nFb major\nGb major\nAb minor\nBb dim`",
                        "Notes": "`Cb Eb Gb (Bb)\nDb Fb Ab (Cb)\nEb Gb Bb (Db)\nFb Ab Cb (Eb)\nGb Gb Db (F)\nAb Cb Eb (Gb)\nBb Db Fb (Ab)`"
                    }
                },
            "Minors": {
                    "C minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": "`C minor\nD dim\nEb major\nF minor\nG minor\nAb major\nBb major`",
                        "Notes": "`C Eb G (Bb)\nD F Ab (C)\nEb G Bb (D)\nF Ab C (Eb)\nG Bb D (F)\nAb C Eb (G)\nBb D F (Ab)`"
                    },
                    "D minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": "`D minor\nE dim\nF major\nG minor\nA minor\nBb major\nC major`",
                        "Notes": "`D F A (C)\nE G Bb (D)\nF Ab C (E)\nG Bb D (F)\nA C E (G)\nBb D F (A)\nC E G (Bb)`"
                    },
                    "E minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": f"`E minor\nF# dim\nG major\nA minor\nB minor\nC major\nD major`",
                        "Notes": f"`E G B (D)\nF# A C (E)\nG B D (F#)\nA C E (G)\nB D F# (A)\nC E G (B)\nD F# A (C)`"
                    },
                    "F minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": "`F minor\nG dim\nAb major\nBb minor\nC minor\nDb major\nEb major`",
                        "Notes": "`F Ab C (Eb)\nG Bb Db (F)\nAb C Eb (G)\nBb Db F (Ab)\nC Eb G (Bb)\nDb F Ab (C)\nEb G Bb (Db)`"
                    },
                    "G minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": "`G minor\nA dim\nBb major\nC minor\nD minor\nEb major\nF major`",
                        "Notes": "`G Bb D (F)\nA C Eb (G)\nBb D F (A)\nC Eb G (Bb)\nD F A (C)\nEb G Bb (D)\nF Ab C (Eb)`"
                    },
                    "A minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": "`A minor\nB dim\nC major\nD minor\nE minor\nF major\nG major`",
                        "Notes": "`A C E (G)\nB D F (A)\nC E G (B)\nD F A (C)\nE G B (D)\nF A C (E)\nG B D (F)`"
                    },
                    "B minor": {
                        "Degree": f"`i\nii{degree}\nIII\niv\nv\nVI\nVII`",
                        "Chords": f"`B minor\nC# dim\nD major\nE minor\nF# minor\nG major\nA major`",
                        "Notes": f"`B D F# (A)\nC# E G (B)\nD F# A (C#)\nE G B (D)\nF# A C# (E)\nG B D (F#)\nA C# E (G)`"
                    }
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