import discord
import asyncio
from discord.ext import commands, tasks
from data.constants import FINISHED_MUSIC

class FinishedMusicMessage(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.stored_message_id = None
        self.stored_channel_id = FINISHED_MUSIC
        self.message_sent = False

    async def cog_load(self):
        """Called when the cog is loaded - starts the background task."""
        self.delete_and_repost_cycle.start()

    async def cog_unload(self):
        """Called when the cog is unloaded - stops the background task."""
        self.delete_and_repost_cycle.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        """Send initial message when bot is ready."""
        if not self.message_sent:
            await self.send_finished_message()
            self.message_sent = True

    async def send_finished_message(self):
        """Send a message to the specified channel when music finishes."""
        channel = self.client.get_channel(FINISHED_MUSIC)

        print("Sending finished music message...")

        message_text = "**Deleted song?** If your name is green, you have the Groupies role and have 5-minute access to this channel! Stay active in the server for a few days and quickly rank up for full access."

        if channel:
            sent_message = await channel.send(message_text)
            self.stored_message_id = sent_message.id
        else:
            print(f"Channel with ID {FINISHED_MUSIC} not found")

    @tasks.loop(hours=24)
    async def delete_and_repost_cycle(self):
        """Delete and repost the message every 24 hours."""
        channel = self.client.get_channel(self.stored_channel_id)
        
        if channel and self.stored_message_id:
            try:
                # Fetch and delete the old message
                old_message = await channel.fetch_message(self.stored_message_id)
                await old_message.delete()
            except discord.NotFound:
                print("Message not found, may have been manually deleted")
            except discord.HTTPException as e:
                print(f"Error deleting message: {e}")
            
            # Send new message
            message_text = "**Deleted song?** If your name is green, you have the Groupies role and have 5-minute access to this channel! Stay active in the server for a few days and quickly rank up for full access."
            
            try:
                new_message = await channel.send(message_text)
                self.stored_message_id = new_message.id
            except discord.HTTPException as e:
                print(f"Error sending new message: {e}")
        else:
            print(f"Channel with ID {self.stored_channel_id} not found")

    @delete_and_repost_cycle.before_loop
    async def before_cycle(self):
        """Wait for bot to be ready before starting the loop."""
        await self.client.wait_until_ready()


async def setup(bot):
    await bot.add_cog(FinishedMusicMessage(bot))