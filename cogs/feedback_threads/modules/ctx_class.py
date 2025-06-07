import discord

class ContextLike:
    def __init__(self, interaction: discord.Interaction, command=None):
        self._interaction = interaction # Correctly stores the interaction
        self.author = interaction.user
        self.channel = interaction.channel
        self.guild = interaction.guild
        self.user = interaction.user 
        self.command = command
        self.message = None

    @property # Add this decorator
    def interaction(self):
        return self._interaction

    async def send(self, *args, **kwargs):
        try:
            # Now accessing via the @property 'interaction'
            return await self.interaction.response.send_message(*args, **kwargs) 
        except Exception:
            # Now accessing via the @property 'interaction'
            return await self.interaction.followup.send(*args, **kwargs)

