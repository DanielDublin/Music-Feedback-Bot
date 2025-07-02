import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter, ImageOps
import io
import os
import math
from datetime import datetime
import aiohttp
from pilmoji import Pilmoji
import emoji
from data.constants import COLLAB_ROLE
from typing import Optional
import time

# Define the Discord channel ID for logging (replace with your actual channel ID)
LOG_CHANNEL_ID = 993597439594479747  # Placeholder; set to your logging channel ID

def time_it(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        # Only log major functions
        if func.__name__ in ["render_animated_frames", "generate_card", "view_mf_card"]:
            kwargs.get("log_collector", []).append(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

class GetMemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        current_script_dir = os.path.dirname(__file__)
        base_media_dir = os.path.abspath(os.path.join(current_script_dir, "../../media/Bebas_Neue/"))
        self.font_path = os.path.join(base_media_dir, "BebasNeue-Regular.ttf")
        self.background_images_dir = os.path.join(base_media_dir, "images/")
        self._banner_image_path = os.path.join(self.background_images_dir, "banner.png")

        self.background_map = {
            "Server Booster": "booster.png",
            "Owner": "admins.png",
            "Admins": "admins.png",
            "Moderators": "moderators.png",
            "Chat Moderators": "moderators.png",
            "Bot Boinker": "moderators.png",
            "The Real MFrs": "gilded.png",
            "MF Gilded": "gilded.png",
            "Headliners": "headliners.png",
            "Supporting Acts": "supporting_acts.png",
            "Ultimate Fans": "ultimate_fans.png",
            "Stagehands": "stagehands.png",
            "Groupies": "groupies.png",
            "Fans": "fans.png",
            "Artist of the Week": "artist_of_the_week.png",
            "New Member": "new_member.png",
            "Member": "member.png"
        }

        self.rank_blink_colors = {
            "Server Booster": "#f47fff",
            "Owner": "#ffd1dc",
            "Admins": "#ffd1dc",
            "Moderators": "#0F806A",
            "Chat Moderators": "#bce6d4",
            "Bot Boinker": "#02cffc",
            "Artist of the Week": "#00ffd1",
            "The Real MFrs": "#3e35ff",
            "MF Gilded": "#8c32e6",
            "Headliners": "#b399d4",
            "Supporting Acts": "#fadcaa",
            "Ultimate Fans": "#ca7290",
            "Stagehands": "#b2deec",
            "Groupies": "#9ecca4",
            "Fans": "#c7150a",
            "New Member": "#808080",
            "Member": "#808080",
            "No specific rank": "#808080"
        }

        if not os.path.exists(self.font_path):
            raise FileNotFoundError(f"Font file not found: {self.font_path}")

        try:
            _ = ImageFont.truetype(self.font_path, 10)
        except IOError:
            raise IOError(f"Could not load font from: {self.font_path}. Check file permissions or corruption.")

        if not os.path.exists(self.background_images_dir):
            print(f"WARNING: Background images directory not found at: {self.background_images_dir}. Card backgrounds might default to gradient.")

    async def send_log_to_discord(self, logs, guild):
        """Send collected logs to the designated Discord channel."""
        if not logs:
            return
        try:
            log_channel = guild.get_channel(LOG_CHANNEL_ID)
            if not log_channel:
                print(f"Log channel with ID {LOG_CHANNEL_ID} not found.")
                return
            log_message = "\n".join(logs)
            await log_channel.send(f"```log\n{log_message}\n```")
        except discord.errors.HTTPException as e:
            if e.code == 429:  # Rate limit
                retry_after = e.retry_after
                print(f"Rate limited. Retrying after {retry_after} seconds.")
                await discord.utils.sleep_until(time.time() + retry_after)
                await log_channel.send(f"```log\n{log_message}\n```")
            else:
                print(f"Error sending log to Discord: {e}")
        except Exception as e:
            print(f"Unexpected error sending log to Discord: {e}")

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    mf_card_group = app_commands.Group(name="mf", description="View your MF Card related commands.")

    def _get_star_points(self, center_x, center_y, num_points, outer_radius, inner_radius, rotation_degrees):
        points = []
        for i in range(num_points):
            angle_outer = math.radians(rotation_degrees + i * (360 / num_points))
            x_outer = center_x + outer_radius * math.sin(angle_outer)
            y_outer = center_y - outer_radius * math.cos(angle_outer)
            points.append((x_outer, y_outer))
            angle_inner = math.radians(rotation_degrees + (i + 0.5) * (360 / num_points))
            x_inner = center_x + inner_radius * math.sin(angle_inner)
            y_inner = center_y - inner_radius * math.cos(angle_inner)
            points.append((x_inner, y_inner))
        return points

    def _draw_top_mfr_badge(self, draw_obj, y_pos, x_pos, font_top_mfr, icon_size, text_padding, text_color):
        star_color = (255, 215, 0)
        top_mfr_text = "TOP MFR"
        star_center_x = x_pos + icon_size // 2
        star_center_y = y_pos + icon_size // 2
        star_points = self._get_star_points(star_center_x, star_center_y, 5, icon_size/2, icon_size/4, 0)
        draw_obj.polygon(star_points, fill=star_color)
        text_x = x_pos + icon_size + text_padding
        text_y_centered = y_pos + (icon_size - font_top_mfr.size) // 2
        draw_obj.text((text_x, text_y_centered), top_mfr_text, fill=text_color, font=font_top_mfr)
        top_mfr_text_bbox = draw_obj.textbbox((text_x, text_y_centered), top_mfr_text, font=font_top_mfr)
        return top_mfr_text_bbox[2], text_y_centered

    def get_text_bbox(self, text, font, max_width=None):
        font_size = font.size
        est_width = max(len(text) * font_size, 100)
        est_height = font_size * 2
        temp_image = Image.new("RGBA", (est_width, est_height), (0, 0, 0, 0))
        
        with Pilmoji(temp_image) as pilmoji_draw:
            pilmoji_draw.text((0, 0), text, fill=(255, 255, 255), font=font)
        
        bbox = temp_image.getbbox()
        if bbox:
            x0, y0, x1, y1 = bbox
            return (x0, y0 - font_size // 2, x1, y1 + font_size // 2)
        else:
            return (0, 0, 0, font_size)

    def generate_card(self, pfp_image_pil, discord_username, server_name, rank_str, numeric_points, message_count, join_date, card_size, font_path, animated=True, random_msg="", is_top_feedback=False, **kwargs):
        start_time_total = time.time()
        log_collector = []  # Collect major logs
        frames = []
        num_frames = 75 # 100
        frame_duration = 75

        def time_section(section_name):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    start = time.time()
                    result = func(*args, **kwargs)
                    end = time.time()
                    # Only log major sections
                    if section_name in ["Render Animated Frames", "Prepare Static Card", "Process Roles", "Process Random Message", "Setup Background", "Load Banner"]:
                        log_collector.append(f"{section_name} took {end - start:.4f} seconds")
                    return result
                return wrapper
            return decorator

        @time_section("Initialize Fonts")
        def initialize_fonts():
            font_date_label = ImageFont.truetype(font_path, 20)
            font_date_value = ImageFont.truetype(font_path, 25)
            font_rank_blinking = ImageFont.truetype(font_path, 50)
            font_top_mfr = ImageFont.truetype(font_path, 25)
            font_tag = ImageFont.truetype(font_path, 12)
            font_collab = ImageFont.truetype(font_path, 15)
            return font_date_label, font_date_value, font_rank_blinking, font_top_mfr, font_tag, font_collab

        font_date_label, font_date_value, font_rank_blinking, font_top_mfr, font_tag, font_collab = initialize_fonts()

        top_mfr_icon_size = 30
        top_mfr_text_padding = 8
        tag_text_color = (255, 255, 255)
        collab_circle_diameter = 45
        collab_text_color = (0, 0, 0)
        collab_circle_y_offset = 25
        collab_text_bg_color = (213, 213, 79)
        host_text_bg_color = (255, 255, 255)
        booster_text_bg_color = (244, 127, 255)
        badge_vertical_gap = 5
        tag_horizontal_padding = 6
        tag_vertical_padding = 4
        dot_diameter = 7
        dot_right_margin = 4
        tag_spacing_x = 4
        tag_line_height = font_tag.size + (2 * tag_vertical_padding)

        card_width, card_height = card_size

        relevant_roles = kwargs.get("relevant_roles", [])
        has_collab_role = COLLAB_ROLE in relevant_roles
        has_host_role = "Event Host" in relevant_roles
        has_booster_role = "Server Booster" in relevant_roles

        @time_section("Load Banner")
        def load_banner():
            banner = Image.open(self._banner_image_path).convert("RGBA")
            banner = banner.crop((0, 5, 800, 35))
            return banner

        banner = load_banner()
        banner_width, banner_height = banner.size
        amplitude = 50
        center_x = (card_width // 2) - (banner_width // 2)

        inverted_text_roles = ["Moderators", "Chat Moderators", "Bot Boinker"]

        @time_section("Setup Background")
        def setup_background():
            if rank_str == "Artist of the Week" and animated:
                base_card_content = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
                flash_colors = [
                    (255, 255, 255),
                    self._hex_to_rgb("d585eb"),
                    self._hex_to_rgb("3bc4ed"),
                    (255, 255, 255)
                ]
            else:
                background_image_path = None
                if rank_str in self.background_map:
                    background_filename = self.background_map[rank_str]
                    background_image_path = os.path.join(self.background_images_dir, background_filename)
                base_card_content = None
                if background_image_path and os.path.exists(background_image_path):
                    try:
                        background_image = Image.open(background_image_path).convert("RGBA")
                        base_card_content = background_image.resize((card_width, card_height), Image.Resampling.LANCZOS)
                    except Exception as e:
                        log_collector.append(f"Error loading background image '{background_image_path}': {e}. Falling back to gradient.")
                        base_card_content = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
                        draw_background = ImageDraw.Draw(base_card_content)
                        center_color = (179, 153, 212)
                        side_color = (88, 70, 191)
                        for x in range(card_width):
                            distance_from_center_norm = abs((x / (card_width - 1)) * 2 - 1)
                            blend_factor = 1 - distance_from_center_norm
                            r = int(side_color[0] + (center_color[0] - side_color[0]) * blend_factor)
                            g = int(side_color[1] + (center_color[1] - side_color[1]) * blend_factor)
                            b = int(side_color[2] + (center_color[2] - side_color[2]) * blend_factor)
                            draw_background.line((x, 0, x, card_height), fill=(r, g, b, 255))
                else:
                    base_card_content = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
                    draw_background = ImageDraw.Draw(base_card_content)
                    center_color = (179, 153, 212)
                    side_color = (88, 70, 191)
                    for x in range(card_width):
                        distance_from_center_norm = abs((x / (card_width - 1)) * 2 - 1)
                        blend_factor = 1 - distance_from_center_norm
                        r = int(side_color[0] + (center_color[0] - side_color[0]) * blend_factor)
                        g = int(side_color[1] + (center_color[1] - side_color[1]) * blend_factor)
                        b = int(side_color[2] + (center_color[2] - side_color[2]) * blend_factor)
                        draw_background.line((x, 0, x, card_height), fill=(r, g, b, 255))
            return base_card_content, flash_colors if rank_str == "Artist of the Week" and animated else None

        base_card_content, flash_colors = setup_background()

        pfp_x, pfp_y = 50, 65
        pfp_diameter = 120
        border_thickness = 8
        border_color = (0, 0, 0, 255)

        border_bbox_x1 = pfp_x - border_thickness
        border_bbox_y1 = pfp_y - border_thickness
        border_bbox_x2 = pfp_x + pfp_diameter + border_thickness
        border_bbox_y2 = pfp_y + pfp_diameter + border_thickness

        current_left_y = pfp_y + pfp_diameter + 10
        username_y = current_left_y
        current_left_y += 25 + 5
        member_since_label_y = current_left_y
        current_left_y += font_date_label.size
        join_date_value_y = current_left_y
        current_left_y += font_date_value.size + 20

        right_column_x_start = pfp_x + pfp_diameter + 30
        rank_y = pfp_y + 10

        current_y_for_points_block = rank_y + font_rank_blinking.size + 5
        bottom_of_points_block_y = current_y_for_points_block + max(top_mfr_icon_size, font_top_mfr.size) if is_top_feedback else current_y_for_points_block + font_top_mfr.size

        roles_y = bottom_of_points_block_y + 10
        message_box_width_for_random_msg = card_width - right_column_x_start - 20
        tag_line_available_width = card_width - right_column_x_start - 20
        tag_bg_color = (40, 40, 40, 200)

        @time_section("Process Roles")
        def process_roles():
            try:
                all_genres_roles = kwargs.get("all_genres_roles", [])
                all_daws_roles = kwargs.get("all_daws_roles", [])
                all_instruments_roles = kwargs.get("all_instruments_roles", [])

                displayed_roles_raw = []
                for role_name in all_genres_roles[:3]:
                    displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#8d8c8c")})
                for role_name in all_daws_roles[:3]:
                    displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#6155a6")})
                for role_name in all_instruments_roles[:3]:
                    displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#e3abff")})

                seen_displayed_roles = set()
                displayed_roles_final = []
                for role_data in displayed_roles_raw:
                    if role_data['name'] not in seen_displayed_roles:
                        displayed_roles_final.append(role_data)
                        seen_displayed_roles.add(role_data['name'])

                final_displayed_roles = []
                first_line_roles = []
                second_line_roles = []
                current_first_line_width = 0
                current_second_line_width = 0

                for tag_data in displayed_roles_final:
                    tag_text = tag_data['name']
                    try:
                        text_bbox = self.get_text_bbox(tag_text, font_tag)
                        text_width = text_bbox[2] - text_bbox[0]
                    except Exception as e:
                        log_collector.append(f"Error calculating text bbox for role '{tag_text}': {e}")
                        continue
                    tag_full_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding) + tag_spacing_x

                    remaining_first_line_space = tag_line_available_width - current_first_line_width
                    remaining_second_line_space = tag_line_available_width - current_second_line_width

                    if len(first_line_roles) < 5 and tag_full_width <= remaining_first_line_space:
                        first_line_roles.append(tag_data)
                        current_first_line_width += tag_full_width
                    elif len(second_line_roles) < 5 and tag_full_width <= remaining_second_line_space:
                        second_line_roles.append(tag_data)
                        current_second_line_width += tag_full_width

                len_first_line_roles = len(first_line_roles)
                final_displayed_roles = first_line_roles + second_line_roles
                return final_displayed_roles, len_first_line_roles
            except Exception as e:
                log_collector.append(f"Error in process_roles: {e}")
                return [], 0

        final_displayed_roles, len_first_line_roles = process_roles()
        roles_block_height = 2 * tag_line_height if final_displayed_roles else 0

        random_msg_y = roles_y + roles_block_height + 10

        @time_section("Process Random Message")
        def process_random_message():
            if not random_msg:
                return None
            random_msg_initial_font_size = 20
            random_msg_min_font_size = font_tag.size
            bottom_of_member_since_date_block_y = join_date_value_y + font_date_value.size
            height_if_align_to_date_bottom = bottom_of_member_since_date_block_y - random_msg_y
            bottom_buffer_for_message_box = 20
            max_height_to_card_bottom = card_height - random_msg_y - bottom_buffer_for_message_box
            max_available_height_for_msg_box_area = min(height_if_align_to_date_bottom, max_height_to_card_bottom) if height_if_align_to_date_bottom > 0 else max(max_height_to_card_bottom, 0)
            min_practical_height = (2 * 10) + random_msg_min_font_size
            max_available_height_for_msg_box_area = max(max_available_height_for_msg_box_area, min_practical_height)

            final_font_random_msg = ImageFont.truetype(font_path, random_msg_min_font_size)
            final_wrapped_message = []
            current_font_size = random_msg_initial_font_size
            font_found = False

            while current_font_size >= random_msg_min_font_size:
                temp_font = ImageFont.truetype(font_path, current_font_size)
                message_box_padding = 10
                effective_text_width = message_box_width_for_random_msg - (2 * message_box_padding)
                if effective_text_width <= 0:
                    effective_text_width = 1
                wrapped_message_temp = self.wrap_text(random_msg, temp_font, effective_text_width)
                temp_message_content_height = len(wrapped_message_temp) * temp_font.size
                temp_message_box_total_height = temp_message_content_height + (2 * message_box_padding)
                if temp_message_box_total_height <= max_available_height_for_msg_box_area:
                    final_wrapped_message = wrapped_message_temp
                    final_font_random_msg = temp_font
                    font_found = True
                    break
                current_font_size -= 1

            if not font_found:
                final_font_random_msg = ImageFont.truetype(font_path, random_msg_min_font_size)
                message_box_padding = 10
                effective_text_width = message_box_width_for_random_msg - (2 * message_box_padding)
                if effective_text_width <= 0:
                    effective_text_width = 1
                wrapped_message_temp = self.wrap_text(random_msg, final_font_random_msg, effective_text_width)
                max_content_height_at_min_font = max_available_height_for_msg_box_area - (2 * message_box_padding)
                max_lines_for_min_font = math.floor(max_content_height_at_min_font / final_font_random_msg.size)
                if max_lines_for_min_font <= 0:
                    final_wrapped_message = ["..."]
                elif len(wrapped_message_temp) > max_lines_for_min_font:
                    final_wrapped_message = wrapped_message_temp[:max_lines_for_min_font]
                    last_line_index = max_lines_for_min_font - 1
                    if last_line_index >= 0:
                        original_last_line = final_wrapped_message[last_line_index]
                        truncated_last_line = ""
                        ellipsis_bbox = self.get_text_bbox("...", final_font_random_msg)
                        ellipsis_width = ellipsis_bbox[2] - ellipsis_bbox[0]
                        max_text_width_for_last_line = effective_text_width - ellipsis_width
                        for char in original_last_line:
                            test_line = truncated_last_line + char
                            test_bbox = self.get_text_bbox(test_line, final_font_random_msg)
                            test_width = test_bbox[2] - test_bbox[0]
                            if test_width <= max_text_width_for_last_line:
                                truncated_last_line += char
                            else:
                                break
                        final_wrapped_message[last_line_index] = truncated_last_line.strip() + "..."
                else:
                    final_wrapped_message = wrapped_message_temp

            final_message_box_height = max_available_height_for_msg_box_area
            min_practical_height_for_box = (2 * message_box_padding) + final_font_random_msg.size
            final_message_box_height = max(final_message_box_height, min_practical_height_for_box)

            message_box = Image.new("RGBA", (message_box_width_for_random_msg, final_message_box_height), (0, 0, 0, 200))
            with Pilmoji(message_box) as pilmoji_draw:
                ImageDraw.Draw(message_box).rounded_rectangle((0, 0, message_box_width_for_random_msg, final_message_box_height), fill=(0, 0, 0, 200), radius=10)
                total_text_content_height = len(final_wrapped_message) * final_font_random_msg.size
                message_text_y_start = (final_message_box_height - total_text_content_height) // 2 if total_text_content_height <= (final_message_box_height - (2 * message_box_padding)) else message_box_padding
                current_text_y = message_text_y_start
                for i, line in enumerate(final_wrapped_message):
                    display_line = line
                    if i == 0:
                        display_line = "“" + display_line
                    if i == len(final_wrapped_message) - 1:
                        display_line = display_line.replace("...", "”...") if display_line.endswith("...") else display_line + "”"
                    temp_bbox = self.get_text_bbox(display_line, final_font_random_msg)
                    message_text_x = (message_box_width_for_random_msg - (temp_bbox[2] - temp_bbox[0])) // 2
                    pilmoji_draw.text((message_text_x, current_text_y), display_line, fill=(255, 255, 255), font=final_font_random_msg)
                    current_text_y += final_font_random_msg.size
            return message_box

        message_box = process_random_message()

        @time_section("Prepare Static Card")
        def prepare_static_card():
            try:
                static_card_base = base_card_content.copy()
            except Exception as e:
                log_collector.append(str(e))
                static_card_base = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))

            static_draw = ImageDraw.Draw(static_card_base)

            max_username_width_area = pfp_diameter + (2 * border_thickness) + 10
            username_initial_font_size = 30
            username_min_font_size = 18
            current_username_font_size = username_initial_font_size
            dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
            temp_username_to_measure = discord_username

            while True:
                dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
                temp_bbox = self.get_text_bbox(temp_username_to_measure, dynamic_font_username)
                temp_width = temp_bbox[2] - temp_bbox[0]
                if temp_width <= max_username_width_area:
                    break
                current_username_font_size -= 1
                if current_username_font_size < username_min_font_size:
                    current_username_font_size = username_min_font_size
                    dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
                    while True:
                        test_str_with_ellipsis = temp_username_to_measure + "..."
                        temp_bbox = self.get_text_bbox(test_str_with_ellipsis, dynamic_font_username)
                        temp_width = temp_bbox[2] - temp_bbox[0]
                        if temp_width <= max_username_width_area:
                            temp_username_to_measure = test_str_with_ellipsis
                            break
                        if len(temp_username_to_measure) > 1:
                            temp_username_to_measure = temp_username_to_measure[:-1]
                            while emoji.is_emoji(temp_username_to_measure[-1:]) and len(temp_username_to_measure) > 1:
                                temp_username_to_measure = temp_username_to_measure[:-1]
                        else:
                            temp_username_to_measure = "..."
                            break
                    break

            final_username_to_draw = temp_username_to_measure
            final_font_username = dynamic_font_username
            username_bbox = self.get_text_bbox(final_username_to_draw, final_font_username)
            username_center_x = pfp_x + (pfp_diameter // 2)
            username_x_aligned = username_center_x - ((username_bbox[2] - username_bbox[0]) // 2)

            joined_label = "MEMBER SINCE:"
            joined_date_str = join_date.strftime('%B %d, %Y')
            label_bbox = static_draw.textbbox((0, 0), joined_label, font=font_date_label)
            label_x_aligned = username_center_x - ((label_bbox[2] - label_bbox[0]) // 2)
            date_value_bbox = static_draw.textbbox((0, 0), joined_date_str, font=font_date_value)
            date_value_x_aligned = username_center_x - ((date_value_bbox[2] - date_value_bbox[0]) // 2)

            target_hex_color = self.rank_blink_colors.get(rank_str, "#808080")
            rank_color_end = self._hex_to_rgb(target_hex_color)
            rank_color_start = (255, 255, 255) if rank_str in inverted_text_roles else (0, 0, 0)
            base_text_color = (255, 255, 255) if rank_str in inverted_text_roles else (0, 0, 0)

            return static_card_base, static_draw, final_username_to_draw, final_font_username, username_x_aligned, label_x_aligned, joined_label, date_value_x_aligned, joined_date_str, rank_color_start, rank_color_end, base_text_color

        static_card_base, static_draw, final_username_to_draw, final_font_username, username_x_aligned, label_x_aligned, joined_label, date_value_x_aligned, joined_date_str, rank_color_start, rank_color_end, base_text_color = prepare_static_card()

        if not animated:
            @time_section("Render Static Card")
            def render_static_card():
                with Pilmoji(static_card_base) as pilmoji_draw:
                    pilmoji_draw.text((username_x_aligned, username_y), final_username_to_draw, fill=base_text_color, font=final_font_username)
                static_draw.text((right_column_x_start, rank_y), f"{rank_str}", fill=rank_color_end, font=font_rank_blinking)
                static_draw.text((label_x_aligned, member_since_label_y), joined_label, fill=base_text_color, font=font_date_label)
                static_draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=base_text_color, font=font_date_value)

                static_card_base.paste(pfp_image_pil, (pfp_x, pfp_y), pfp_image_pil)
                static_draw.ellipse(
                    (border_bbox_x1, border_bbox_y1, border_bbox_x2, border_bbox_y2),
                    outline=border_color,
                    width=border_thickness
                )

                static_card_base.paste(banner, (center_x, 15), banner)

                if is_top_feedback:
                    top_mfr_static_color = (59, 196, 237)
                    top_mfr_text_end_x, top_mfr_text_y = self._draw_top_mfr_badge(static_draw, current_y_for_points_block, right_column_x_start, font_top_mfr, top_mfr_icon_size, top_mfr_text_padding, top_mfr_static_color)
                    mf_points_static_text = f" - MF Points: {numeric_points}"
                    mf_points_x = top_mfr_text_end_x + 5
                    mf_points_y = top_mfr_text_y
                    static_draw.text((mf_points_x, mf_points_y), mf_points_static_text, fill=base_text_color, font=font_top_mfr)
                else:
                    mf_points_only_text = f"MF Points: {numeric_points}"
                    mf_points_only_y = current_y_for_points_block + (top_mfr_icon_size - font_top_mfr.size) // 2
                    static_draw.text((right_column_x_start, mf_points_only_y), mf_points_only_text, fill=base_text_color, font=font_top_mfr)

                badge_right_x = card_width - 10
                badge_y = banner_height + collab_circle_y_offset

                if has_booster_role:
                    booster_text = "Booster"
                    text_bbox = static_draw.textbbox((0, 0), booster_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    static_draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=booster_text_bg_color,
                        radius=pill_height // 2
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    static_draw.text((text_x, text_y), booster_text, fill=collab_text_color, font=font_collab)
                    badge_y += pill_height + badge_vertical_gap

                if has_collab_role:
                    collab_text = "COLLAB"
                    text_bbox = static_draw.textbbox((0, 0), collab_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    static_draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=collab_text_bg_color,
                        radius=pill_height // 2
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    static_draw.text((text_x, text_y), collab_text, fill=collab_text_color, font=font_collab)
                    badge_y += pill_height + badge_vertical_gap

                if has_host_role:
                    host_text = "HOST"
                    text_bbox = static_draw.textbbox((0, 0), host_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    static_draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=host_text_bg_color,
                        radius=pill_height // 2
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    static_draw.text((text_x, text_y), host_text, fill=collab_text_color, font=font_collab)

                current_tag_draw_x = right_column_x_start
                current_tag_draw_y = roles_y
                extra_vertical_gap = 5
                for i, tag_data in enumerate(final_displayed_roles):
                    tag_text = tag_data['name']
                    category_dot_color = tag_data['color']
                    text_bbox = self.get_text_bbox(tag_text, font_tag)
                    text_width = text_bbox[2] - text_bbox[0]
                    tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)
                    if i == len_first_line_roles:
                        current_tag_draw_x = right_column_x_start
                        current_tag_draw_y += tag_line_height + extra_vertical_gap
                    tag_rect = (current_tag_draw_x, current_tag_draw_y, current_tag_draw_x + tag_width, current_tag_draw_y + tag_line_height)
                    static_draw.rounded_rectangle(tag_rect, radius=tag_line_height // 2, fill=tag_bg_color)
                    dot_x = current_tag_draw_x + tag_horizontal_padding
                    dot_y = current_tag_draw_y + (tag_line_height - dot_diameter) // 2
                    static_draw.ellipse((dot_x, dot_y, dot_x + dot_diameter, dot_y + dot_diameter), fill=category_dot_color)
                    text_x = dot_x + dot_diameter + dot_right_margin
                    text_y = current_tag_draw_y + tag_vertical_padding - 1
                    with Pilmoji(static_card_base) as pilmoji_draw:
                        pilmoji_draw.text((text_x, text_y), tag_text, fill=tag_text_color, font=font_tag)
                    current_tag_draw_x += tag_width + tag_spacing_x

                if random_msg and message_box:
                    static_card_base.paste(message_box, (right_column_x_start, random_msg_y), message_box)

                output = io.BytesIO()
                static_card_base.save(output, format="PNG")
                output.seek(0)
                return output, "png"

            output, file_ext = render_static_card()
            end_time_total = time.time()
            log_collector.append(f"Total generate_card (static) took {end_time_total - start_time_total:.4f} seconds")
            return output, file_ext, log_collector

        top_mfr_color_start = (59, 196, 237)
        top_mfr_color_end = (
            int(top_mfr_color_start[0] + (255 - top_mfr_color_start[0]) * 0.5),
            int(top_mfr_color_start[1] + (255 - top_mfr_color_start[1]) * 0.5),
            int(top_mfr_color_start[2] + (255 - top_mfr_color_start[2]) * 0.5)
        )

        rank_display_text = f"{rank_str}"
        total_rank_chars = len(rank_display_text)
        reveal_frames = int(num_frames * 0.5)
        blink_frames = num_frames - reveal_frames

        @time_section("Create Gradient")
        def create_gradient():
            gradient_width = int(math.sqrt(card_width**2 + card_height**2)) * 2
            gradient_height = 100
            gradient = Image.new("RGBA", (gradient_width, gradient_height), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)
            for x in range(gradient_width):
                alpha = 0
                if x > gradient_width // 3 and x < 2 * gradient_width // 3:
                    alpha = int(128 * math.sin(math.pi * (x - gradient_width // 3) / (gradient_width // 3)))
                gradient_draw.line((x, 0, x, gradient_height), fill=(255, 255, 255, alpha))
            gradient = gradient.rotate(45, expand=True)
            return gradient

        gradient = create_gradient()

        @time_section("Render Animated Frames")
        def render_animated_frames():
            frames = []
            pink_color = (244, 127, 255)  # #f47fff
            black_color = (0, 0, 0)
            for i in range(num_frames):
                try:
                    frame = static_card_base.copy()
                except Exception as e:
                    log_collector.append(f"Error copying static_card_base: {str(e)}")
                    frame = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
                
                draw = ImageDraw.Draw(frame)
                pulse_progress = (math.sin(2 * math.pi * i / num_frames) + 1) / 2
                current_rank_pulse_color = (
                    int(rank_color_start[0] + (rank_color_end[0] - rank_color_start[0]) * pulse_progress),
                    int(rank_color_start[1] + (rank_color_end[1] - rank_color_start[1]) * pulse_progress),
                    int(rank_color_start[2] + (rank_color_end[2] - rank_color_start[2]) * pulse_progress)
                )

                current_text_color = base_text_color
                if rank_str == "Artist of the Week" and animated:
                    segment_length = num_frames / (len(flash_colors) - 1)
                    segment_index = int(i / segment_length)
                    if segment_index >= len(flash_colors) - 1:
                        segment_index = len(flash_colors) - 1
                    segment_progress = (i % segment_length) / segment_length
                    color1 = flash_colors[segment_index]
                    color2 = flash_colors[segment_index + 1] if segment_index + 1 < len(flash_colors) else color1
                    current_color = (
                        int(color1[0] + (color2[0] - color1[0]) * segment_progress),
                        int(color1[1] + (color2[1] - color1[1]) * segment_progress),
                        int(color1[2] + (color2[2] - color1[2]) * segment_progress)
                    )
                    draw.rectangle((0, 0, card_width, card_height), fill=current_color)
                    if base_card_content:
                        frame.paste(base_card_content, (0, 0), base_card_content)
                        draw = ImageDraw.Draw(frame)
                    brightness = sum(current_color) / 3
                    current_text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

                with Pilmoji(frame) as pilmoji_draw:
                    pilmoji_draw.text((username_x_aligned, username_y), final_username_to_draw, fill=current_text_color, font=final_font_username)
                draw.text((label_x_aligned, member_since_label_y), joined_label, fill=current_text_color, font=font_date_label)
                draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=current_text_color, font=font_date_value)

                progress = i / num_frames
                x_offset = int(amplitude * math.sin(2 * math.pi * progress))
                x = center_x + x_offset
                visible_banner = banner.crop((max(0, -x), 0, min(banner_width, card_width - x), banner_height))
                frame.paste(visible_banner, (max(0, x), 15), visible_banner)

                if rank_str in ["MF Gilded", "The Real MFrs"]:
                    total_cycle_frames = int(60 / (frame_duration / 1000))
                    cycle_frame = (i * 2) % (total_cycle_frames // num_frames * num_frames)
                    if cycle_frame < 40:
                        flash_progress = cycle_frame / 40
                        offset_x = int(-gradient.size[0] + flash_progress * (gradient.size[0] + card_width))
                        offset_y = int(-gradient.size[1] + flash_progress * (gradient.size[1] + card_height))
                        frame.paste(gradient, (offset_x, offset_y), gradient)

                frame.paste(pfp_image_pil, (pfp_x, pfp_y), pfp_image_pil)
                draw.ellipse(
                    (border_bbox_x1, border_bbox_y1, border_bbox_x2, border_bbox_y2),
                    outline=border_color,
                    width=border_thickness
                )

                if i < reveal_frames:
                    chars_to_show = int(total_rank_chars * (i / reveal_frames))
                    current_rank_segment = rank_display_text[:chars_to_show]
                    draw.text((right_column_x_start, rank_y), current_rank_segment, fill=current_rank_pulse_color, font=font_rank_blinking)
                else:
                    draw.text((right_column_x_start, rank_y), rank_display_text, fill=current_rank_pulse_color, font=font_rank_blinking)

                if is_top_feedback:
                    current_top_mfr_color = (
                        int(top_mfr_color_start[0] + (top_mfr_color_end[0] - top_mfr_color_start[0]) * pulse_progress),
                        int(top_mfr_color_start[1] + (top_mfr_color_end[1] - top_mfr_color_start[1]) * pulse_progress),
                        int(top_mfr_color_start[2] + (top_mfr_color_end[2] - top_mfr_color_start[2]) * pulse_progress)
                    )
                    top_mfr_text_end_x, top_mfr_text_y = self._draw_top_mfr_badge(
                        draw, current_y_for_points_block, right_column_x_start, 
                        font_top_mfr, top_mfr_icon_size, top_mfr_text_padding, current_top_mfr_color
                    )
                    mf_points_static_text = f" - MF Points: {numeric_points}"
                    mf_points_x = top_mfr_text_end_x + 5
                    mf_points_y = top_mfr_text_y
                    draw.text((mf_points_x, mf_points_y), mf_points_static_text, fill=current_text_color, font=font_top_mfr)
                else:
                    mf_points_only_text = f"MF Points: {numeric_points}"
                    mf_points_only_y = current_y_for_points_block + (top_mfr_icon_size - font_top_mfr.size) // 2
                    draw.text((right_column_x_start, mf_points_only_y), mf_points_only_text, fill=current_text_color, font=font_top_mfr)

                badge_right_x = card_width - 10
                badge_y = banner_height + collab_circle_y_offset

                if has_booster_role:
                    booster_text = "Booster"
                    text_bbox = draw.textbbox((0, 0), booster_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    current_booster_bg_color = (
                        int(pink_color[0] + (black_color[0] - pink_color[0]) * pulse_progress),
                        int(pink_color[1] + (black_color[1] - pink_color[1]) * pulse_progress),
                        int(pink_color[2] + (black_color[2] - pink_color[2]) * pulse_progress)
                    )
                    draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=current_booster_bg_color,
                        radius=pill_height // 2
                    )
                    current_booster_text_color = (
                        int(black_color[0] + (pink_color[0] - black_color[0]) * pulse_progress),
                        int(black_color[1] + (pink_color[1] - black_color[1]) * pulse_progress),
                        int(black_color[2] + (pink_color[2] - black_color[2]) * pulse_progress)
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    draw.text((text_x, text_y), booster_text, fill=current_booster_text_color, font=font_collab)
                    badge_y += pill_height + badge_vertical_gap

                if has_collab_role:
                    collab_text = "COLLAB"
                    text_bbox = draw.textbbox((0, 0), collab_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=collab_text_bg_color,
                        radius=pill_height // 2
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    draw.text((text_x, text_y), collab_text, fill=collab_text_color, font=font_collab)
                    badge_y += pill_height + badge_vertical_gap

                if has_host_role:
                    host_text = "HOST"
                    text_bbox = draw.textbbox((0, 0), host_text, font=font_collab)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    pill_width = text_width + 12
                    pill_height = text_height + 8
                    rect_right = badge_right_x
                    rect_left = badge_right_x - pill_width
                    rect_top = badge_y
                    rect_bottom = badge_y + pill_height
                    draw.rounded_rectangle(
                        (rect_left, rect_top, rect_right, rect_bottom),
                        fill=host_text_bg_color,
                        radius=pill_height // 2
                    )
                    text_x = rect_left + (pill_width - text_width) // 2
                    text_y = badge_y + (pill_height - text_height) // 2 - 2
                    draw.text((text_x, text_y), host_text, fill=collab_text_color, font=font_collab)

                current_tag_draw_x = right_column_x_start
                current_tag_draw_y = roles_y
                extra_vertical_gap = 5
                for i, tag_data in enumerate(final_displayed_roles):
                    tag_text = tag_data['name']
                    category_dot_color = tag_data['color']
                    text_bbox = self.get_text_bbox(tag_text, font_tag)
                    text_width = text_bbox[2] - text_bbox[0]
                    tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)
                    if i == len_first_line_roles:
                        current_tag_draw_x = right_column_x_start
                        current_tag_draw_y += tag_line_height + extra_vertical_gap
                    tag_rect = (current_tag_draw_x, current_tag_draw_y, current_tag_draw_x + tag_width, current_tag_draw_y + tag_line_height)
                    draw.rounded_rectangle(tag_rect, radius=tag_line_height // 2, fill=tag_bg_color)
                    dot_x = current_tag_draw_x + tag_horizontal_padding
                    dot_y = current_tag_draw_y + (tag_line_height - dot_diameter) // 2
                    draw.ellipse((dot_x, dot_y, dot_x + dot_diameter, dot_y + dot_diameter), fill=category_dot_color)
                    text_x = dot_x + dot_diameter + dot_right_margin
                    text_y = current_tag_draw_y + tag_vertical_padding - 1
                    with Pilmoji(frame) as pilmoji_draw:
                        pilmoji_draw.text((text_x, text_y), tag_text, fill=tag_text_color, font=font_tag)
                    current_tag_draw_x += tag_width + tag_spacing_x

                if random_msg and message_box:
                    frame.paste(message_box, (right_column_x_start, random_msg_y), message_box)

                dithered = frame.convert("P", palette=Image.ADAPTIVE, dither=Image.FLOYDSTEINBERG)
                frames.append(dithered)

            output = io.BytesIO()
            if frames:
                frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:], duration=frame_duration, loop=0)
            output.seek(0)
            return output, "gif", log_collector

        output, file_ext, log_collector = render_animated_frames()
        end_time_total = time.time()
        log_collector.append(f"Total generate_card (animated) took {end_time_total - start_time_total:.4f} seconds")
        return output, file_ext, log_collector

    def wrap_text(self, text, font, max_width):
        wrapped_lines = []
        words = text.split()
        current_line = ""
        for word in words:
            bbox_word = self.get_text_bbox(word, font)
            word_width = bbox_word[2] - bbox_word[0]
            if word_width > max_width:
                if current_line:
                    wrapped_lines.append(current_line.strip())
                    current_line = ""
                temp_word_part = ""
                for char in word:
                    test_temp_part = temp_word_part + char
                    temp_part_bbox = self.get_text_bbox(test_temp_part, font)
                    if (temp_part_bbox[2] - temp_part_bbox[0]) <= max_width:
                        temp_word_part += char
                    else:
                        wrapped_lines.append(temp_word_part)
                        temp_word_part = char
                if temp_word_part:
                    wrapped_lines.append(temp_word_part)
            else:
                test_line = current_line + word + " "
                test_bbox = self.get_text_bbox(test_line, font)
                test_width = test_bbox[2] - test_bbox[0]
                if test_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped_lines.append(current_line.strip())
                    current_line = word + " "
        if current_line.strip():
            wrapped_lines.append(current_line.strip())
        return wrapped_lines

    @time_it
    @app_commands.checks.has_any_role(*["Admins", "Moderators", "Chat Moderators"])
    @mf_card_group.command(name="card", description="View a member's MF Card.")
    @app_commands.describe(member="The member whose MF Card you want to view (defaults to you).")
    async def view_mf_card(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        log_collector = []
        if member is None:
            member = interaction.user

        cog = self.bot.get_cog("MemberCards")
        if not cog:
            log_collector.append("MemberCards cog is not loaded. Please ensure it's loaded.")
            await interaction.followup.send("MemberCards cog is not loaded. Please ensure it's loaded.", ephemeral=True)
            await self.send_log_to_discord(log_collector, interaction.guild)
            return

        discord_username = member.display_name
        pfp_url = await cog.get_pfp(member)
        join_date = await cog.get_join_date(member)

        if isinstance(join_date, str):
            try:
                join_date = datetime.strptime(join_date, "%Y-%m-%d")
            except ValueError:
                join_date = datetime.now()
                log_collector.append(f"Invalid join date format for {discord_username}. Using current date.")

        rank_str = await cog.get_rank(member)
        is_top_feedback, numeric_points = False, 0
        try:
            is_top_feedback, numeric_points = await cog.get_points(member)
        except Exception as e:
            log_collector.append(f"Error calling get_points for {discord_username}: {str(e)}")
            is_top_feedback = False
            numeric_points = 0

        all_main_genres_roles, all_daw_roles, all_instruments_roles = await self.bot.get_cog("MemberCards").get_roles_by_colors(member)
        message_count = await cog.get_message_count(member)

        random_msg_content = ""
        random_msg_url = None
        try:
            retrieved_msg_data = await cog.get_random_message(member)
            if retrieved_msg_data and len(retrieved_msg_data) == 2:
                random_msg_content, random_msg_url = retrieved_msg_data
            else:
                random_msg_content = "A true MFR"
                random_msg_url = None
        except Exception as e:
            log_collector.append(f"Error fetching random message for {discord_username}: {str(e)}")
            random_msg_content = "An unexpected error occurred while looking for a message."
            random_msg_url = None

        last_music = await cog.get_last_finished_music(member)
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
        card_buffer, file_ext, log_collector = self.generate_card(
            pfp, discord_username, server_name, rank_str, numeric_points, message_count, join_date,
            (img_width, img_height), self.font_path, animated=animated, random_msg=random_msg_content,
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