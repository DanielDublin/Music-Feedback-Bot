from discord.ext import commands, menus
import discord
from discord import app_commands
from datetime import datetime



class HelpMenu(menus.Menu):
    def __init__(self, bot, pfp_url):
        super().__init__(timeout=180.0, delete_message_after=True, clear_reactions_after=True)
        self.user = None
        self.main_menu = None
        self.is_main = True
        self.bot = bot
        self.bot.add_listener(self.on_raw_reaction_add)
        self.page_index =0
        self.guild = None
        self.message = None
        self.pfp_url = pfp_url
        
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.user.id:
            if payload.emoji.name == '↩️' and not self.is_main:
                self.is_main = True
                self.page_index =0
                await self.message.clear_reactions()
                await self.update_main_menu()
                
            elif payload.emoji.name == "⬅️" and not self.is_main:
                self.page_index -=1    
                await self.message.clear_reaction('⬅️') 
                await self.message.clear_reaction('➡️') 
                await self.show_page(self.page_index)
                
            elif payload.emoji.name == "➡️" and not self.is_main:
                self.page_index +=1
                await self.message.clear_reaction('⬅️') 
                await self.message.clear_reaction('➡️') 
                await self.show_page(self.page_index)
            
            

    async def send_initial_message(self, ctx, channel):
        self.user = ctx.author
        self.guild = ctx.guild
        return await ctx.send(embed=self.get_main_menu())

    def get_main_menu(self):
    
        embed = discord.Embed(title="Help Menu", color=0x7e016f)
        embed.add_field(name="1️⃣ General", value="Show general commands", inline=False)
        embed.add_field(name="2️⃣ Admin", value="Show admin commands", inline=False)  
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
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
        
        general_commands = [
        cmd for cmd in self.bot.commands
        if cmd.cog_name is not None  # Exclude commands with no cog
        and cmd.cog_name != 'Owner_Utilities'  # Exclude commands from the Owner Utilities cog
        ]
        
        custom_order = {
        "r": 1,
        "s": 2,
        "points": 3,
        "submit": 4,
        "top": 5,
        "notes": 6,
        "genres": 7,
        "similar": 8,
        "help": 9
        }

        # Sort self.bot.commands based on the custom order
        general_commands = sorted(general_commands, key=lambda cmd: custom_order.get(cmd.name.lower(), 999))
        
        per_page = 5  # Number of commands to display per page
        pages = [general_commands[i:i + per_page] for i in range(0, len(general_commands), per_page)]

        if not pages:
            await self.message.edit(embed=self.get_no_commands_embed())
        else:
            self.pages = pages
            self.page_index = 0
            await self.show_page(self.page_index)
        

    async def show_page(self, page_index, is_admin = False):
        commands = self.pages[page_index]
        
        embed = None
        if not is_admin:
            embed = self.get_general_commands_embed(commands, page_index)
        else:
            embed = self.get_admin_commands_embed(commands, page_index)
            
        await self.message.edit(embed=embed)
        await self.add_page_reactions()

    def get_no_commands_embed(self):
        embed = discord.Embed(title="No commands available", color=0x7e016f)
        return embed
    def get_no_perms_embed(self):
        embed = discord.Embed(title="You have no power here!", color=0x7e016f)
        embed.set_image(url="https://media.tenor.com/GYeAvy0kg0MAAAAC/gandalf-laughing.gif")
        return embed

    def get_general_commands_embed(self, commands, page_index):
        embed = discord.Embed(
            title="General Commands",
            color=0x7e016f
        )

        for index, command in enumerate(commands, start=page_index * 5):
            # Display the command's name with its index and description
            embed.add_field(
                name=f"{chr(ord('A') + index)})  <MF {command.name.title()} {command.brief or ' '}".replace("<MF R ", "<MFR ").replace("<MF S ", "<MFS "),
                value=command.help or "No description",
                inline=False
            )

        # Set the page number in the footer
        embed.set_footer(text=f"Made by FlamingCore  -  Page {page_index + 1}/{len(self.pages)}", icon_url=self.pfp_url)
        return embed

    def get_admin_commands_embed(self, commands, page_index):
            embed = discord.Embed(
                title="Admin Commands",
                color=0x7e016f
            )

            for index, command in enumerate(commands, start=page_index * 5):
                # Display the command's name with its index and description
                embed.add_field(
                    name=f"{chr(ord('A') + index)})  /{command.qualified_name.title()}",
                    value=command.description or "No description",
                    inline=False
                )

            # Set the page number in the footer
            embed.set_footer(text=f"Made by FlamingCore  -  Page {page_index + 1}/{len(self.pages)}", icon_url=self.pfp_url)
            return embed

    async def add_page_reactions(self):
        if self.page_index > 0:
            await self.message.add_reaction("⬅️")  # Left arrow (only if there's a previous page)
        if len(self.pages) > 1 and self.page_index < len(self.pages) - 1:
            await self.message.add_reaction("➡️")  # Right arrow (only if there's a next page)

    @menus.button("2️⃣")
    async def on_admin(self, payload):
        await self.message.clear_reactions()
        await self.message.add_reaction("↩️")
        self.is_main = False
        
        if not payload.member.guild_permissions.administrator:
            await self.message.edit(embed=self.get_no_perms_embed())
            return
            

        admin_commands = [command for command in self.bot.tree.walk_commands() if isinstance(command, app_commands.Command)]
        admin_commands = sorted(admin_commands, key=lambda cmd: cmd.qualified_name.lower())
        
        per_page = 5  # Number of commands to display per page
        pages = [admin_commands[i:i + per_page] for i in range(0, len(admin_commands), per_page)]

        if not pages:
            await self.message.edit(embed=self.get_no_commands_embed())
        else:
            self.pages = pages
            self.page_index = 0
            await self.show_page(self.page_index, True)



class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command(help= "Use to see this menu.")
    async def help(self, ctx):
        
        creator_user = await self.bot.fetch_user(self.bot.owner_id)
        pfp_url = creator_user.avatar.url
        self.menu = HelpMenu(self.bot, pfp_url)
        await self.menu.start(ctx)
        
async def setup(bot):
    await bot.add_cog(HelpCog(bot))
