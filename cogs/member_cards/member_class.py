import discord
import requests 
import json 
import os
import re
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import database.db as db 
from data.constants import SERVER_ID, FINISHED_MUSIC, AOTW_CHANNEL, GENERAL_CHAT_CHANNEL_ID, INTRO_MUSIC
from discord.ext import commands
import traceback 
from typing import Union

load_dotenv()
token = os.environ.get('DISCORD_TOKEN') 

class MemberCards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.TARGET_MAIN_GENRES = self._hex_to_rgb("#8d8c8c") 
        self.TARGET_DAW = self._hex_to_rgb("#6155a6") 
        self.TARGET_INSTRUMENTS = self._hex_to_rgb("#e3abff") 

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    async def get_username(self, member: discord.Member) -> str:
        return member.display_name

    async def get_pfp(self, member: discord.Member) -> str:
        if member.display_avatar.url:
            return str(member.display_avatar.url)
        else:
            return "https://discord.com/assets/f69a538202956c38266205842880b4c3.svg"

    async def get_join_date(self, member: discord.Member) -> datetime:
        return member.joined_at

    async def get_rank(self, member: discord.Member) -> str:
        aotw = "Artist of the Week"
        fans_role_name = "Fans" 
        roles_to_ignore = ["POO CAFE", "kangaroo", "emo nemo", "Event Host"]

        for role in reversed(member.roles): 
            if role.name in roles_to_ignore:
                continue
            
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                if role.name == aotw:
                    return aotw
                elif role.name == fans_role_name:
                    return fans_role_name
                else:
                    return role.name 
        return "No specific rank" 
            
    async def get_points(self, member: discord.Member):
        raw_points = await db.fetch_points(str(member.id))

        try:
            points = int(raw_points)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert raw points '{raw_points}' to int for member {member.display_name}. Defaulting to 0.")
            points = 0

        is_top_feedback = False
        try:
            top_users = await db.top_10()
            for user_data in top_users:
                if user_data.get("user_id") == str(member.id):
                    is_top_feedback = True
                    break 
        except Exception as e:
            print(f"Error fetching top 10 users from DB: {e}")
            is_top_feedback = False

        return is_top_feedback, points
            
    async def get_message_count(self, member: discord.Member) -> int:
        return 0 

    async def get_last_finished_music(self, member: discord.Member) -> str:
        """
        Retrieves the latest music release/link by the member based on their role.
        - Prioritizes AOTW messages if the member has that role.
        - If 'Fans' role: searches intro-music for last message with link/attachment.
        - Otherwise (regular member): searches finished-music for last message with link/attachment.
        Returns a clean URL string, or a descriptive text if no link is found.
        If a message has an attachment, the link will redirect to the message itself.
        """
        finished_music_channel = self.bot.get_channel(FINISHED_MUSIC)
        intro_music_channel = self.bot.get_channel(INTRO_MUSIC)
        aotw_channel = self.bot.get_channel(AOTW_CHANNEL)

        rank = await self.get_rank(member)
        aotw_role_name = "Artist of the Week"
        fans_role_name = "Fans"

        # Helper to extract URL from a message
        # UPDATED: Prioritize message.jump_url if attachments exist
        def extract_url_from_message(message: discord.Message) -> Union[str, None]:
            if message.attachments:
                return str(message.jump_url) # Redirect to the message if it has an attachment
            
            url_detect_pattern = r"(https?://\S+|www\.\S+)"
            detected_urls = re.findall(url_detect_pattern, message.content)
            if detected_urls:
                return detected_urls[0].strip('<>')
            return None # No direct link found in content or attachments


        # --- AOTW Logic (Highest Priority) ---
        if rank == aotw_role_name and aotw_channel and isinstance(aotw_channel, discord.TextChannel):
            print(f"Checking AOTW channel ({aotw_channel.name}) for {member.display_name}...")
            try:
                async for message in aotw_channel.history(limit=5):
                    url = extract_url_from_message(message)
                    if url:
                        print(f"Found AOTW message with URL: {url}")
                        return url

            except discord.Forbidden:
                print(f"Bot lacks permissions to read AOTW channel history.")
                return "Cannot access AOTW channel to find release."
            except discord.HTTPException as e:
                print(f"HTTP error fetching AOTW history: {e}")
                return "Error fetching AOTW release."

        # --- Fans (Intro Music) Logic ---
        elif rank == fans_role_name:
            if intro_music_channel and isinstance(intro_music_channel, discord.TextChannel):
                print(f"Checking Intro Music channel ({intro_music_channel.name}) for {member.display_name} (Fans)...")
                try:
                    async for message in intro_music_channel.history(limit=100): 
                        if message.author.id == member.id:
                            url = extract_url_from_message(message)
                            if url:
                                print(f"Found last intro music link for {member.display_name}: {url}")
                                return url
                    
                    print(f"No recent intro music message with a link/attachment found for {member.display_name}.")
                    return "No intro music link found."
                except discord.Forbidden:
                    print(f"Bot lacks permissions to read Intro Music channel history.")
                    return "Cannot access Intro Music channel to find release."
                except discord.HTTPException as e:
                    print(f"HTTP error fetching Intro Music history: {e}")
                    return "Error fetching intro music release."
            else:
                print("Intro Music channel not found or not a text channel.")
                return "Could not retrieve intro music info."

        # --- Default (Finished Music) Logic for other members ---
        else: # Covers all other roles (non-AOTW, non-Fans)
            if finished_music_channel and isinstance(finished_music_channel, discord.TextChannel):
                print(f"Checking Finished Music channel ({finished_music_channel.name}) for {member.display_name} (Default)...")
                try:
                    async for message in finished_music_channel.history(limit=100): 
                        if message.author.id == member.id:
                            url = extract_url_from_message(message)
                            if url:
                                print(f"Found last finished music link for {member.display_name}: {url}")
                                return url
                            elif message.attachments:
                                return str(message.jump_url)
                            else:
                                continue
                    print(f"No recent finished music message found for {member.display_name}.")
                    return "No music finished yet."
                except discord.Forbidden:
                    print(f"Bot lacks permissions to read Finished Music channel history.")
                    return "Cannot access Finished Music channel to find release."
                except discord.HTTPException as e:
                    print(f"HTTP error fetching Finished Music history: {e}")
                    return "Error fetching finished music release."
            else:
                print("Finished Music channel not found or not a text channel.")
                return "Could not retrieve finished music info."

    async def generate_random_date_range(self, member_join_date: datetime) -> tuple[datetime, datetime]:
        if member_join_date.tzinfo is None:
            member_join_date = member_join_date.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        time_since_join = now_utc - member_join_date

        if time_since_join.total_seconds() <= 0: 
            start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_of_day, end_of_day

        random_seconds_offset = random.uniform(0, time_since_join.total_seconds())
        random_timedelta = timedelta(seconds=random_seconds_offset)
        
        random_date_chosen = member_join_date + random_timedelta

        start_of_day_utc = random_date_chosen.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = random_date_chosen.replace(hour=23, minute=59, second=59, microsecond=999999)

        return start_of_day_utc, end_of_day_utc

    async def get_random_message(self, member: discord.Member) -> tuple[str, Union[str, None]]:
        """
        Retrieves a random message by the member from the general chat channel.
        This function is intended for members who are NOT 'Fans' or 'Artist of the Week',
        as their specific music links are handled by get_last_finished_music.
        Returns a tuple of (message_content, message_jump_url).
        """
        member_join_date_dt = await self.get_join_date(member)
        general_chat_channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)

        if not general_chat_channel or not isinstance(general_chat_channel, discord.TextChannel):
            print(f"Error: GENERAL_CHAT_CHANNEL (ID: {GENERAL_CHAT_CHANNEL_ID}) not found or not a text channel.")
            return "Couldn't find the general chat channel to look for messages!", None

        async def search_general_chat_for_random_message(channel: discord.TextChannel, join_date: datetime):
            # Strategy 1: Try 10 random days
            random_day_attempts = 15
            print(f"Attempting {random_day_attempts} random days for {member.display_name} in {channel.name}...")
            for attempt in range(random_day_attempts):
                start_of_day, end_of_day = await self.generate_random_date_range(join_date)
                
                print(f"  Random Attempt {attempt + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

                messages_by_member_on_day = []
                try:
                    async for message in channel.history(limit=100, after=start_of_day, before=end_of_day):
                        if message.author.id == member.id:
                            if message.content and message.content.strip():
                                messages_by_member_on_day.append(message)
                    
                    if messages_by_member_on_day:
                        chosen_message = random.choice(messages_by_member_on_day)
                        # For random messages, we always return the jump_url along with content
                        print(f"  SUCCESS (Random): Found message on {start_of_day.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                        return chosen_message.content, chosen_message.jump_url

                except discord.Forbidden:
                    print(f"  Error: Bot lacks permissions to read history in {channel.name}. Aborting random attempts.")
                    return "I don't have permission to look through message history in that channel.", None
                except discord.HTTPException as e:
                    print(f"  Error: HTTP error fetching history for {channel.name} (random day): {e}. Aborting random attempts.")
                    return "Something went wrong trying to fetch message history. Please try again later!", None
                except Exception as e:
                    print(f"  Error: An unexpected error occurred (random day): {e}. Aborting random attempts.")
                    traceback.print_exc()
                    return "An unexpected error occurred while looking for a message.", None

            print(f"Finished {random_day_attempts} random attempts for {member.display_name}. No suitable message found.")

            # --- Strategy 2: If random days fail, try the past 3 consecutive days ---
            now_utc = datetime.now(timezone.utc)
            recent_days_to_check = 3

            print(f"Trying past {recent_days_to_check} consecutive days for {member.display_name} in {channel.name}...")
            for i in range(recent_days_to_check):
                target_date = now_utc - timedelta(days=i)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

                print(f"  Recent Attempt {i + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

                messages_by_member_on_day = []
                try:
                    async for message in channel.history(limit=100, after=start_of_day, before=end_of_day):
                        if message.author.id == member.id:
                            if message.content and message.content.strip():
                                messages_by_member_on_day.append(message)
                        
                        if messages_by_member_on_day:
                            chosen_message = random.choice(messages_by_member_on_day)
                            # For random messages, we always return the jump_url along with content
                            print(f"  SUCCESS (Recent): Found message on {start_of_day.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                            return chosen_message.content, chosen_message.jump_url

                except discord.Forbidden:
                    print(f"  Error: Bot lacks permissions to read history in {channel.name}. Aborting recent checks.")
                    return "I don't have permission to look through recent message history in that channel.", None
                except discord.HTTPException as e:
                    print(f"  Error: HTTP error fetching history for {channel.name} (recent day): {e}. Aborting recent checks.")
                    return "Something went wrong trying to fetch recent message history. Please try again later!", None
                except Exception as e:
                    print(f"  Error: An unexpected error occurred (recent day): {e}. Aborting recent checks.")
                    traceback.print_exc() 
                    return "An unexpected error occurred while looking for a recent message.", None
            
            return f"A true MFR", None
        
        return await search_general_chat_for_random_message(general_chat_channel, member_join_date_dt)


    async def get_roles(self, member: discord.Member):
        relevant_roles = []
        for role in member.roles:
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                relevant_roles.append(role.name)
        return relevant_roles

    async def get_roles_by_colors(self, member: discord.Member) -> tuple[list[str], list[str], list[str]]:
        main_genres_roles = []
        daw_roles = []
        instruments_roles = []

        for role in member.roles:
            if role.id == member.guild.id or role.color == discord.Color.default() or role.is_bot_managed() or role.is_integration():
                continue

            role_rgb = (role.color.r, role.color.g, role.color.b)

            if role_rgb == self.TARGET_MAIN_GENRES:
                main_genres_roles.append(role.name)
            elif role_rgb == self.TARGET_DAW:
                daw_roles.append(role.name)
            elif role_rgb == self.TARGET_INSTRUMENTS:
                instruments_roles.append(role.name)
            
        main_genres_roles.sort()
        daw_roles.sort()
        instruments_roles.sort()

        return main_genres_roles, daw_roles, instruments_roles

async def setup(bot):
    await bot.add_cog(MemberCards(bot))