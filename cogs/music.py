import discord
from discord.ext import commands
import json
import logging
from modules.cooldowns import admin_bypass_cooldown

logger = logging.getLogger(__name__)


class _OptionButton(discord.ui.Button):
    def __init__(self, label: str, option: str, notes_view: 'NotesView', row: int):
        super().__init__(style=discord.ButtonStyle.primary, label=label[:80], row=row)
        self.option = option
        self.notes_view = notes_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.notes_view.user_id:
            await interaction.response.send_message(
                "Please use your own menu with the `<MF notes` command", ephemeral=True
            )
            return
        self.notes_view.selections.append(self.option)
        self.notes_view.current_level += 1
        self.notes_view.page_index = 0
        await self.notes_view._update(interaction)


class _NavButton(discord.ui.Button):
    def __init__(self, label: str, nav_type: str, notes_view: 'NotesView'):
        super().__init__(style=discord.ButtonStyle.secondary, label=label, row=4)
        self.nav_type = nav_type
        self.notes_view = notes_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.notes_view.user_id:
            await interaction.response.send_message(
                "Please use your own menu with the `<MF notes` command", ephemeral=True
            )
            return
        if self.nav_type == 'back':
            self.notes_view.current_level -= 1
            self.notes_view.selections.pop()
            self.notes_view.page_index = 0
        elif self.nav_type == 'prev':
            self.notes_view.page_index -= 1
        elif self.nav_type == 'next':
            self.notes_view.page_index += 1
        await self.notes_view._update(interaction)


class NotesView(discord.ui.View):
    OPTIONS_PER_PAGE = 7

    def __init__(self, user_id: int, json_data: dict, pfp_url: str, guild_icon_url: str):
        super().__init__(timeout=60.0)
        self.user_id = user_id
        self.json_data = json_data
        self.pfp_url = pfp_url
        self.guild_icon_url = guild_icon_url
        self.current_level = 0
        self.selections: list[str] = []
        self.page_index = 0
        self.current_options: list[str] = []
        self.message: discord.Message | None = None

    def _get_options(self, output=False):
        data = self.json_data
        for i in range(self.current_level):
            sel = self.selections[i]
            if sel in data:
                data = data[sel]
            else:
                return {} if output else []
        if output:
            return data
        if isinstance(data, dict):
            return list(data.keys())
        if isinstance(data, str):
            return [data]
        return []

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(color=0x7e016f)
        embed.set_footer(text="Made by FlamingCore", icon_url=self.pfp_url)
        self.clear_items()

        raw = self._get_options(output=True)

        # Terminal state: string leaf (Info section scale/key descriptions)
        if isinstance(raw, str):
            name = self.selections[-1] if self.selections else "Info"
            embed.set_author(name=name, icon_url=self.guild_icon_url)
            embed.description = raw
            if self.current_level > 0:
                self.add_item(_NavButton("↩️ Back", 'back', self))
            return embed

        options = self._get_options()
        self.current_options = options
        pages = [options[i:i + self.OPTIONS_PER_PAGE] for i in range(0, len(options), self.OPTIONS_PER_PAGE)]
        self.page_index = max(0, min(self.page_index, max(len(pages) - 1, 0)))

        # Terminal state: show Degree / Chords / Notes values
        is_terminal = (
            len(options) == 3
            and {"Degree", "Chords", "Notes"}.issubset(set(options))
        )
        if is_terminal:
            chord_name = self.selections[-1] if self.selections else "Unknown Chords"
            embed.set_author(name=f"{chord_name} Chords", icon_url=self.guild_icon_url)
            for key in ("Degree", "Chords", "Notes"):
                val = raw.get(key, "")
                if val:
                    embed.add_field(name=key, value=f"`{val.replace('{degree}', '°')}`", inline=True)
            if self.current_level > 0:
                self.add_item(_NavButton("↩️ Back", 'back', self))
            return embed

        current_page = pages[self.page_index] if pages else []
        chord_name = self.selections[-1] if self.selections else "Menu"
        embed.set_author(name=chord_name, icon_url=self.guild_icon_url)
        embed.description = "\n".join(f"{i + 1}. {opt}" for i, opt in enumerate(current_page))
        if len(pages) > 1:
            embed.set_footer(
                text=f"Page {self.page_index + 1} of {len(pages)} | Made by FlamingCore",
                icon_url=self.pfp_url
            )

        # Option buttons: up to 5 per row, spread across rows 0-1
        for i, opt in enumerate(current_page):
            self.add_item(_OptionButton(f"{i + 1}. {opt}"[:80], opt, self, row=i // 5))

        # Navigation buttons always on row 4
        if self.current_level > 0:
            self.add_item(_NavButton("↩️ Back", 'back', self))
        if self.page_index > 0:
            self.add_item(_NavButton("⬅️", 'prev', self))
        if len(pages) > 1 and self.page_index < len(pages) - 1:
            self.add_item(_NavButton("➡️", 'next', self))

        return embed

    async def _update(self, interaction: discord.Interaction):
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._notes_data = None

    async def cog_load(self):
        with open("cogs/options.json", "r") as file:
            self._notes_data = json.load(file)

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    @commands.command(help="Use to see the chord/notes information menu.")
    @admin_bypass_cooldown(1, 10)
    async def notes(self, ctx):
        pfp_url = await self.bot.get_owner_pfp_url()
        view = NotesView(ctx.author.id, self._notes_data, pfp_url, ctx.guild.icon.url)
        embed = view.build_embed()
        view.message = await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Music(bot))
