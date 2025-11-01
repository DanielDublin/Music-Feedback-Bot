import discord
from discord.ui import Button, View
import database.db as db
from data.constants import AOTW_SUBMISSIONS


class PollView(View):
    def __init__(self, poll_manager, names, emojis, messages):
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
        async def callback(interaction: discord.Interaction):
            await self.poll_manager.handle_vote(interaction, index, self.names[index])
        return callback


class CreatePoll:
    def __init__(self, bot):
        self.bot = bot
        self.messages = {}  # Store message content for each user
        self.voter_choices = {}  # Store user ID to option index mapping

    async def scrape_channel_for_names(self, ctx, channel_id):
        """
        Scrapes a channel for user names and their message content.

        Args:
            ctx (discord.Context or discord.Interaction): The context or interaction of the command.
            channel_id (int): The ID of the channel to scrape.

        Returns:
            list: List of user names.
        """
        user = ctx.user if hasattr(ctx, 'user') else ctx.author
        
        if user.name != self.bot.user.name:
            channel = self.bot.get_channel(channel_id)
            names = set()
            self.messages = {}  # Reset messages dict

            async for message in channel.history(limit=50):
                if message.author.name != self.bot.user.name:
                    names.add(message.author.display_name)
                    self.messages[message.author.display_name] = message.content

            return list(names)

    async def create_embed(self, ctx, names):
        emojis = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']

        embed = discord.Embed(
            title="Artist Of The Week Voting",
            description="Vote for our next Artist of the week! Give each song a listen and vote anonymously for your favorite.",
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
        """
        Initializes poll data and sends a message with a PollView.

        Args:
            ctx (discord.Context or discord.Interaction): The context or interaction.
            embed (discord.Embed): The embed to send.
            emojis (list[str]): List of emojis for buttons.
            names (list[str]): List of names for buttons.

        Returns:
            discord.Message: The message sent.
        """
        self.names = names
        self.emojis = emojis
        self.votes = {i: 0 for i in range(len(names))}
        self.voters = set()
        self.voter_choices = {}  # Reset voter choices
        
        # Create view with buttons
        view = PollView(self, names, emojis, self.messages)
        
        # Get the AOTW submissions channel
        poll_channel = self.bot.get_channel(AOTW_SUBMISSIONS)
        
        if not poll_channel:
            print("AOTW submissions channel not found!")
            return None
        
        # Send to AOTW submissions channel
        self.poll_message = await poll_channel.send(embed=embed, view=view)
        
        return self.poll_message
    
    async def handle_vote(self, interaction, option_index, option_name):
        """Handle when someone votes"""
        user_id = interaction.user.id
        
        if user_id in self.voters:
            await interaction.response.send_message(
                "You've already voted in this poll!",
                ephemeral=True
            )
            return
        
        # Record vote
        self.votes[option_index] += 1
        self.voters.add(user_id)
        self.voter_choices[user_id] = option_index  # Store who voted for whom
        
        # Update votes channel
        await self.update_votes_channel()
        
        # Confirm vote to user
        await interaction.response.send_message(
            f"✅ Your vote for **{option_name}** has been recorded anonymously!",
            ephemeral=True
        )
    
    async def update_votes_channel(self):
        """Update the votes tracking channel with vote counts and voter list"""
        votes_channel = self.bot.get_channel(1429975150039924806)
        
        if not votes_channel:
            return
        
        # Format vote results
        results_text = "**AOTW Votes**\n\n"
        for i, name in enumerate(self.names):
            votes = self.votes.get(i, 0)
            results_text += f"{self.emojis[i]} {name}: {votes} votes\n"
        
        results_text += f"\n**Total votes:** {len(self.voters)}\n"
        
        # Add list of who voted for whom (admin/visible based on your needs)
        results_text += "\n**Who Voted for Whom:**\n"
        for i, name in enumerate(self.names):
            voters = [self.bot.get_user(user_id).display_name for user_id, choice in self.voter_choices.items() if choice == i]
            if voters:
                results_text += f"{self.emojis[i]} {name}: {', '.join(voters)}\n"
            else:
                results_text += f"{self.emojis[i]} {name}: No votes yet\n"
        
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
        votes_channel = self.bot.get_channel(1429975150039924806)
        
        if not votes_channel:
            return None
        
        # Get the most recent message from votes channel
        message = None
        async for msg in votes_channel.history(limit=1):
            message = msg
            break
        
        if not message:
            return None
        
        # Parse the message content
        lines = message.content.split('\n')
        
        vote_counts = {}
        
        for line in lines:
            # Look for lines with vote counts (e.g., "lilbocx: 1 votes" or "🇦 lilbocx: 1 votes")
            if ':' in line and 'votes' in line.lower() and not line.startswith('**'):
                # Split on the LAST colon to handle names with colons
                parts = line.rsplit(':', 1)
                if len(parts) == 2:
                    # Get name part and vote part
                    name_part = parts[0].strip()
                    vote_part = parts[1].strip()
                    
                    # Remove emoji if present - just take everything after the first space
                    if ' ' in name_part:
                        # Split and take everything after first element (which would be emoji)
                        name_parts = name_part.split(' ', 1)
                        name = name_parts[1] if len(name_parts) > 1 else name_parts[0]
                    else:
                        name = name_part
                    
                    # Get vote count (first word in vote_part)
                    try:
                        votes = int(vote_part.split()[0])
                        vote_counts[name] = votes
                    except (ValueError, IndexError):
                        pass
        
        if not vote_counts:
            return None
        
        # Find winner(s)
        max_votes = max(vote_counts.values())
        winners = [name for name, votes in vote_counts.items() if votes == max_votes]
        
        return {
            'winners': winners,
            'votes': max_votes,
            'vote_counts': vote_counts
        }