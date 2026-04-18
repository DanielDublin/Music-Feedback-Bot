import discord
from discord.ext import commands, menus
import json
import asyncio
from modules.cooldowns import admin_bypass_cooldown



class NotesMenu(menus.Menu):
    def __init__(self, ctx, bot, json_data, pfp_url):
        super().__init__(timeout=60.0, delete_message_after=True, clear_reactions_after=True)
        self.json_data = json_data
        self.current_level = 0
        self.selections = []
        self.bot = bot
        self.menu_message = None
        self.user_id = ctx.author.id
        self.page_index = 0
        self.options_per_page = 7  # Number of options per page
        self.pfp_url = pfp_url
        # Listener is registered in send_initial_message, after the menu message exists


    async def on_raw_reaction_add(self, payload):
        if self.menu_message is None:
            return
        if payload.message_id != self.menu_message.id:
            return
        if payload.user_id == self.bot.user.id:
            return
        if payload.user_id != self.user_id:
            msg = await self.menu_message.channel.send(
                f"{payload.member.mention} Please use your own menu with the ``<MF notes`` command")
            await asyncio.sleep(3)
            await msg.delete()
            return

        message_id = payload.message_id
        channel_id = payload.channel_id
        channel = self.bot.get_channel(channel_id)

        if not channel:
            return

        try:
            menu_message = await channel.fetch_message(message_id)
        except discord.NotFound:
            return

        if menu_message.author != self.bot.user:
            return

        try:
            await menu_message.clear_reactions()
        except discord.Forbidden:
            pass

        emoji = str(payload.emoji)
        if emoji == "↩️" and self.current_level > 0:
            self.current_level -= 1
            self.selections.pop()
        elif emoji == "⬅️":
            if self.page_index > 0:
                self.page_index -= 1
        elif emoji == "➡️":
            if self.page_index < len(self.pages) - 1:
                self.page_index += 1
        elif emoji.endswith("\u20e3"):
            # Option selection
            index = int(emoji[0]) - 1  # Convert emoji number to index
            option_index = index + self.page_index * self.options_per_page
            if 0 <= option_index < len(self.current_options):
                self.selections.append(self.current_options[option_index])
                self.current_level += 1

        await self.send_menu(menu_message, update=True)

    async def send_menu(self, message, update=False):
        if not update:
            self.page_index = 0
        await self.show_page(message)

    async def show_page(self, message):

        options = self.get_options()
        self.current_options = options  # Store the current options for pagination
        self.pages = [options[i:i + self.options_per_page] for i in range(0, len(options), self.options_per_page)]
        if self.page_index < 0:
            self.page_index = 0
        if self.page_index >= len(self.pages):
            self.page_index = len(self.pages) - 1


        if len(options) == 3 and "Degree" in options and "Chords" in options and "Notes" in options:

            values = self.get_options(output=True)

            embed = discord.Embed(color=0x7e016f)
            chord_name = self.selections[-1] if self.selections else "Unknown Chords"
            embed.set_author(name=f"{chord_name} Chords", icon_url=message.guild.icon.url)

            degree_values = values['Degree']
            chords_values = values['Chords']
            notes_values = values['Notes']

            if degree_values:
                degree_values = degree_values.replace('{degree}', '°')
                embed.add_field(name="Degree", value=f"`{degree_values}`", inline=True)
            if chords_values:
                chords_values = chords_values.replace('{degree}', '°')
                embed.add_field(name="Chords", value=f"`{chords_values}`", inline=True)
            if notes_values:
                notes_values = notes_values.replace('{degree}', '°')
                embed.add_field(name="Notes", value=f"`{notes_values}`", inline=True)

            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)

            if self.menu_message is None:
                self.menu_message = await message.channel.send(embed=embed)
            else:
                await self.menu_message.edit(embed=embed)

            # Terminal state reached — clean up listener now
            self.bot.remove_listener(self.on_raw_reaction_add)
            return

        else:
            embed = discord.Embed(color=0x7e016f,
                                  description="\n".join(f"{index + 1}. {option}" for index, option in
                                                        enumerate(self.pages[self.page_index]))
                                  )
            chord_name = self.selections[-1] if self.selections else "Menu"
            embed.set_author(name=f"{chord_name}", icon_url=message.guild.icon.url)

            if self.page_index > 0:
                embed.set_footer(text="Page {} of {}".format(self.page_index + 1, len(self.pages)))

            if self.current_level > 0:
                embed.add_field(name="Go Back", value="↩️", inline=False)

            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)

            if self.menu_message is None:
                self.menu_message = await message.channel.send(embed=embed)
            else:
                await self.menu_message.edit(embed=embed)

        if self.current_level > 0:
            await self.menu_message.add_reaction("↩️")

        if len(options) > 1 and not (
                len(options) == 3 and "Degree" in options and "Chords" in options and "Notes" in options):
            for i in range(len(self.pages[self.page_index])):
                emoji_label = f"{i + 1}\u20e3"
                await self.menu_message.add_reaction(emoji_label)

        if self.page_index > 0:
            await self.menu_message.add_reaction("⬅️")
        if len(self.pages) > 1 and self.page_index < len(self.pages) - 1:
            await self.menu_message.add_reaction("➡️")

    def get_options(self, output=False):
        options = []

        data = self.json_data
        for i in range(self.current_level):
            selection = self.selections[i]
            if selection in data:
                data = data[selection]
            else:
                return options

        if output:
            return data

        if isinstance(data, dict):
            options = list(data.keys())
        elif isinstance(data, str):
            options.append(data)

        return options

    def stop(self):
        self.bot.remove_listener(self.on_raw_reaction_add)
        super().stop()

    async def send_data(self, ctx, data):
        embed = discord.Embed(description=data)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await ctx.send(embed=embed)

    async def send_initial_message(self, ctx, channel):
        options = self.get_options()
        self.current_options = options
        self.user = ctx.author
        self.guild = ctx.guild
        await self.send_menu(ctx)
        # Register listener only after the menu message exists
        self.bot.add_listener(self.on_raw_reaction_add)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._pfp_url = None  # cached so we don't hit the API on every command
        self._notes_data = None  # cached JSON to avoid disk read on every command

    async def cog_load(self):
        with open("cogs/options.json", "r") as file:
            self._notes_data = json.load(file)

    def guild_only(ctx):
        return ctx.guild is not None

    async def _get_pfp_url(self):
        if self._pfp_url is None:
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self._pfp_url = creator_user.avatar.url
        return self._pfp_url

    @commands.check(guild_only)
    @commands.command(help= "Use to see the chord/notes information menu.")
    @admin_bypass_cooldown(1, 10)
    async def notes(self, ctx):
        pfp_url = await self._get_pfp_url()
        menu = NotesMenu(ctx, self.bot, self._notes_data, pfp_url)
        await menu.start(ctx)


async def setup(bot):
    await bot.add_cog(Music(bot))
