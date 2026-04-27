import discord
import re
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import Union
from data.constants import FINISHED_MUSIC, AOTW_CHANNEL, GENERAL_CHAT_CHANNEL_ID, INTRO_MUSIC
from data.config import AOTW_ROLE_NAME, FANS_ROLE_NAME, ROLES_TO_IGNORE

logger = logging.getLogger(__name__)


class MemberData:
    """Fetches and holds Discord data for a guild member. Not a cog."""

    TARGET_MAIN_GENRES = (0x8d, 0x8c, 0x8c)
    TARGET_DAW = (0x61, 0x55, 0xa6)
    TARGET_INSTRUMENTS = (0xe3, 0xab, 0xff)

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
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
        for role in reversed(member.roles):
            if role.name in ROLES_TO_IGNORE:
                continue
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                if role.name == AOTW_ROLE_NAME:
                    return AOTW_ROLE_NAME
                elif role.name == FANS_ROLE_NAME:
                    return FANS_ROLE_NAME
                else:
                    return role.name
        return "No specific rank"

    async def get_points(self, member: discord.Member):
        raw_points = await self.bot.db.fetch_points(str(member.id))

        try:
            points = int(raw_points)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert raw points '{raw_points}' to int for member {member.display_name}. Defaulting to 0.")
            points = 0

        is_top_feedback = False
        try:
            top_users = await self.bot.db.top_10()
            for user_data in top_users:
                if user_data["user_id"] == str(member.id):
                    is_top_feedback = True
                    break
        except Exception:
            logger.error("Error fetching top 10 users from DB", exc_info=True)
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

        def extract_url_from_message(message: discord.Message) -> Union[str, None]:
            if message.attachments:
                return str(message.jump_url)
            url_detect_pattern = r"(https?://\S+|www\.\S+)"
            detected_urls = re.findall(url_detect_pattern, message.content)
            if detected_urls:
                return detected_urls[0].strip('<>')
            return None

        if rank == AOTW_ROLE_NAME and aotw_channel and isinstance(aotw_channel, discord.TextChannel):
            logger.debug(f"Checking AOTW channel ({aotw_channel.name}) for {member.display_name}...")
            try:
                async for message in aotw_channel.history(limit=5):
                    url = extract_url_from_message(message)
                    if url:
                        logger.debug(f"Found AOTW message with URL: {url}")
                        return url
            except discord.Forbidden:
                logger.warning("Bot lacks permissions to read AOTW channel history.")
                return "Cannot access AOTW channel to find release."
            except discord.HTTPException:
                logger.error("HTTP error fetching AOTW history", exc_info=True)
                return "Error fetching AOTW release."

        elif rank == FANS_ROLE_NAME:
            if intro_music_channel and isinstance(intro_music_channel, discord.TextChannel):
                logger.debug(f"Checking Intro Music channel ({intro_music_channel.name}) for {member.display_name} (Fans)...")
                try:
                    async for message in intro_music_channel.history(limit=100):
                        if message.author.id == member.id:
                            url = extract_url_from_message(message)
                            if url:
                                logger.debug(f"Found last intro music link for {member.display_name}: {url}")
                                return url
                    logger.debug(f"No recent intro music message with a link/attachment found for {member.display_name}.")
                    return "No intro music link found."
                except discord.Forbidden:
                    logger.warning("Bot lacks permissions to read Intro Music channel history.")
                    return "Cannot access Intro Music channel to find release."
                except discord.HTTPException:
                    logger.error("HTTP error fetching Intro Music history", exc_info=True)
                    return "Error fetching intro music release."
            else:
                logger.warning("Intro Music channel not found or not a text channel.")
                return "Could not retrieve intro music info."

        else:
            if finished_music_channel and isinstance(finished_music_channel, discord.TextChannel):
                logger.debug(f"Checking Finished Music channel ({finished_music_channel.name}) for {member.display_name} (Default)...")
                try:
                    async for message in finished_music_channel.history(limit=100):
                        if message.author.id == member.id:
                            url = extract_url_from_message(message)
                            if url:
                                logger.debug(f"Found last finished music link for {member.display_name}: {url}")
                                return url
                            elif message.attachments:
                                return str(message.jump_url)
                            else:
                                continue
                    logger.debug(f"No recent finished music message found for {member.display_name}.")
                    return "No music finished yet."
                except discord.Forbidden:
                    logger.warning("Bot lacks permissions to read Finished Music channel history.")
                    return "Cannot access Finished Music channel to find release."
                except discord.HTTPException:
                    logger.error("HTTP error fetching Finished Music history", exc_info=True)
                    return "Error fetching finished music release."
            else:
                logger.warning("Finished Music channel not found or not a text channel.")
                return "Could not retrieve finished music info."

    async def generate_random_date_range(self, member_join_date: datetime) -> tuple:
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

    async def get_random_message(self, member: discord.Member) -> tuple:
        """
        Retrieves a random message by the member from the general chat channel.
        Returns a tuple of (message_content, message_jump_url).
        """
        member_join_date_dt = await self.get_join_date(member)
        general_chat_channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)

        if not general_chat_channel or not isinstance(general_chat_channel, discord.TextChannel):
            logger.error(f"GENERAL_CHAT_CHANNEL (ID: {GENERAL_CHAT_CHANNEL_ID}) not found or not a text channel.")
            return "Couldn't find the general chat channel to look for messages!", None

        async def search_general_chat_for_random_message(channel: discord.TextChannel, join_date: datetime):
            random_day_attempts = 10
            logger.debug(f"Attempting {random_day_attempts} random days for {member.display_name} in {channel.name}...")
            for attempt in range(random_day_attempts):
                start_of_day, end_of_day = await self.generate_random_date_range(join_date)

                logger.debug(f"  Random Attempt {attempt + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

                messages_by_member_on_day = []
                try:
                    async for message in channel.history(limit=100, after=start_of_day, before=end_of_day):
                        if message.author.id == member.id:
                            if message.content and message.content.strip():
                                messages_by_member_on_day.append(message)

                    if messages_by_member_on_day:
                        chosen_message = random.choice(messages_by_member_on_day)
                        logger.debug(f"  SUCCESS (Random): Found message on {start_of_day.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                        return chosen_message.content, chosen_message.jump_url

                except discord.Forbidden:
                    logger.warning(f"Bot lacks permissions to read history in {channel.name}. Aborting random attempts.")
                    return "I don't have permission to look through message history in that channel.", None
                except discord.HTTPException:
                    logger.error(f"HTTP error fetching history for {channel.name} (random day)", exc_info=True)
                    return "Something went wrong trying to fetch message history. Please try again later!", None
                except Exception:
                    logger.error("Unexpected error during random day search", exc_info=True)
                    return "An unexpected error occurred while looking for a message.", None

            logger.debug(f"Finished {random_day_attempts} random attempts for {member.display_name}. No suitable message found.")

            now_utc = datetime.now(timezone.utc)
            recent_days_to_check = 3

            logger.debug(f"Trying past {recent_days_to_check} consecutive days for {member.display_name} in {channel.name}...")
            all_recent_candidates = []
            for i in range(recent_days_to_check):
                target_date = now_utc - timedelta(days=i)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

                logger.debug(f"  Recent Attempt {i + 1}: Searching on {start_of_day.strftime('%Y-%m-%d')}")

                try:
                    async for message in channel.history(limit=100, after=start_of_day, before=end_of_day):
                        if message.author.id == member.id:
                            if message.content and message.content.strip():
                                all_recent_candidates.append(message)

                except discord.Forbidden:
                    logger.warning(f"Bot lacks permissions to read history in {channel.name}. Aborting recent checks.")
                    return "I don't have permission to look through recent message history in that channel.", None
                except discord.HTTPException:
                    logger.error(f"HTTP error fetching history for {channel.name} (recent day)", exc_info=True)
                    return "Something went wrong trying to fetch recent message history. Please try again later!", None
                except Exception:
                    logger.error("Unexpected error during recent day search", exc_info=True)
                    return "An unexpected error occurred while looking for a recent message.", None

            if all_recent_candidates:
                chosen_message = random.choice(all_recent_candidates)
                logger.debug(f"  SUCCESS (Recent): Found message from {chosen_message.created_at.strftime('%Y-%m-%d')}: {chosen_message.jump_url}")
                return chosen_message.content, chosen_message.jump_url

            return "A true MFR", None

        return await search_general_chat_for_random_message(general_chat_channel, member_join_date_dt)

    async def get_roles(self, member: discord.Member):
        relevant_roles = []
        for role in member.roles:
            if role.name != "@everyone" and not role.is_bot_managed() and not role.is_integration():
                relevant_roles.append(role.name)
        return relevant_roles

    async def get_roles_by_colors(self, member: discord.Member) -> tuple:
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
