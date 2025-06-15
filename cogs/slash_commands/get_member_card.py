import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter, ImageOps
import io
import os
import traceback
import math
from datetime import datetime
import aiohttp
from pilmoji import Pilmoji 
import emoji
from typing import Optional

class GetMemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        current_script_dir = os.path.dirname(__file__)

        base_media_dir = os.path.abspath(os.path.join(current_script_dir, "../../media/Bebas_Neue/"))

        self.font_path = os.path.join(base_media_dir, "BebasNeue-Regular.ttf")
        self.background_images_dir = os.path.join(base_media_dir, "images/")

        # IMPORTANT: Also update the hardcoded path for the banner image later in generate_card
        # We will define it here so it can be used later.
        self._banner_image_path = os.path.join(self.background_images_dir, "banner.png")


        self.background_map = {
            "Owner": "moderators.png",
            "Admins": "moderators.png",
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

    def generate_card(self, pfp_image_pil, discord_username, server_name, rank_str, numeric_points, message_count, join_date, card_size, font_path, animated=True, random_msg="", is_top_feedback=False, **kwargs):
        frames = []
        num_frames = 100
        frame_duration = 75

        # --- Font and Size Definitions ---
        # font_username will be determined dynamically
        font_date_label = ImageFont.truetype(font_path, 20)
        font_date_value = ImageFont.truetype(font_path, 25)
        font_rank_blinking = ImageFont.truetype(font_path, 55)
        font_top_mfr = ImageFont.truetype(font_path, 30)
        # font_random_msg will be determined dynamically
        font_tag = ImageFont.truetype(font_path, 12) # Adjusted font for individual tags

        # Define icon and text padding sizes used in badge drawing and layout
        top_mfr_icon_size = 30
        top_mfr_text_padding = 8
        # --- End Font and Size Definitions ---

        # Retrieve all roles for each category from kwargs
        all_genres_roles = kwargs.get("all_genres_roles", [])
        all_daws_roles = kwargs.get("all_daws_roles", [])
        all_instruments_roles = kwargs.get("all_instruments_roles", [])

        tag_text_color = (255, 255, 255) # White text for dark tags

        # Tag dimensions and spacing (ADJUSTED for smaller and closer)
        tag_horizontal_padding = 8 # Padding inside tag, around text and dot
        tag_vertical_padding = 4   # Vertical padding inside tag
        dot_diameter = 7 # Size of the color dot
        dot_right_margin = 4 # Space between dot and text
        tag_spacing_x = 5 # Space between tags horizontally
        tag_line_height = font_tag.size + (2 * tag_vertical_padding)

        card_width, card_height = card_size

        banner = Image.open(self._banner_image_path).convert("RGBA")
        banner = banner.crop((0, 5, 800, 35))
        banner_width, banner_height = banner.size
        amplitude = 50
        center_x = (card_width // 2) - (banner_width // 2)

        inverted_text_roles = ["Owner", "Admins", "Moderators", "Chat Moderators", "Bot Boinker"]

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
                if rank_str in inverted_text_roles:
                    background_filename = os.path.join(self.background_images_dir, "moderators.png")
                background_image_path = os.path.join(self.background_images_dir, background_filename)
            base_card_content = None
            if background_image_path and os.path.exists(background_image_path):
                try:
                    background_image = Image.open(background_image_path).convert("RGBA")
                    base_card_content = background_image.resize((card_width, card_height), Image.Resampling.LANCZOS)
                except Exception as e:
                    print(f"Error loading background image '{background_image_path}': {e}. Falling back to gradient.")
                    base_card_content = None
            if base_card_content is None:
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
        current_left_y += 30 + 5 # Use initial font size for calculation if username_font_size is not yet defined
        member_since_label_y = current_left_y
        current_left_y += font_date_label.size
        join_date_value_y = current_left_y
        current_left_y += font_date_value.size + 20

        right_column_x_start = pfp_x + pfp_diameter + 30
        rank_y = pfp_y + 10 # Starting Y for the Rank text

        # Calculate Y position for the start of the "TOP MFR / MF Points" block
        current_y_for_points_block = rank_y + font_rank_blinking.size + 10 # Padding after rank

        # Determine the effective bottom Y of the points block
        bottom_of_points_block_y = 0
        if is_top_feedback:
            bottom_of_points_block_y = current_y_for_points_block + max(top_mfr_icon_size, font_top_mfr.size)
        else:
            bottom_of_points_block_y = current_y_for_points_block + font_top_mfr.size

        # --- Roles block starts below the points block ---
        roles_y = bottom_of_points_block_y + 10 # Add padding after points block

        # The random message box should be as wide as it was before the previous change.
        # This is the full available width of the right column.
        message_box_width_for_random_msg = card_width - right_column_x_start - 30 

        # Available width for tags. This is the entire right column's content area.
        tag_line_available_width = card_width - right_column_x_start - 30 
        tag_bg_color = (40, 40, 40, 200) # Semi-transparent dark grey for tag background

        # --- REVISED ROLE LOGIC ---
        displayed_roles_raw = [] # Store tuples of (role_name, color)
        total_hidden_count = 0

        # Add up to 2 genres
        if all_genres_roles:
            for role_name in all_genres_roles[:2]:
                displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#8d8c8c")})
            total_hidden_count += max(0, len(all_genres_roles) - 2)

        # Add up to 2 DAWs
        if all_daws_roles:
            for role_name in all_daws_roles[:2]:
                displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#6155a6")})
            total_hidden_count += max(0, len(all_daws_roles) - 2)

        # Add up to 2 Instruments
        if all_instruments_roles:
            for role_name in all_instruments_roles[:2]:
                displayed_roles_raw.append({'name': role_name, 'color': self._hex_to_rgb("#e3abff")})
            total_hidden_count += max(0, len(all_instruments_roles) - 2)

        # Remove duplicates from the initially selected roles (e.g., if a role is both genre and DAW)
        seen_displayed_roles = set()
        displayed_roles_final = []
        for role_data in displayed_roles_raw:
            if role_data['name'] not in seen_displayed_roles:
                displayed_roles_final.append(role_data)
                seen_displayed_roles.add(role_data['name'])
            # Note: If a role name appears multiple times (e.g., in different categories),
            # this logic ensures it's only *displayed* once. The `total_hidden_count`
            # still reflects the original count from each category. This is generally
            # the desired behavior for a compact display.

        # Prepare for potential "+X" tag
        temp_draw_for_measurement = ImageDraw.Draw(Image.new("RGB", (1,1)))
        neutral_extra_color = (128, 128, 128) # Grey for the +x dot

        final_displayed_roles = []
        current_tags_width = 0

        # Determine if a "+X" tag is needed and its estimated width
        plus_x_tag_data = None
        plus_x_tag_width_estimate = 0
        if total_hidden_count > 0:
            plus_x_text = f"+{total_hidden_count}"
            plus_x_text_bbox = temp_draw_for_measurement.textbbox((0,0), plus_x_text, font=font_tag)
            plus_x_text_width = plus_x_text_bbox[2] - plus_x_text_bbox[0]
            plus_x_tag_width_estimate = dot_diameter + dot_right_margin + plus_x_text_width + (2 * tag_horizontal_padding) + tag_spacing_x
            plus_x_tag_data = {'name': plus_x_text, 'color': neutral_extra_color}

        # Iterate through `displayed_roles_final` to fit roles, leaving space for "+X"
        for i, tag_data in enumerate(displayed_roles_final):
            tag_text = tag_data['name']
            text_bbox = temp_draw_for_measurement.textbbox((0, 0), tag_text, font=font_tag)
            text_width = text_bbox[2] - text_bbox[0]
            tag_full_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding) + tag_spacing_x

            # Check if this tag fits, considering the remaining space must also accommodate the "+X" tag
            # If no +X tag is needed, then we use the full available width.
            remaining_space_for_tags = tag_line_available_width - current_tags_width
            
            if plus_x_tag_data: # If a +X tag is expected
                if tag_full_width + plus_x_tag_width_estimate <= remaining_space_for_tags:
                    final_displayed_roles.append(tag_data)
                    current_tags_width += tag_full_width
                else:
                    # This role doesn't fit if we need to reserve space for +X
                    # We already know total_hidden_count, so no need to increment it here.
                    break 
            else: # No +X tag expected, so just fit as many as possible
                if tag_full_width <= remaining_space_for_tags:
                    final_displayed_roles.append(tag_data)
                    current_tags_width += tag_full_width
                else:
                    break


        # Finally, append the "+X" tag if needed and it fits
        if plus_x_tag_data and (current_tags_width + plus_x_tag_width_estimate <= tag_line_available_width):
            final_displayed_roles.append(plus_x_tag_data)
        elif plus_x_tag_data:
            # If the +X tag itself doesn't fit even with all prior tags removed,
            # this indicates an extreme case where the line is too short.
            # In a very rare scenario, this might leave no roles shown if the +X tag
            # itself is larger than the line, but it should generally fit if the line
            # is long enough for at least one small tag.
            # We ensure the +X is shown by clearing previous tags if needed.
            # This loop makes sure the +X tag is *always* attempted to be displayed if `total_hidden_count > 0`
            # even if it means removing all other tags.
            while final_displayed_roles and (current_tags_width + plus_x_tag_width_estimate > tag_line_available_width):
                removed_tag = final_displayed_roles.pop()
                removed_tag_text_bbox = temp_draw_for_measurement.textbbox((0,0), removed_tag['name'], font=font_tag)
                removed_tag_width = dot_diameter + dot_right_margin + (removed_tag_text_bbox[2] - removed_tag_text_bbox[0]) + (2 * tag_horizontal_padding) + tag_spacing_x
                current_tags_width -= removed_tag_width

            if (current_tags_width + plus_x_tag_width_estimate <= tag_line_available_width):
                final_displayed_roles.append(plus_x_tag_data)
            # If it still doesn't fit, there's likely a layout issue where the line is too short even for "+1".
            # For this context, we assume it will eventually fit or it's a critical layout problem.


        roles_block_height = tag_line_height if final_displayed_roles else 0
        # --- End REVISED ROLE LOGIC ---


        # Random message box starts below the roles block
        random_msg_y = roles_y + roles_block_height + 10 # Add padding after roles block
        
        # --- Dynamic Font Sizing and Truncation for Random Message ---
        message_box = None # Initialize message_box outside the if block
        if random_msg:
            random_msg_initial_font_size = 20
            random_msg_min_font_size = font_tag.size # Smallest allowed, 12
            
            # Calculate the effective bottom Y coordinate of the "member since date" block
            bottom_of_member_since_date_block_y = join_date_value_y + font_date_value.size

            # The target height if the message box aligns its bottom with the date block
            # This is the space from random_msg_y down to the bottom of the date text.
            height_if_align_to_date_bottom = bottom_of_member_since_date_block_y - random_msg_y

            # Max height available down to the bottom of the card with a buffer
            bottom_buffer_for_message_box = 20
            max_height_to_card_bottom = card_height - random_msg_y - bottom_buffer_for_message_box

            # Determine the maximum available height for the message box.
            # If the top of the message box (`random_msg_y`) is already below the date's bottom,
            # then the "alignment height" would be negative or zero. In that case, we just
            # limit by the card's bottom. Otherwise, take the minimum of the two constraints.
            if height_if_align_to_date_bottom > 0:
                max_available_height_for_msg_box_area = min(height_if_align_to_date_bottom, max_height_to_card_bottom)
            else: 
                # Message box starts below the date's bottom, so just use card bottom limit
                max_available_height_for_msg_box_area = max(max_height_to_card_bottom, 0) # Ensure it's not negative

            # Ensure there's at least a minimal height for content/padding if a message is present.
            # This prevents issues if calculated max_available_height is too small or negative.
            min_practical_height = (2 * 10) + random_msg_min_font_size # 2*padding + height of 1 line at min font
            if max_available_height_for_msg_box_area < min_practical_height:
                 max_available_height_for_msg_box_area = max(min_practical_height, 0)
            
            # Initialize final_font_random_msg to a default in case no text fits
            final_font_random_msg = ImageFont.truetype(font_path, random_msg_min_font_size)
            final_wrapped_message = [] 
            
            current_font_size = random_msg_initial_font_size
            font_found = False

            while current_font_size >= random_msg_min_font_size:
                temp_font = ImageFont.truetype(font_path, current_font_size)
                message_box_padding = 10 # Padding inside the message box

                effective_text_width = message_box_width_for_random_msg - (2 * message_box_padding)
                if effective_text_width <= 0: 
                    effective_text_width = 1 # Avoid division by zero or negative width issues

                wrapped_message_temp = self.wrap_text(random_msg, temp_font, effective_text_width)
                
                temp_message_content_height = len(wrapped_message_temp) * temp_font.size
                temp_message_box_total_height = temp_message_content_height + (2 * message_box_padding)

                if temp_message_box_total_height <= max_available_height_for_msg_box_area:
                    final_wrapped_message = wrapped_message_temp
                    final_font_random_msg = temp_font
                    font_found = True
                    break # Found a font size that fits

                current_font_size -= 1 # Try a smaller font size

            # --- MODIFIED TRUNCATION LOGIC HERE ---
            # If no font fit even at min_font_size, or if it still overflows at min_font_size,
            # truncate and add "..."
            if not font_found:
                final_font_random_msg = ImageFont.truetype(font_path, random_msg_min_font_size)
                message_box_padding = 10
                effective_text_width = message_box_width_for_random_msg - (2 * message_box_padding)
                if effective_text_width <= 0:
                    effective_text_width = 1

                wrapped_message_temp = self.wrap_text(random_msg, final_font_random_msg, effective_text_width)
                
                # Calculate max lines that can fit at min_font_size within the available height
                max_content_height_at_min_font = max_available_height_for_msg_box_area - (2 * message_box_padding)
                max_lines_for_min_font = math.floor(max_content_height_at_min_font / final_font_random_msg.size)
                
                if max_lines_for_min_font <= 0: 
                    # If even one line at min font doesn't fit, show just "..."
                    final_wrapped_message = ["..."] 
                elif len(wrapped_message_temp) > max_lines_for_min_font:
                    # Truncate the last line and add "..."
                    final_wrapped_message = wrapped_message_temp[:max_lines_for_min_font] # Get all lines that fit
                    last_line_index = max_lines_for_min_font - 1 # Index of the last line
                    if last_line_index >= 0:
                        original_last_line = final_wrapped_message[last_line_index]
                        truncated_last_line = ""
                        # Determine the maximum text that can fit on the last line with "..."
                        ellipsis_width = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), "...", font=final_font_random_msg)[2] - ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), "...", font=final_font_random_msg)[0]
                        max_text_width_for_last_line = effective_text_width - ellipsis_width

                        for char in original_last_line:
                            test_line = truncated_last_line + char
                            test_width = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), test_line, font=final_font_random_msg)[2] - ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), test_line, font=final_font_random_msg)[0]
                            if test_width <= max_text_width_for_last_line:
                                truncated_last_line += char
                            else:
                                break
                        final_wrapped_message[last_line_index] = truncated_last_line.strip() + "..."
                    else: # No lines fit at all
                        final_wrapped_message = ["..."]
                else:
                    # It fits at min font size
                    final_wrapped_message = wrapped_message_temp

            # --- End MODIFIED TRUNCATION LOGIC ---

            # --- FORCE final_message_box_height to align with date bottom or card bottom ---
            # Use the calculated max_available_height_for_msg_box_area as the explicit height.
            # This forces the box to be this tall, regardless of how much text it contains,
            # ensuring it reaches the desired bottom alignment.
            final_message_box_height = max_available_height_for_msg_box_area

            # Ensure minimum height is still respected even if max_available_height_for_msg_box_area is very small.
            min_practical_height_for_box = (2 * message_box_padding) + (final_font_random_msg.size if final_font_random_msg else random_msg_min_font_size)
            final_message_box_height = max(final_message_box_height, min_practical_height_for_box)


            # Create the message box image using the determined size and wrapped text
            message_box = Image.new("RGBA", (message_box_width_for_random_msg, final_message_box_height), (0, 0, 0, 200))
            
            # Use Pilmoji for drawing text with emojis
            with Pilmoji(message_box) as pilmoji_draw:
                # Draw the rounded rectangle background *before* text
                ImageDraw.Draw(message_box).rounded_rectangle((0, 0, message_box_width_for_random_msg, final_message_box_height), fill=(0, 0, 0, 200), radius=10)
                
                # Now, draw the text. The text should be vertically centered within this forced height.
                total_text_content_height = len(final_wrapped_message) * final_font_random_msg.size
                
                # Calculate y_offset for vertical centering of the text within the box
                # If total_text_content_height is greater than final_message_box_height - (2 * message_box_padding),
                # it means the text content itself is larger than the available space within the box's padding.
                # In this scenario, we should not aim for perfect centering but rather start from padding top.
                if total_text_content_height > (final_message_box_height - (2 * message_box_padding)):
                    message_text_y_start = message_box_padding
                else:
                    message_text_y_start = (final_message_box_height - total_text_content_height) // 2

                current_text_y = message_text_y_start
                for i, line in enumerate(final_wrapped_message):
                    display_line = line
                    # Add opening quote to the first line
                    if i == 0:
                        display_line = "“" + display_line
                    # Add closing quote to the last line
                    if i == len(final_wrapped_message) - 1:
                        # Make sure not to double-add if it's "..."
                        if not display_line.endswith("..."):
                            display_line += "”"
                        else: # If it ends with "...", place quote before it
                            display_line = display_line.replace("...", "”...")

                    # Use temporary ImageDraw for textbbox to ensure accurate centering, as Pilmoji's textbbox
                    # might behave slightly differently for composite glyphs.
                    temp_bbox_for_centering = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), display_line, font=final_font_random_msg)
                    message_text_x = (message_box_width_for_random_msg - (temp_bbox_for_centering[2] - temp_bbox_for_centering[0])) // 2

                    # Use pilmoji_draw.text instead of message_box_draw.text
                    pilmoji_draw.text((message_text_x, current_text_y), display_line, fill=(255, 255, 255), font=final_font_random_msg)
                    current_text_y += final_font_random_msg.size
        # --- End Dynamic Font Sizing and Truncation for Random Message ---


        static_card_base = base_card_content.copy()
        static_draw = ImageDraw.Draw(static_card_base)

        # --- Dynamic Font Sizing for Username ---
        max_username_width_area = pfp_diameter + (2 * border_thickness) + 10 # Adding a small buffer
        username_initial_font_size = 30
        username_min_font_size = 18 # Smallest allowed font for username

        current_username_font_size = username_initial_font_size
        dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
        
        # Test with the full username first
        temp_username_to_measure = discord_username
        
        while True:
            temp_bbox = static_draw.textbbox((0, 0), temp_username_to_measure, font=dynamic_font_username)
            temp_width = temp_bbox[2] - temp_bbox[0]

            if temp_width <= max_username_width_area:
                break # It fits at this size, or larger if we're reducing.

            current_username_font_size -= 1
            if current_username_font_size < username_min_font_size:
                # If even min font is too big, then we must truncate
                current_username_font_size = username_min_font_size 
                dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
                # Now, truncate the username until it fits with the min font size
                while True:
                    # Append "..." for measurement, then adjust
                    test_str_with_ellipsis = temp_username_to_measure + "..." 
                    temp_bbox = static_draw.textbbox((0, 0), test_str_with_ellipsis, font=dynamic_font_username)
                    temp_width = temp_bbox[2] - temp_bbox[0]
                    if temp_width <= max_username_width_area:
                        temp_username_to_measure = test_str_with_ellipsis # Store it with ellipsis
                        break
                    if len(temp_username_to_measure) > 1: # Prevent endless loop or empty string
                        temp_username_to_measure = temp_username_to_measure[:-1] # Remove last char
                    else: # If it's down to one char and still too big, just use "..."
                        temp_username_to_measure = "..."
                        break
                break # Break from the outer while loop as we've adjusted/truncated

            dynamic_font_username = ImageFont.truetype(font_path, current_username_font_size)
        
        final_username_to_draw = temp_username_to_measure
        final_font_username = dynamic_font_username
        # --- End Dynamic Font Sizing for Username ---


        username_bbox = static_draw.textbbox((0, 0), final_username_to_draw, font=final_font_username)
        username_center_x = pfp_x + (pfp_diameter // 2)
        username_x_aligned = username_center_x - ((username_bbox[2] - username_bbox[0]) // 2)

        joined_label = "MEMBER SINCE:"
        joined_date_str = join_date.strftime('%B %d, %Y')
        label_bbox = static_draw.textbbox((0,0), joined_label, font=font_date_label)
        label_x_aligned = username_center_x - ((label_bbox[2] - label_bbox[0]) // 2)
        date_value_bbox = static_draw.textbbox((0,0), joined_date_str, font=font_date_value)
        date_value_x_aligned = username_center_x - ((date_value_bbox[2] - date_value_bbox[0]) // 2)

        target_hex_color = self.rank_blink_colors.get(rank_str, "#808080")
        rank_color_end = self._hex_to_rgb(target_hex_color)
        rank_color_start = (0, 0, 0)

        base_text_color = (255, 255, 255) if rank_str in inverted_text_roles else (0, 0, 0)

        if not animated:
            output = io.BytesIO()
            static_draw.text((right_column_x_start, rank_y), f"{rank_str}", fill=rank_color_end, font=font_rank_blinking)
            static_draw.text((username_x_aligned, username_y), final_username_to_draw, fill=base_text_color, font=final_font_username) # Use dynamic font and name
            static_draw.text((label_x_aligned, member_since_label_y), joined_label, fill=base_text_color, font=font_date_label)
            static_draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=base_text_color, font=font_date_value)

            # Draw MF Points / Top MFR for static card
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

            # Draw roles for static card (using final_displayed_roles)
            current_tag_draw_x = right_column_x_start
            current_tag_draw_y = roles_y # This remains fixed for single line
            
            for tag_data in final_displayed_roles:
                tag_text = tag_data['name']
                category_dot_color = tag_data['color']
                
                text_bbox = static_draw.textbbox((0, 0), tag_text, font=font_tag)
                text_width = text_bbox[2] - text_bbox[0]
                
                tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)

                # Draw rounded rectangle background
                tag_rect = (current_tag_draw_x, current_tag_draw_y,
                            current_tag_draw_x + tag_width, current_tag_draw_y + tag_line_height)
                static_draw.rounded_rectangle(tag_rect, radius=tag_line_height // 2, fill=tag_bg_color)

                # Draw color dot
                dot_x = current_tag_draw_x + tag_horizontal_padding
                dot_y = current_tag_draw_y + (tag_line_height - dot_diameter) // 2
                static_draw.ellipse((dot_x, dot_y, dot_x + dot_diameter, dot_y + dot_diameter), fill=category_dot_color)

                # Draw tag text
                text_x = dot_x + dot_diameter + dot_right_margin
                text_y = current_tag_draw_y + tag_vertical_padding - 1 # Adjusted for visual centering
                static_draw.text((text_x, text_y), tag_text, fill=tag_text_color, font=font_tag)

                current_tag_draw_x += tag_width + tag_spacing_x

            if random_msg and message_box: # Only paste if message_box was created and message exists
                static_card_base.paste(message_box, (right_column_x_start, random_msg_y), message_box)
            static_card_base.save(output, format="PNG")
            output.seek(0)
            return output, "png"

        top_mfr_color_start = (59, 196, 237)
        # Corrected calculation for top_mfr_color_end
        top_mfr_color_end = (
            int(top_mfr_color_start[0] + (255 - top_mfr_color_start[0]) * 0.5), # Blend with white for Red channel
            int(top_mfr_color_start[1] + (255 - top_mfr_color_start[1]) * 0.5), # Blend with white for Green channel
            int(top_mfr_color_start[2] + (255 - top_mfr_color_start[2]) * 0.5)  # Blend with white for Blue channel
        )

        rank_display_text = f"{rank_str}"
        total_rank_chars = len(rank_display_text)
        reveal_frames = int(num_frames * 0.5)
        blink_frames = num_frames - reveal_frames

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

        for i in range(num_frames):
            frame = static_card_base.copy() # Start with the base content
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
                    segment_index = len(flash_colors) - 2

                segment_progress = (i % segment_length) / segment_length

                color1 = flash_colors[segment_index]
                color2 = flash_colors[segment_index + 1]

                current_color = (
                    int(color1[0] + (color2[0] - color1[0]) * segment_progress),
                    int(color1[1] + (color2[1] - color1[1]) * segment_progress),
                    int(color1[2] + (color2[2] - color1[2]) * segment_progress)
                )
                draw.rectangle((0, 0, card_width, card_height), fill=current_color)
                # If there's a background image, redraw it transparently on top of the flashing color
                if base_card_content:
                    frame.paste(base_card_content, (0,0), base_card_content) 
                    draw = ImageDraw.Draw(frame) # Re-get draw object to draw on the updated frame
                
                brightness = sum(current_color) / 3
                current_text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

            draw.text((username_x_aligned, username_y), final_username_to_draw, fill=current_text_color, font=final_font_username) # Use dynamic font and name
            draw.text((label_x_aligned, member_since_label_y), joined_label, fill=current_text_color, font=font_date_label)
            draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=current_text_color, font=font_date_value)

            progress = i / num_frames
            x_offset = int(amplitude * math.sin(2 * math.pi * progress))
            x = center_x + x_offset
            visible_banner = banner.crop((max(0, -x), 0, min(banner_width, card_width - x), banner_height))
            frame.paste(visible_banner, (max(0, x), 15), visible_banner)

            if rank_str in ["MF Gilded", "The Real Mfrs"]:
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

            # Draw MF Points / Top MFR
            if is_top_feedback:
                current_top_mfr_pulse_color = (
                    int(top_mfr_color_start[0] + (top_mfr_color_end[0] - top_mfr_color_start[0]) * pulse_progress),
                    int(top_mfr_color_start[1] + (top_mfr_color_end[1] - top_mfr_color_start[1]) * pulse_progress),
                    int(top_mfr_color_start[2] + (top_mfr_color_end[2] - top_mfr_color_start[2]) * pulse_progress)
                )
                top_mfr_text_end_x, top_mfr_text_y = self._draw_top_mfr_badge(draw, current_y_for_points_block, right_column_x_start, font_top_mfr, top_mfr_icon_size, top_mfr_text_padding, current_top_mfr_pulse_color)
                mf_points_static_text = f" - MF Points: {numeric_points}"
                mf_points_x = top_mfr_text_end_x + 5
                mf_points_y = top_mfr_text_y
                draw.text((mf_points_x, mf_points_y), mf_points_static_text, fill=current_text_color, font=font_top_mfr)
            else:
                mf_points_only_text = f"MF Points: {numeric_points}"
                mf_points_only_y = current_y_for_points_block + (top_mfr_icon_size - font_top_mfr.size) // 2
                draw.text((right_column_x_start, mf_points_only_y), mf_points_only_text, fill=current_text_color, font=font_top_mfr)

            # Draw roles for animated card (using final_displayed_roles)
            current_tag_draw_x = right_column_x_start
            current_tag_draw_y = roles_y # This remains fixed for single line
            
            for tag_data in final_displayed_roles:
                tag_text = tag_data['name']
                category_dot_color = tag_data['color']
                
                text_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
                text_width = text_bbox[2] - text_bbox[0]
                
                tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)

                # Draw rounded rectangle background
                tag_rect = (current_tag_draw_x, current_tag_draw_y,
                            current_tag_draw_x + tag_width, current_tag_draw_y + tag_line_height)
                draw.rounded_rectangle(tag_rect, radius=tag_line_height // 2, fill=tag_bg_color)

                # Draw color dot
                dot_x = current_tag_draw_x + tag_horizontal_padding
                dot_y = current_tag_draw_y + (tag_line_height - dot_diameter) // 2
                draw.ellipse((dot_x, dot_y, dot_x + dot_diameter, dot_y + dot_diameter), fill=category_dot_color)

                # Draw tag text
                text_x = dot_x + dot_diameter + dot_right_margin
                text_y = current_tag_draw_y + tag_vertical_padding - 1 # Adjusted for visual centering
                draw.text((text_x, text_y), tag_text, fill=tag_text_color, font=font_tag)

                current_tag_draw_x += tag_width + tag_spacing_x

            if random_msg and message_box:
                # Ensure the message_box is pasted correctly, using the pre-calculated message_box variable
                frame.paste(message_box, (right_column_x_start, random_msg_y), message_box)

            dithered = frame.convert("P", palette=Image.ADAPTIVE, dither=Image.FLOYDSTEINBERG)
            frames.append(dithered)

        output = io.BytesIO()
        frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:], duration=frame_duration, loop=0)
        output.seek(0)
        return output, "gif"

    def wrap_text(self, text, font, max_width):
        wrapped_lines = []
        words = text.split()
        current_line = ""
        for word in words:
            # Check if a single word is longer than max_width, if so, break it down
            bbox_word = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), word, font=font)
            word_width = bbox_word[2] - bbox_word[0]
            
            if word_width > max_width:
                if current_line: # Add any existing partial line first
                    wrapped_lines.append(current_line.strip())
                    current_line = ""
                
                temp_word_part = ""
                for char_idx, char in enumerate(word):
                    test_temp_part = temp_word_part + char
                    temp_part_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), test_temp_part, font=font)
                    if (temp_part_bbox[2] - temp_part_bbox[0]) <= max_width:
                        temp_word_part += char
                    else:
                        wrapped_lines.append(temp_word_part)
                        temp_word_part = char # Start new part with current char
                if temp_word_part: # Add any remaining part of the word
                    wrapped_lines.append(temp_word_part)
            else: # Word fits normally
                test_line = current_line + word + " "
                test_bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), test_line, font=font)
                test_width = test_bbox[2] - test_bbox[0]
                if test_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped_lines.append(current_line.strip())
                    current_line = word + " " # Start new line with the current word
        if current_line.strip():
            wrapped_lines.append(current_line.strip())
        return wrapped_lines


    ALLOWED_ROLES = ["Admins", "Moderators", "Chat Moderators"]
    @app_commands.checks.has_any_role(*ALLOWED_ROLES)
    @mf_card_group.command(name="card", description="View a member's MF Card.")
    @app_commands.describe(member="The member whose MF Card you want to view (defaults to you).")
    async def view_mf_card(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        if member == None:
            member = interaction.user

        cog = self.bot.get_cog("MemberCards")
        if not cog:
            return await interaction.followup.send("MemberCards cog is not loaded. Please ensure it's loaded.", ephemeral=True)

        discord_username = member.display_name
        pfp_url = await cog.get_pfp(member)
        join_date = await cog.get_join_date(member)

        if isinstance(join_date, str):
            try:
                join_date = datetime.strptime(join_date, "%Y-%m-%d")
            except ValueError:
                join_date = datetime.now()

        rank_str = await cog.get_rank(member)

        is_top_feedback, numeric_points = False, 0
        try:
            is_top_feedback, numeric_points = await cog.get_points(member)
        except Exception as e:
            print(f"Error calling get_points for {member.display_name}: {e}")
            is_top_feedback = False
            numeric_points = 0

        # Retrieve ALL roles for each category - this is important for correct counting
        all_main_genres_roles, all_daw_roles, all_instruments_roles = await self.bot.get_cog("MemberCards").get_roles_by_colors(member)
        
        # Pass all roles for calculation in generate_card
        # No more 'roles_to_display' or 'extra_count' here, logic is fully in generate_card
        
        message_count = await cog.get_message_count(member)

        # --- IMPORTANT: Revert to dynamic fetching here ---
        random_msg_content = "" # Initialize with empty string
        random_msg_url = None   # Initialize with None

        try:
            retrieved_msg_data = await cog.get_random_message(member)
            if retrieved_msg_data and len(retrieved_msg_data) == 2:
                random_msg_content, random_msg_url = retrieved_msg_data
            else:
                # Set default "no message" content if fetching fails or returns unexpected data
                random_msg_content = "Couldn't find any random messages by **member** in the general chat. Maybe they haven't posted much, or not in a while!"
                # Consider if you want random_msg_url to be None in this case,
                # or a generic link, but None is usually safer to prevent a broken button.
                random_msg_url = None
        except Exception as e:
            print(f"Error fetching random message for {member.display_name}: {e}")
            random_msg_content = "An unexpected error occurred while looking for a message."
            random_msg_url = None
        # --- End dynamic fetching block ---

        last_music = await cog.get_last_finished_music(member)
        server_name = interaction.guild.name if interaction.guild else "Direct Message"

        release_link = None
        if last_music and (last_music.startswith("http://") or last_music.startswith("https://")):
            release_link = last_music

        img_width, img_height = 600, 300

        async with aiohttp.ClientSession() as session:
            async with session.get(pfp_url) as resp:
                if resp.status != 200:
                    print(f"Failed to fetch PFP for {member.display_name}. Status: {resp.status}")
                    pfp = Image.new("RGBA", (120, 120), (100, 100, 100, 255))
                else:
                    pfp_data = io.BytesIO(await resp.read())
                    pfp = Image.open(pfp_data).convert("RGBA").resize((120, 120), Image.Resampling.LANCZOS)

        mask = Image.new('L', pfp.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, *pfp.size), fill=255)
        pfp.putalpha(mask)

        animated = True

        card_buffer, file_ext = self.generate_card(
            pfp, discord_username, server_name, rank_str, numeric_points, message_count, join_date,
            (img_width, img_height), self.font_path, animated=animated, random_msg=random_msg_content,
            is_top_feedback=is_top_feedback,
            all_genres_roles=all_main_genres_roles, # Pass all roles
            all_daws_roles=all_daw_roles,
            all_instruments_roles=all_instruments_roles
        )

        filename = f"{discord_username}_mf_card.{file_ext}"
        file = discord.File(card_buffer, filename=filename)

        view = discord.ui.View()
        if release_link:
            view.add_item(discord.ui.Button(label=f"{discord_username}'s Latest Release", style=discord.ButtonStyle.link, url=release_link))
        # This condition is already good: the button will only show if random_msg_url is not None
        # and random_msg_content is not one of the default error messages.
        if random_msg_url and random_msg_content not in ["Couldn't find any random messages by **member** in the general chat. Maybe they haven't posted much, or not in a while!", "I don't have permission to look through message history in that channel.", "Something went wrong trying to fetch message history. Please try again later!", "An unexpected error occurred while looking for a message."]:
             view.add_item(discord.ui.Button(label=emoji.emojize(":rocket:"), style=discord.ButtonStyle.link, url=random_msg_url))


        await interaction.followup.send(file=file, view=view)

async def setup(bot):
    await bot.add_cog(GetMemberCard(bot))