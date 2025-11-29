import discord
from discord import ui
from datetime import datetime

class PaginationView(ui.View):
    def __init__(self, embeds, timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message = None
        
        # Disable previous button on first page
        self.previous_button.disabled = True
        
        # Disable next button if only one page
        if len(embeds) <= 1:
            self.next_button.disabled = True
    
    async def update_buttons(self):
        # Update button states
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
        
        # Update the message
        if self.message:
            await self.message.edit(embed=self.embeds[self.current_page], view=self)
    
    @ui.button(label="◀ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_buttons()
            await interaction.response.defer()
    
    @ui.button(label="Next ▶", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await self.update_buttons()
            await interaction.response.defer()
    
    async def on_timeout(self):
        # Disable buttons when view times out
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)
