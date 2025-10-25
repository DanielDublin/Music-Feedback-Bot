import discord
from discord.ui import Button, View
import database.db as db


class PollView(View):
    def __init__(self, poll_manager, names, emojis):
        super().__init__(timeout=None)
        self.poll_manager = poll_manager
        self.names = names
        
        # Create button for each option
        for i, emoji in enumerate(emojis):
            button = Button(
                label="",
                custom_id=f"vote_{i}",
                style=discord.ButtonStyle.primary,
                emoji=emoji
            )
            button.callback = self.create_callback(i)
            self.add_item(button)
    
    def create_callback(self, index):
        """
        Creates a callback function for each button. Captures information for each user interaction for each button.
        
        Args:
            index (int): The index of the button and the corresponding name in self.names.
        
        Returns:
            callback (function): A function that takes a discord.Interaction object as an argument and calls self.poll_manager.handle_vote with the interaction, index, and name.
        """
        async def callback(interaction: discord.Interaction):
            await self.poll_manager.handle_vote(interaction, index, self.names[index])
        return callback


class CreatePoll:
    def __init__(self, bot):
        self.bot = bot

    async def scrape_channel_for_names(self, ctx, channel_id):
        # check that name doesn't equal bot as bot will send the initial message
        # Handle both ctx (regular command) and interaction (slash command)
        """
        Scrapes a channel for user names and returns them as a list.

        Handles both ctx (regular command) and interaction (slash command).
        Scrapes the artists who have posted their songs in the aotw channel.

        Args:
            ctx (discord.Context or discord.Interaction): The context or interaction of the command.
            channel_id (int): The ID of the channel to scrape.

        Returns:
            list[str]: A list of user names scraped from the channel.
        """
        user = ctx.user if hasattr(ctx, 'user') else ctx.author
        
        if user.name != self.bot.user.name:
            channel = self.bot.get_channel(channel_id)

            names = set()

            async for message in channel.history(limit=50):
                if message.author.name != self.bot.user.name:
                    names.add(message.author.display_name)

            return list(names)

    async def create_embed(self, ctx, names):
        emojis = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']

        embed = discord.Embed(
            title=f"Artist Of The Week Voting",
            description=f"Vote for our next Artist of the week! Give each song a listen and vote anonymously for your favorite.",
            color=discord.Color.blue()
        )

        # Add choices section
        choices_text = ""
        for i, name in enumerate(names[:len(emojis)]):
            choices_text += f"{emojis[i]} {name}\n"
        
        embed.add_field(name="Choices", value=choices_text, inline=False)
        
        # Add settings
        embed.add_field(name="Settings", value="🔒 Hidden Poll\n👤 1 allowed choice", inline=False)

        return embed, emojis[:len(names)]
    
    async def react_to_embed(self, ctx, embed, emojis, names):
        # Initialize poll data here when creating the poll
        """
        Initializes poll data and sends a message with a PollView to the specified context.

        Args:
            ctx (discord.Context or discord.Interaction): The context or interaction of the command.
            embed (discord.Embed): The embed to send with the message.
            emojis (list[str]): A list of emojis to use for the buttons.
            names (list[str]): A list of names to use for the buttons.

        Returns:
            discord.Message: The message that was sent.
        """
        self.names = names
        self.emojis = emojis
        self.votes = {i: 0 for i in range(len(names))}
        self.voters = set()
        
        # Create view with buttons
        view = PollView(self, names, emojis)
        
        # Send message - handle both ctx and interaction
        if hasattr(ctx, 'send'):
            # Regular command context
            self.poll_message = await ctx.send(embed=embed, view=view)
        else:
            # Slash command interaction - send to channel
            self.poll_message = await ctx.channel.send(embed=embed, view=view)
        
        return self.poll_message
    
    async def handle_vote(self, interaction, option_index, option_name):
        """Handle when someone votes"""
        # gets the user id from the interaction
        user_id = interaction.user.id
        
        # Check if already voted
        if user_id in self.voters:
            await interaction.response.send_message(
                "You've already voted in this poll!",
                ephemeral=True
            )
            return
        
        # Record vote
        self.votes[option_index] += 1
        self.voters.add(user_id)
        
        # Update votes channel
        await self.update_votes_channel()
        
        # Confirm vote to user (only they see this)
        await interaction.response.send_message(
            f"✅ Your vote for **{option_name}** has been recorded anonymously!",
            ephemeral=True
        )
    
    async def update_votes_channel(self):
        """Update the votes tracking channel"""
        votes_channel = self.bot.get_channel(1429975150039924806)
        
        if not votes_channel:
            return
        
        # Format vote results
        results_text = "**AOTW Votes**\n\n"
        for i, name in enumerate(self.names):
            votes = self.votes.get(i, 0)
            results_text += f"{self.emojis[i]} {name}: {votes} votes\n"
        
        results_text += f"\n**Total votes:** {len(self.voters)}"
        
        # Get existing messages
        messages = []
        async for msg in votes_channel.history(limit=1):
            messages.append(msg)
        
        # Update or create message
        if len(messages) == 0:
            await votes_channel.send(results_text)
        else:
            await messages[0].edit(content=results_text)
    
    async def determine_the_winner(self):
        """Find who won the poll"""
        if not self.votes:
            return None
        
        # Find max votes
        max_votes = max(self.votes.values())
        
        # Find all winners (in case of tie)
        winners = [
            self.names[i] for i, votes in self.votes.items()
            if votes == max_votes
        ]
        
        return {
            'winners': winners,
            'votes': max_votes,
            'total_voters': len(self.voters)
        }