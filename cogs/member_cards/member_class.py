import discord
import requests # Unused, but kept for context of original code
import json # Unused
import os
import re
import random
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import database.db as db # Assuming you have this database module
from data.constants import SERVER_ID, FINISHED_MUSIC, AOTW_CHANNEL, GENERAL_CHAT_CHANNEL_ID
from discord.ext import commands

load_dotenv()
# It's generally safer to get tokens from environment variables, especially for production
# For testing, you might load a specific test token, as you've done.
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
            # A generic Discord default avatar or a custom placeholder
            return "https://discord.com/assets/f69a538202956c38266205842880b4c3.svg"

    async def get_join_date(self, member: discord.Member) -> datetime:
        """Returns the member's join date in UTC."""
        # member.joined_at is already a datetime object in UTC
        return member.joined_at

    async def get_rank(self, member: discord.Member) -> str:
        """Determines and returns the member's highest significant role name (rank)."""
        aotw = "Artist of the Week"

        # Iterate through roles in reverse order to find the highest role
        # that is not @everyone, bot-managed, or an integration.
        for role in reversed(member.roles): 
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                # Prioritize "Artist of the Week" if present
                if role.name == aotw:
                    return aotw
                else:
                    return role.name # Return the highest role found

        return "No specific rank" # Fallback if no relevant roles are found
            
    async def get_points(self, member: discord.Member):
        """
        Fetches member points and determines if they are in the top 10.
        Assumes db.fetch_points returns a string that can be converted to int.
        Assumes db.top_10 returns a list of dictionaries with 'user_id'.
        Returns a tuple: (is_top_feedback_member, raw_points_as_int).
        """
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
                    break # Found in top_10
        except Exception as e:
            print(f"Error fetching top 10 users from DB: {e}")
            # If there's an error, assume not top feedback
            is_top_feedback = False

        return is_top_feedback, points
            
    async def get_message_count(self, member: discord.Member) -> int:
        """
        Currently a placeholder. Direct Discord API message count is rate-limited and complex.
        For actual message counting, you would need to:
        1. Store message counts in your database as messages are sent.
        2. Use a dedicated logging bot or service.
        3. For historical counts, be aware of Discord's API limitations (max 100 messages per `history` call, rate limits).
        """
        # Placeholder: Returns 0 messages.
        # To implement actual message counting, you'd integrate with your database
        # where message counts are presumably stored.
        # Example: return await db.fetch_message_count(str(member.id)) 
        return 0 

    async def get_last_finished_music(self, member: discord.Member) -> str:
        """
        Retrieves the latest music release/link by the member.
        Prioritizes AOTW messages if the member has that role.
        Searches for URLs in message content or attachments.
        Returns a clean URL string, or a descriptive text if no link is found.
        """
        finished_music_channel = self.bot.get_channel(FINISHED_MUSIC)
        aotw_channel = self.bot.get_channel(AOTW_CHANNEL)

        rank = await self.get_rank(member)
        aotw_role_name = "Artist of the Week"

        # 1. Check for AOTW channel and message first if member has AOTW role
        if rank == aotw_role_name and aotw_channel and isinstance(aotw_channel, discord.TextChannel):
            print(f"Checking AOTW channel ({aotw_channel.name}) for {member.display_name}...")
            try:
                # Assuming AOTW channel will have one recent announcement.
                # Adjust limit if AOTW messages might be buried.
                async for message in aotw_channel.history(limit=5): 
                    if message.author.id == member.id: # Ensure it's *their* AOTW message
                        print(f"Found AOTW message: {message.jump_url}")
                        # Look for a link in the AOTW message content
                        url_detect_pattern = r"(https?://\S+|www\.\S+)"
                        detected_urls = re.findall(url_detect_pattern, message.content)
                        if detected_urls:
                            clean_url = detected_urls[0].strip('<>')
                            return clean_url
                        elif message.attachments:
                            return str(message.attachments[0].url)
                        else:
                            # If AOTW message has no link, still provide its jump URL as a fallback for the button
                            return str(message.jump_url)
                
                print(f"No AOTW message by {member.display_name} found in AOTW channel.")
                # If they have AOTW role but no specific AOTW message found by them, indicate.
                return "AOTW release coming soon!" 
            except discord.Forbidden:
                print(f"Bot lacks permissions to read AOTW channel history.")
                return "Cannot access AOTW channel to find release."
            except discord.HTTPException as e:
                print(f"HTTP error fetching AOTW history: {e}")
                return "Error fetching AOTW release."

        # 2. If not AOTW, or no AOTW message, default to finished music channel
        if finished_music_channel and isinstance(finished_music_channel, discord.TextChannel):
            print(f"Checking Finished Music channel ({finished_music_channel.name}) for {member.display_name}...")
            last_music_by_member = None
            try:
                # Increased limit to find more recent messages from the member
                async for message in finished_music_channel.history(limit=200): 
                    if message.author.id == member.id:
                        last_music_by_member = message
                        break # Found the most recent message by this member

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
                        # Return jump_url if no other link is found, so the button still works
                        return str(last_music_by_member.jump_url) 
                else:
                    print(f"No recent finished music message found for {member.display_name}.")
                    return "No music finished yet." # No message found by member
            except discord.Forbidden:
                print(f"Bot lacks permissions to read Finished Music channel history.")
                return "Cannot access Finished Music channel to find release."
            except discord.HTTPException as e:
                print(f"HTTP error fetching Finished Music history: {e}")
                return "Error fetching finished music release."
        
        print("Finished Music channel not found or not a text channel.")
        return "Could not retrieve finished music info." # Channel not found/accessible

    async def generate_random_date_range(self, member_join_date: datetime) -> tuple[datetime, datetime]:
        """Generates a random date range (start and end of day) between join date and now."""
        # Ensure member_join_date is timezone-aware (UTC) if it's not already
        if member_join_date.tzinfo is None:
            member_join_date = member_join_date.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        time_since_join = now_utc - member_join_date

        # Handle cases where join date is in the future or very recent (e.g., less than a day)
        if time_since_join.total_seconds() <= 0: 
            # If joined very recently or future, set range to current day
            start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_of_day, end_of_day

        # Generate a random timedelta within the period since the member joined
        random_seconds_offset = random.uniform(0, time_since_join.total_seconds())
        random_timedelta = timedelta(seconds=random_seconds_offset)
        
        # Calculate a random date between join_date and now
        random_date_chosen = member_join_date + random_timedelta

        # Get start and end of that randomly chosen day in UTC
        start_of_day_utc = random_date_chosen.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day_utc = random_date_chosen.replace(hour=23, minute=59, second=59, microsecond=999999)

        return start_of_day_utc, end_of_day_utc

    async def get_random_message(self, member: discord.Member) -> tuple[str, str | None]:
        """
        Finds a random message by the member in the general chat.
        Prioritizes messages with content.
        Tries N random days first, then recent consecutive days.
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
                # Fetch history for the specific day. Adjust limit if members post very frequently.
                async for message in general_chat.history(limit=200, after=start_of_day, before=end_of_day):
                    if message.author.id == member.id:
                        # Only consider messages with actual content (not just embeds/attachments)
                        if message.content and message.content.strip():
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
                traceback.print_exc() # Print full traceback for unexpected errors
                return "An unexpected error occurred while looking for a message.", None

        print(f"Finished {random_day_attempts} random attempts for {member.display_name}. No suitable message found.")

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
                # Fetch history for the specific day
                async for message in general_chat.history(limit=200, after=start_of_day, before=end_of_day):
                    if message.author.id == member.id:
                        if message.content and message.content.strip():
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
                traceback.print_exc() # Print full traceback
                return "An unexpected error occurred while looking for a recent message.", None

        # --- Final Fallback ---
        print(f"Failed to find any random messages for {member.display_name} after all strategies.")
        return f"Couldn't find any random messages by **{member.display_name}** in the general chat. Maybe they haven't posted much, or not in a while!", None

    async def get_roles(self, member: discord.Member):
        """
        Returns a list of all role names (excluding @everyone, bot-managed, integrations).
        Consider if this function is still needed if get_roles_by_colors is the primary method.
        """
        relevant_roles = []
        for role in member.roles:
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                relevant_roles.append(role.name)
        return relevant_roles

    async def get_roles_by_colors(self, member: discord.Member) -> tuple[list[str], list[str], list[str]]:
        """
        Categorizes and returns role names based on predefined RGB color targets.
        Skips @everyone and roles with default (invisible) color.
        """
        main_genres_roles = []
        daw_roles = []
        instruments_roles = []

        for role in member.roles:
            # Skip @everyone role (has color 0) and roles with explicit default color.
            # Also skip roles that are bot-managed or integrations if they might have a color
            if role.id == member.guild.id or role.color == discord.Color.default() or role.is_bot_managed() or role.is_integration():
                continue

            # Convert discord.Color object to RGB tuple for comparison
            role_rgb = (role.color.r, role.color.g, role.color.b)

            if role_rgb == self.TARGET_MAIN_GENRES:
                main_genres_roles.append(role.name)
            elif role_rgb == self.TARGET_DAW:
                daw_roles.append(role.name)
            elif role_rgb == self.TARGET_INSTRUMENTS:
                instruments_roles.append(role.name)
            
            # Add more elif conditions here for other specific colors if you have them

        # Optionally sort the lists alphabetically for consistent display order
        main_genres_roles.sort()
        daw_roles.sort()
        instruments_roles.sort()

        # Return the full lists; the card generator handles how many to display
        return main_genres_roles, daw_roles, instruments_roles

async def setup(bot):
    await bot.add_cog(MemberCards(bot))