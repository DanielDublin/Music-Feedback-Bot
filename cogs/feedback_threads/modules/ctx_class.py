import discord

class ContextLike:
    def __init__(self, interaction: discord.Interaction, command=None):
        self._interaction = interaction
        self.author = interaction.user
        self.channel = interaction.channel
        self.guild = interaction.guild
        self.user = interaction.user 
        self.command = command
        self.guild = interaction.guild
        self.message = None

    async def send(self, *args, **kwargs):

        try:
            return await self._interaction.response.send_message(*args, **kwargs)
        except Exception:
            return await self._interaction.followup.send(*args, **kwargs)

