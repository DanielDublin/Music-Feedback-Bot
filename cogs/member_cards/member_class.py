import discord
import requests # Unused, but kept for context of original code
import json # Unused
import os
import re
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import database.db as db
from data.constants import SERVER_ID, FINISHED_MUSIC, AOTW_CHANNEL, GENERAL_CHAT_CHANNEL_ID
from discord.ext import commands

load_dotenv()
token = os.environ.get('DISCORD_TEST_TOKEN')

class MemberCards(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # --- Define your target RGB colors based on provided HEX codes ---
        # These need to be accessible within the cog.
        self.TARGET_MAIN_GENRES = self._hex_to_rgb("#8d8c8c") # Likely your 'Main Genres'
        self.TARGET_DAW = self._hex_to_rgb("#6155a6") # Likely your 'DAW' roles
        self.TARGET_INSTRUMENTS = self._hex_to_rgb("#e3abff") # Likely your 'Instruments' roles
        # You can add more if you have other specific colors to filter by
        # -------------------------------------------------------------

    # Helper function to convert hex to RGB. Needs to be part of the class.
    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    async def get_username(self, member: discord.Member) -> str:
        """Returns the member's display name."""
        return member.display_name

    async def get_pfp(self, member: discord.Member) -> str:
        """
        Returns the URL of the member's display avatar.
        Ensures a string URL is always returned, falling back to a default if necessary.
        """
        if member.display_avatar.url:
            return str(member.display_avatar.url)
        else:
            return "https://discord.com/assets/f69a538202956c38266205842880b4c3.svg"

    async def get_join_date(self, member: discord.Member) -> datetime:
        """Returns the member's join date in UTC."""
        return member.joined_at

    async def get_rank(self, member: discord.Member) -> str:
        """Determines and returns the member's highest significant role name (rank)."""
        aotw = "Artist of the Week"

        for role in reversed(member.roles): # Reversed to get the highest role
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                if role.name == aotw:
                    return aotw
                else:
                    return role.name

        return "No specific rank"
            
    async def get_points(self, member: discord.Member):
        """
        Fetches member points and their rank if they are in the top 10.
        Returns a tuple: (is_top_feedback_member_id, raw_points).
        """
        raw_points = await db.fetch_points(str(member.id))

        try:
            points = int(raw_points)
        except (ValueError, TypeError):
            print(f"Warning: Could not convert raw points '{raw_points}' to int for member {member.display_name}. Defaulting to 0.")
            points = 0

        top_users = await db.top_10()
        is_top_feedback = False
        for index, user_data in enumerate(top_users):
            if user_data["user_id"] == str(member.id):
                is_top_feedback = True
                break # Found in top_10

        return is_top_feedback, points
            
    async def get_message_count(self, member: discord.Member) -> int:
        """
        Currently a placeholder. Direct Discord API message count is rate-limited and complex.
        Consider using a message logging system or bot-cached counts.
        """
        return 0 # Placeholder: Implement actual message counting if needed.

    async def get_last_finished_music(self, member: discord.Member) -> str:
        """
        Retrieves the latest music release/link by the member.
        Prioritizes AOTW messages if the member has that role.
        Returns a clean URL string, or a descriptive text if no link is found.
        """
        finished_music_channel = self.bot.get_channel(FINISHED_MUSIC)
        aotw_channel = self.bot.get_channel(AOTW_CHANNEL)

        rank = await self.get_rank(member)
        aotw_role_name = "Artist of the Week"

        # Check for AOTW channel and message first if member has AOTW role
        if rank == aotw_role_name and aotw_channel and isinstance(aotw_channel, discord.TextChannel):
            print(f"Checking AOTW channel for {member.display_name}...")
            async for message in aotw_channel.history(limit=1):
                # If there's any message in AOTW, consider it the AOTW release
                print(f"Found AOTW message: {message.jump_url}")
                return str(message.jump_url) # Return the raw URL for the button
            
            print("No AOTW message found in AOTW channel.")
            return "AOTW release coming soon!" # If AOTW role but no AOTW message

        # If not AOTW, or no AOTW message, default to finished music channel
        if finished_music_channel and isinstance(finished_music_channel, discord.TextChannel):
            print(f"Checking Finished Music channel for {member.display_name}...")
            last_music_by_member = None
            async for message in finished_music_channel.history(limit=100): # Increased limit for better chance
                if message.author.id == member.id:
                    last_music_by_member = message
                    break

            if last_music_by_member:
                # Regex to find any http(s):// or www. links
                url_detect_pattern = r"(https?://\S+|www\.\S+)"
                finished_music_content = last_music_by_member.content
                detected_urls = re.findall(url_detect_pattern, finished_music_content)

                if detected_urls:
                    # Discord often wraps URLs in <>, so remove them if present
                    clean_url = detected_urls[0].strip('<>')
                    print(f"Detected URL in message content: {clean_url}")
                    return clean_url
                elif last_music_by_member.attachments:
                    # Return the URL of the first attachment if no text URL is found
                    print(f"Detected attachment URL: {last_music_by_member.attachments[0].url}")
                    return str(last_music_by_member.attachments[0].url)
                else:
                    print(f"Message found but no discernible link or attachment: {last_music_by_member.jump_url}")
                    return "No link found in last release." # Message exists but has no discernible link
            else:
                print(f"No recent finished music message found for {member.display_name}.")
                return "No music finished yet." # No message found by member
        
        print("Finished Music channel not found or not a text channel.")
        return "Could not retrieve finished music info." # Channel not found/accessible

    async def generate_random_date_range(self, member_join_date: datetime) -> tuple[datetime, datetime]:
        """Generates a random date range (start and end of day) between join date and now."""
        now_utc = datetime.now(timezone.utc)
        time_since_join = now_utc - member_join_date

        if time_since_join.total_seconds() <= 0: # If joined very recently, use today
            start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_of_day, end_of_day

        random_seconds_offset = random.uniform(0, time_since_join.total_seconds())
        random_timedelta = timedelta(seconds=random_seconds_offset)
        random_date_chosen = member_join_date + random_timedelta

        start_of_day_utc = random_date_chosen.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = random_date_chosen.replace(hour=23, minute=59, second=59, microsecond=999999)

        return start_of_day_utc, end_of_day_utc

    async def get_random_message(self, member: discord.Member) -> tuple[str, str | None]:
        """
        Finds a random message by the member in the general chat.
        Tries random days first, then recent consecutive days.
        Returns a tuple of (message_content, message_jump_url).
        """
        general_chat = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)

        if not general_chat or not isinstance(general_chat, discord.TextChannel):
            print(f"Error: GENERAL_CHAT_CHANNEL (ID: {GENERAL_CHAT_CHANNEL_ID}) not found or not a text channel.")
            return "Couldn't find the general chat channel to look for messages!", None

        member_join_date_dt = await self.get_join_date(member)

        # Strategy 1: Try 10 random days
        random_day_attempts = 10
        print(f"Attempting {random_day_attempts} random days for {member.display_name} in {general_chat.name}...")
        for attempt in range(random_day_attempts):
            start_of_day, end_of_day = await self.generate_random_date_range(member_join_date_dt)
            
            print(f"  Random Attempt {attempt + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

            messages_by_member_on_day = []
            try:
                # Limit can be higher but be mindful of API calls
                async for message in general_chat.history(limit=200, after=start_of_day, before=end_of_day):
                    if message.author.id == member.id:
                        messages_by_member_on_day.append(message)
                
                if messages_by_member_on_day:
                    chosen_message = random.choice(messages_by_member_on_day)
                    print(f"  SUCCESS (Random): Found message on {start_of_day.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                    
                    # Return content and URL for the button
                    return chosen_message.content, chosen_message.jump_url

            except discord.Forbidden:
                print(f"  Error: Bot lacks permissions to read history in {general_chat.name}. Aborting random attempts.")
                return "I don't have permission to look through message history in that channel.", None
            except discord.HTTPException as e:
                print(f"  Error: HTTP error fetching history for {general_chat.name} (random day): {e}. Aborting random attempts.")
                return "Something went wrong trying to fetch message history. Please try again later!", None
            except Exception as e:
                print(f"  Error: An unexpected error occurred (random day): {e}. Aborting random attempts.")
                return "An unexpected error occurred while looking for a message.", None

        print(f"Finished {random_day_attempts} random attempts for {member.display_name}. No message found.")

        # --- Strategy 2: If random days fail, try the past 3 consecutive days ---
        now_utc = datetime.now(timezone.utc)
        recent_days_to_check = 3

        print(f"Trying past {recent_days_to_check} consecutive days for {member.display_name}...")
        for i in range(recent_days_to_check):
            target_date = now_utc - timedelta(days=i)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

            print(f"  Recent Attempt {i + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

            messages_by_member_on_day = []
            try:
                async for message in general_chat.history(limit=200, after=start_of_day, before=end_of_day):
                    if message.author.id == member.id:
                        messages_by_member_on_day.append(message)
                
                if messages_by_member_on_day:
                    chosen_message = random.choice(messages_by_member_on_day)
                    print(f"  SUCCESS (Recent): Found message on {start_of_day.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                    
                    return chosen_message.content, chosen_message.jump_url

            except discord.Forbidden:
                print(f"  Error: Bot lacks permissions to read history in {general_chat.name}. Aborting recent checks.")
                return "I don't have permission to look through recent message history in that channel.", None
            except discord.HTTPException as e:
                print(f"  Error: HTTP error fetching history for {general_chat.name} (recent day): {e}. Aborting recent checks.")
                return "Something went wrong trying to fetch recent message history. Please try again later!", None
            except Exception as e:
                print(f"  Error: An unexpected error occurred (recent day): {e}. Aborting recent checks.")
                return "An unexpected error occurred while looking for a recent message.", None

        # --- Final Fallback ---
        print(f"Failed to find any random messages for {member.display_name} after all strategies.")
        return f"Couldn't find any random messages by **{member.display_name}** in the general chat. Maybe they haven't posted much, or not in a while!", None

    async def get_roles(self, member: discord.Member):
        # This function currently returns ALL role names. 
        # You can keep it if you need all, or remove it if get_roles_by_colors replaces its purpose.
        return [role.name for role in member.roles]

    # --- NEW FUNCTION TO GET ROLES BY SPECIFIC COLORS ---
    async def get_roles_by_colors(self, member: discord.Member):
        main_genres_roles = []
        daw_roles = []
        instruments_roles = []

        for role in member.roles:
            # Skip @everyone role as it has color 0 (black/invisible) and is usually not relevant
            # Also skip roles that explicitly have no color set (discord.Color.default() is 0)
            if role.id == member.guild.id or role.color == discord.Color.default():
                continue

            # Convert discord.Color object to RGB tuple for comparison
            role_rgb = (role.color.r, role.color.g, role.color.b)

            if role_rgb == self.TARGET_MAIN_GENRES:
                main_genres_roles.append(role.name)
            elif role_rgb == self.TARGET_DAW:
                daw_roles.append(role.name)
            elif role_rgb == self.TARGET_INSTRUMENTS:
                instruments_roles.append(role.name)
            
            # Add more elif conditions here for other specific colors if needed

        # Optionally sort the lists alphabetically if the order is important for display
        main_genres_roles.sort()
        daw_roles.sort()
        instruments_roles.sort()

        # NOTE: No slicing here, we return the full lists for the card generator to handle display logic.
        return main_genres_roles, daw_roles, instruments_roles

async def setup(bot):
    await bot.add_cog(MemberCards(bot))