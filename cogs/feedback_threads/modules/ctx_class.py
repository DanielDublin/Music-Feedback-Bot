import discord
from discord import app_commands # Import app_commands
from discord.ui import View # Import View for type checking

class ContextLike:
    """
    A class that mimics a discord.Context or discord.Interaction for simpler
    passing around in helper functions, especially for App Commands.
    """
    def __init__(self, interaction: discord.Interaction, command: app_commands.Command = None, custom_author: discord.Member = None):
        """
        Initializes a ContextLike object.
        
        Args:
            interaction (discord.Interaction): The original interaction object.
            command (app_commands.Command, optional): The command that was invoked. Defaults to None.
            custom_author (discord.Member, optional): An optional custom author to use for ctx.author.
                                                    Useful when performing actions on behalf of another user.
        """
        self.bot = interaction.client
        self.guild = interaction.guild
        self.author = custom_author if custom_author else interaction.user # Use custom_author if provided, else original interaction user
        self.channel = interaction.channel # This will be the channel where the admin command was used
        self.command = command
        self.interaction = interaction # Store the original interaction
        
        # Flags for interaction response management
        self.sent_message = None # To store the message sent by ctx.send
        self.responded = False # To track if interaction.response.send_message was used

    async def send(self, content=None, *, ephemeral=False, embed=None, embeds=None, view: View = None, file=None, files=None):
        """
        Sends a message, handling interaction response vs. followup.
        Note: This sends to the channel where the original interaction occurred.
        If you intend to send to a specific thread, you must call `thread_object.send()` directly.
        """
        # Start with base parameters
        send_kwargs = {
            "content": content,
            "ephemeral": ephemeral,
        }
        
        # --- Crucial Changes Here: Conditionally add 'embed', 'embeds', 'view', 'file', and 'files' ---
        # Prioritize 'embeds' (list of embeds) over 'embed' (single embed)
        if embeds is not None:
            send_kwargs["embeds"] = embeds
        elif embed is not None:
            send_kwargs["embed"] = embed

        if view is not None:
            send_kwargs["view"] = view
        
        # Prioritize 'files' (list of files) over 'file' (single file)
        if files is not None:
            send_kwargs["files"] = files
        elif file is not None:
            send_kwargs["file"] = file

        if not self.responded and not self.interaction.response.is_done():
            # If interaction hasn't been responded to yet, use response.send_message
            await self.interaction.response.send_message(**send_kwargs)
            self.responded = True
        else:
            # If interaction has been responded to, use followup.send
            self.sent_message = await self.interaction.followup.send(**send_kwargs)

    # You might want to add other common ctx methods here if needed,
    # e.g., edit, delete, etc., adapting them for interactions.
