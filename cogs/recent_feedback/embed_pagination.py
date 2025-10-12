from discord import ui
import discord
import math

class EmbedPagination(ui.View):
    def __init__(self, bot, requests, items_per_page=5):
        super().__init__(timeout=None)
        self.bot = bot
        self.requests = requests
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = math.ceil(len(requests) / items_per_page) if requests else 1

        # for edge cases
        self._update_buttons()

    def create_embed(self):

        embed = discord.Embed(title="Recent Feedback Requests", color=0x7e016f)
        
        if self.requests:

            # split up requests
            start_idx = self.current_page * self.items_per_page
            end_idx = start_idx + self.items_per_page
            page_requests = self.requests[start_idx:end_idx]

            for req in page_requests:

                username = req["user_name"].strip("[]")
                message_link = req["message_link"]
                request_id = req["request_id"]
                points_requested = req["points_requested"]
                points_remaining = req["points_remaining"]
                
                # Calculate feedbacks received
                feedbacks_received = points_requested - points_remaining
                
                embed.add_field(
                    name="",
                    value=f"**#{request_id}** - [{username}]({message_link}) ({feedbacks_received}/{points_requested} feedback received)",
                    inline=False
                )
        else:
            embed.add_field(
                name="No Requests",
                value="No open feedback requests found.",
                inline=False
            )

        return embed
    
    def create_help_embed(self):

        embed = discord.Embed(
            title="Feedback System Guide", 
            description="""YOU MUST GIVE FEEDBACK FIRST

        Use <MFR to give feedback.
        Use <MFS to submit your song for feedback.
        Use ⁠feedback-discussion for conversation.""",
            color=0x7e016f
        )

        return embed

    def _update_buttons(self):
        # no previous if on first page
        self.previous_button.disabled = self.current_page == 0
        # no next if on last page
        self.next_button.disabled = self.current_page == self.total_pages - 1

        # if only one page, no buttons
        if self.total_pages <= 1:
            self.previous_button.disabled = True
            self.next_button.disabled = True


    @ui.button(label="⬅️", style=discord.ButtonStyle.grey)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check if going back is possible
        if self.current_page > 0:
            # go back one page
            self.current_page -= 1

        self._update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
            

    @ui.button(label="➡️", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # check if going forward is possible
        if self.current_page < self.total_pages - 1:
            # go forward one page
            self.current_page += 1
        
        self._update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)


    @ui.button(label="Need help?", style=discord.ButtonStyle.grey)
    async def help_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.edit_message(embed=self.create_help_embed(), view=self)

