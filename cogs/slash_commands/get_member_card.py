import discord
import logging
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
import time
from datetime import datetime
import aiohttp
import emoji
from typing import Optional
from cogs.member_cards.member_data import MemberData
from cogs.member_cards.member_card_renderer import render_member_card, FONT_PATH, BACKGROUND_IMAGES_DIR

logger = logging.getLogger(__name__)

LOG_CHANNEL_ID = 993597439594479747


def time_it(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        if func.__name__ in ["render_animated_frames", "generate_card", "view_mf_card"]:
            kwargs.get("log_collector", []).append(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper


class GetMemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.member_data = MemberData(bot)

        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(f"Font file not found: {FONT_PATH}")

        try:
            _ = ImageFont.truetype(FONT_PATH, 10)
        except IOError:
            raise IOError(f"Could not load font from: {FONT_PATH}. Check file permissions or corruption.")

        if not os.path.exists(BACKGROUND_IMAGES_DIR):
            logger.warning("Background images directory not found at: %s. Card backgrounds might default to gradient.", BACKGROUND_IMAGES_DIR)

    async def send_log_to_discord(self, logs, guild):
        """Send collected logs to the designated Discord channel."""
        if not logs:
            return
        try:
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if not log_channel:
                logger.warning("Log channel with ID %s not found.", LOG_CHANNEL_ID)
                return
            log_message = "\n".join(logs)
            await log_channel.send(f"```log\n{log_message}\n```")
        except discord.errors.HTTPException as e:
            if e.code == 429:
                retry_after = e.retry_after
                logger.warning("Rate limited. Retrying after %s seconds.", retry_after)
                await discord.utils.sleep_until(time.time() + retry_after)
                await log_channel.send(f"```log\n{log_message}\n```")
            else:
                logger.error("Error sending log to Discord", exc_info=True)
        except Exception:
            logger.error("Unexpected error sending log to Discord", exc_info=True)

    mf_card_group = app_commands.Group(name="mf", description="View your MF Card related commands.")

    @time_it
    @app_commands.checks.has_any_role(*["Admins", "Moderators", "Chat Moderators"])
    @mf_card_group.command(name="card", description="View a member's MF Card.")
    @app_commands.describe(member="The member whose MF Card you want to view (defaults to you).")
    async def view_mf_card(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        log_collector = []
        if member is None:
            member = interaction.user

        discord_username = member.display_name
        pfp_url = await self.member_data.get_pfp(member)
        join_date = await self.member_data.get_join_date(member)

        if isinstance(join_date, str):
            try:
                join_date = datetime.strptime(join_date, "%Y-%m-%d")
            except ValueError:
                join_date = datetime.now()
                log_collector.append(f"Invalid join date format for {discord_username}. Using current date.")

        rank_str = await self.member_data.get_rank(member)
        is_top_feedback, numeric_points = False, 0
        try:
            is_top_feedback, numeric_points = await self.member_data.get_points(member)
        except Exception as e:
            logger.error("Error calling get_points for %s", discord_username, exc_info=True)
            log_collector.append(f"Error calling get_points for {discord_username}: {str(e)}")

        all_main_genres_roles, all_daw_roles, all_instruments_roles = await self.member_data.get_roles_by_colors(member)
        message_count = await self.member_data.get_message_count(member)

        random_msg_content = ""
        random_msg_url = None
        try:
            retrieved_msg_data = await self.member_data.get_random_message(member)
            if retrieved_msg_data and len(retrieved_msg_data) == 2:
                random_msg_content, random_msg_url = retrieved_msg_data
            else:
                random_msg_content = "A true MFR"
                random_msg_url = None
        except Exception as e:
            logger.error("Error fetching random message for %s", discord_username, exc_info=True)
            log_collector.append(f"Error fetching random message for {discord_username}: {str(e)}")
            random_msg_content = "An unexpected error occurred while looking for a message."
            random_msg_url = None

        last_music = await self.member_data.get_last_finished_music(member)
        server_name = interaction.guild.name if interaction.guild else "Direct Message"
        release_link = last_music if last_music and (last_music.startswith("http://") or last_music.startswith("https://")) else None

        img_width, img_height = 600, 300

        async with aiohttp.ClientSession() as session:
            async with session.get(pfp_url) as resp:
                if resp.status != 200:
                    log_collector.append(f"Failed to fetch PFP for {discord_username}. Status: {resp.status}")
                    pfp = Image.new("RGBA", (120, 120), (100, 100, 100, 255))
                else:
                    pfp_data = io.BytesIO(await resp.read())
                    pfp = Image.open(pfp_data).convert("RGBA").resize((120, 120), Image.Resampling.LANCZOS)

        mask = Image.new("L", pfp.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, *pfp.size), fill=255)
        pfp.putalpha(mask)

        animated = True
        card_buffer, file_ext, log_collector = await render_member_card(
            pfp, discord_username, server_name, rank_str, numeric_points, message_count, join_date,
            (img_width, img_height), animated=animated, random_msg=random_msg_content,
            is_top_feedback=is_top_feedback,
            relevant_roles=[role.name for role in member.roles],
            all_genres_roles=all_main_genres_roles,
            all_daws_roles=all_daw_roles,
            all_instruments_roles=all_instruments_roles,
            log_collector=log_collector
        )

        filename = f"{discord_username}_mf_card.{file_ext}"
        file = discord.File(card_buffer, filename=filename)

        view = discord.ui.View()
        if release_link:
            view.add_item(discord.ui.Button(label=f"{discord_username}'s Latest Release", style=discord.ButtonStyle.link, url=release_link))
        if random_msg_url and random_msg_content not in ["A true MFR"]:
            view.add_item(discord.ui.Button(label=emoji.emojize(":rocket:"), style=discord.ButtonStyle.link, url=random_msg_url))

        log_collector.append(f"Member card sent to general chat for {discord_username}")
        await self.send_log_to_discord(log_collector, interaction.guild)
        await interaction.followup.send(file=file, view=view)


async def setup(bot):
    await bot.add_cog(GetMemberCard(bot))
