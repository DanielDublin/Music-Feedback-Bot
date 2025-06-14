import discord
import requests
import json
import os
import re
from dotenv import load_dotenv
import database.db as db
from data.constants import SERVER_ID, FINISHED_MUSIC, AOTW_CHANNEL
from discord.ext import commands

load_dotenv()
token = os.environ.get('DISCORD_TEST_TOKEN')

class MemberCards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    async def get_username(self, member: discord.Member):

        return member.display_name

    async def get_pfp(self, member: discord.Member):
        
        return member.display_avatar

    async def get_join_date(self, member: discord.Member):

        return member.joined_at.strftime("%b %d, %Y")

    async def get_rank(self, member: discord.Member):

        aotw = "Artist of the Week"

        for role in reversed(member.roles):
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                if role.name == "Artist of the Week":
                    return aotw
                else:
                    return role.name

    async def get_points(self, member: discord.Member):

        points = await db.fetch_points(str(member.id))

        top_users = await db.top_10()
        for index, user_data in enumerate(top_users):
            if user_data["user_id"] == str(member.id):
                return index+1, points
            else:
                return points
            
    async def get_message_count(self, member: discord.Member):
        
        # url = f"https://discord.com/api/v9/guilds/{SERVER_ID}/messages/search?author_id={member.id}"
        # print(url)
    
        # headers = {
        #     'Authorization': f"Bot {token}",
        #     'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', # Use your browser's User-Agent
        #     'accept': '*/*',
        #     'accept-language': 'en-US,en;q=0.9',
        #     'accept-encoding': 'gzip, deflate', # As you noted, exclude 'br' if it causes issues
        #     'referer': 'https://discord.com/'
        # }

        # print(token)
        # print(headers)

        # try:
        #     response = requests.get(url, headers=headers)
        #     response.raise_for_status()
        #     data = response.json()
        # except requests.exceptions.RequestException as e:
        #     print(f"Error: {e}")
        #     return 0

        # try:
        #     if 'results' in data:
        #         message_count = data['results']
        #         return message_count
        #     else:
        #         return 0
        # except KeyError:
        #     return 0
        pass

    async def get_last_finished_music(self, member: discord.Member):

        finished_music_channel = self.bot.get_channel(FINISHED_MUSIC)
        aotw_channel = self.bot.get_channel(AOTW_CHANNEL)

        rank = await self.get_rank(member)
        aotw_role_name = "Artist of the Week"

        if rank == aotw_role_name:
            # get last message in AOTW channel regardless of who sent it 
            last_aotw_message = None
            async for message in aotw_channel.history(limit=1):
                last_aotw_message = message
                break

            # if there's a message in AOTW, hyperlink it
            if last_aotw_message:
                return f"[Special Artist of the Week Release](<{last_aotw_message.jump_url}>)"
            
        # if not AOTW, default to finished music
        else:
            # get latest message for member in finished music
            last_music_by_member = None
            async for message in finished_music_channel.history(limit=100):
                if message.author.id == member.id:
                    last_music_by_member = message
                    break

            # check for links or urls
            if last_music_by_member:
                url_detect_pattern = r"(?:https?://|www\.)[a-zA-Z0-9./-]+(?:\.[a-zA-Z]{2,})(?:/[^\s]*)?"
                finished_music_content = last_music_by_member.content
                detected_urls = re.findall(url_detect_pattern, finished_music_content)

                # if URL
                if detected_urls:
                    return f"[Latest Release](<{detected_urls[0]}>)"
                # if attachment
                elif last_music_by_member.attachments:
                    return f"[Latest Release](<{last_music_by_member.jump_url}>)"
                # posted in finish music, but not a link or attachment
                else:
                    return "Coming soon!"
            # if not AOTW or posted, then return
            else:
                return "Coming soon!"

    async def get_random_message(self, member: discord.Member):
        pass



async def setup(bot):
    await bot.add_cog(MemberCards(bot))


