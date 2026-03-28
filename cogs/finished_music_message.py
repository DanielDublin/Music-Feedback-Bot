import discord
import asyncio
from discord.ext import commands, tasks
from data.constants import FINISHED_MUSIC

class FinishedMusicMessage(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.stored_message_id = None
        self.stored_channel_id = FINISHED_MUSIC

    async def cog_load(self):
        """Called when the cog is loaded - starts the background task."""
        self.delete_and_repost_cycle.start()

    async def cog_unload(self):
        """Called when the cog is unloaded - stops the background task."""
        self.delete_and_repost_cycle.cancel()

    @tasks.loop(hours=24)
    async def delete_and_repost_cycle(self):
        """Delete and repost the message every 24 hours."""
        
        # 1. Force the ID to be an integer
        channel = self.client.get_channel(int(self.stored_channel_id))
        
        # 2. Check if the channel actually exists first
        if not channel:
            print(f"Channel with ID {self.stored_channel_id} not found. Check permissions and ID!")
            return

        # 3. Try to delete the old message ONLY if we have an ID stored
        if self.stored_message_id:
            try:
                old_message = await channel.fetch_message(self.stored_message_id)
                await old_message.delete()
            except discord.NotFound:
                print("Message not found, may have been manually deleted.")
            except discord.HTTPException as e:
                print(f"Error deleting message: {e}")
        
        # 4. ALWAYS send the new message, regardless of whether an old one was deleted
        message_text = "**Deleted song?** If your name is green, you have the Groupies role and have 5-minute access to this channel! Stay active in the server for a few days and quickly rank up for full access."
        
        try:
            new_message = await channel.send(message_text)
            self.stored_message_id = new_message.id  # Save the new ID for tomorrow
        except discord.HTTPException as e:
            print(f"Error sending new message: {e}")

    @delete_and_repost_cycle.before_loop
    async def before_cycle(self):
        """Wait for bot to be ready, then recover the lost ID from history."""
        await self.client.wait_until_ready()
        
        channel = self.client.get_channel(int(self.stored_channel_id))
        if not channel:
            print("Could not find the Finished Music channel during setup.")
            return

        message_found = False
        
        # 1. Search the last 50 messages in the channel
        async for message in channel.history(limit=50):
            # 2. Check if the message is from our bot AND contains our specific text
            if message.author == self.client.user and "**Deleted song?**" in message.content:
                self.stored_message_id = message.id
                message_found = True
                print(f"Recovered existing message ID from history: {self.stored_message_id}")
                break # Stop searching once we find it
        
        # 3. If the bot restarts and the channel is totally empty, send it now
        if not message_found:
            message_text = "**Deleted song?** If your name is green, you have the Groupies role and have 5-minute access to this channel! Stay active in the server for a few days and quickly rank up for full access."
            try:
                new_msg = await channel.send(message_text)
                self.stored_message_id = new_msg.id
                print("No previous message found in history. Sent a new one.")
            except discord.HTTPException as e:
                print(f"Failed to send initial message: {e}")

async def setup(bot):
    await bot.add_cog(FinishedMusicMessage(bot))