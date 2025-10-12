import discord
from discord.ext import commands
from discord import app_commands
from data.constants import FEEDBACK_CHANNEL_ID, SERVER_ID, FEEDBACK_ACCESS_CHANNEL_ID
from database.db import get_feedback_requests_mfs

class Tracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def pull_db_feedback(self):
        try:

            feedback_channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)

            requests = await get_feedback_requests_mfs()

            formatted_requests = []
            for req in requests:
                message_id = req.get("message_id")
  
                message = await feedback_channel.fetch_message(int(message_id))
                user_id = message.author.id
                user_name = message.author.display_name
                formatted_requests.append({
                    "request_id": req.get("request_id"),
                    "message_id": message_id,
                    "points_requested": req.get("points_requested_to_use", 0),
                    "points_remaining": req.get("points_remaining", 0),
                    "message_link": message.jump_url,
                    "user_id": user_id,
                    "user_name": user_name
                })

            return formatted_requests
        except Exception as e:
            print(f"Error fetching feedback requests: {str(e)}.")
            return []

async def setup(bot):
    await bot.add_cog(Tracker(bot))