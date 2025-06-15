import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont, ImageSequence, ImageFilter, ImageOps
import io
import aiohttp
import os
import traceback
import math
from datetime import datetime

class GetMemberCard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Ensure these paths are correct for your environment
        self.font_path = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/BebasNeue-Regular.ttf"
        self.italic_font_path = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/BebasNeue-Italic.ttf" # Assuming you have an italic font
        self.background_images_dir = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/images/"

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
        if self.italic_font_path and not os.path.exists(self.italic_font_path):
            print(f"WARNING: Italic font file not found: {self.italic_font_path}. Random messages will not be italic.")
            self.italic_font_path = None

        try:
            _ = ImageFont.truetype(self.font_path, 10)
            if self.italic_font_path:
                _ = ImageFont.truetype(self.italic_font_path, 10)
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
        font_username = ImageFont.truetype(font_path, 30)
        font_date_label = ImageFont.truetype(font_path, 20)
        font_date_value = ImageFont.truetype(font_path, 25)
        font_rank_blinking = ImageFont.truetype(font_path, 55)
        font_top_mfr = ImageFont.truetype(font_path, 30)
        font_random_msg = ImageFont.truetype(self.italic_font_path or font_path, 18)
        font_tag = ImageFont.truetype(font_path, 12) # Adjusted font for individual tags
        # font_extra_roles removed as it's no longer needed

        # Define icon and text padding sizes used in badge drawing and layout
        top_mfr_icon_size = 30
        top_mfr_text_padding = 8
        # --- End Font and Size Definitions ---

        # Retrieve roles data from kwargs
        genres_to_display = kwargs.get("genres_to_display", [])
        genres_extra_count = kwargs.get("genres_extra_count", 0)
        daws_to_display = kwargs.get("daws_to_display", [])
        daws_extra_count = kwargs.get("daws_extra_count", 0)
        instruments_to_display = kwargs.get("instruments_to_display", [])
        instruments_extra_count = kwargs.get("instruments_extra_count", 0)

        tag_text_color = (255, 255, 255) # White text for dark tags

        # Tag dimensions and spacing (ADJUSTED for smaller and closer)
        tag_horizontal_padding = 8 # Padding inside tag, around text and dot
        tag_vertical_padding = 4   # Vertical padding inside tag
        dot_diameter = 7 # Size of the color dot
        dot_right_margin = 4 # Space between dot and text
        tag_spacing_x = 5 # Space between tags horizontally
        tag_spacing_y = 4 # Space between lines of tags vertically
        tag_line_height = font_tag.size + (2 * tag_vertical_padding)

        card_width, card_height = card_size

        banner = Image.open("/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/images/banner.png").convert("RGBA")
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
                    background_filename = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/images/moderators.png"
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
        border_color = (255, 215, 0, 255) if rank_str in ["MF Gilded", "The Real MFrs"] else (0, 0, 0, 255)

        border_bbox_x1 = pfp_x - border_thickness
        border_bbox_y1 = pfp_y - border_thickness
        border_bbox_x2 = pfp_x + pfp_diameter + border_thickness
        border_bbox_y2 = pfp_y + pfp_diameter + border_thickness

        current_left_y = pfp_y + pfp_diameter + 10
        username_y = current_left_y
        current_left_y += font_username.size + 5
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
        roles_y = bottom_of_points_block_y + 10 # Add padding after roles block

        message_box_width = card_width - right_column_x_start - 30 # Available width for tags and random message
        tag_bg_color = (40, 40, 40, 200) # Semi-transparent dark grey for tag background

        role_categories = [
            (genres_to_display, genres_extra_count, self._hex_to_rgb("#8d8c8c")), # TARGET_MAIN_GENRES RGB
            (daws_to_display, daws_extra_count, self._hex_to_rgb("#6155a6")),    # TARGET_DAW RGB
            (instruments_to_display, instruments_extra_count, self._hex_to_rgb("#e3abff")) # TARGET_INSTRUMENTS RGB
        ]
        
        # Combine all roles into a single list for continuous flow
        all_roles_combined = []
        total_extra_roles_count = 0 

        for roles_list, extra_count, category_dot_color in role_categories:
            for role_name in roles_list: # roles_list already contains only the first 2
                all_roles_combined.append({'name': role_name, 'color': category_dot_color})
            total_extra_roles_count += extra_count # Accumulate extra count

        # Add the combined "+x" tag if there are extra roles
        if total_extra_roles_count > 0:
            neutral_extra_color = (128, 128, 128) # Grey for the +x dot
            all_roles_combined.append({'name': f"+{total_extra_roles_count}", 'color': neutral_extra_color})


        # Calculate height of the roles block by performing a dry run of tag layout
        roles_block_height = 0
        current_tag_x_dry_run = right_column_x_start
        current_tag_y_offset_dry_run = 0
        
        for tag_data in all_roles_combined:
            tag_text = tag_data['name']
            
            temp_draw = ImageDraw.Draw(Image.new("RGB", (1, 1))) # Dummy draw object
            text_bbox = temp_draw.textbbox((0, 0), tag_text, font=font_tag)
            text_width = text_bbox[2] - text_bbox[0]
            
            tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)

            if current_tag_x_dry_run + tag_width > right_column_x_start + message_box_width:
                current_tag_x_dry_run = right_column_x_start
                current_tag_y_offset_dry_run += tag_line_height + tag_spacing_y
            
            current_tag_x_dry_run += tag_width + tag_spacing_x
            
        # Adjust roles_block_height if no tags were drawn
        if not all_roles_combined:
            roles_block_height = 0
        else:
            # The last line height and spacing were added. Subtract if only one line, or if the last item caused a wrap.
            roles_block_height = current_tag_y_offset_dry_run + tag_line_height # Add the height of the last line


        # Random message box starts below the roles block
        random_msg_y = roles_y + roles_block_height + 10 # Add padding after roles block


        max_message_lines = 3

        static_card_base = base_card_content.copy()
        static_draw = ImageDraw.Draw(static_card_base)

        username_bbox = static_draw.textbbox((0, 0), discord_username, font=font_username)
        username_center_x = pfp_x + (pfp_diameter // 2)
        username_x_aligned = username_center_x - ((username_bbox[2] - username_bbox[0]) // 2)

        joined_label = "MEMBER SINCE:"
        joined_date_str = join_date.strftime('%B %d, %Y')
        label_bbox = static_draw.textbbox((0,0), joined_label, font=font_date_label)
        label_x_aligned = username_center_x - ((label_bbox[2] - label_bbox[0]) // 2)
        date_value_bbox = static_draw.textbbox((0,0), joined_date_str, font=font_date_value)
        date_value_x_aligned = username_center_x - ((date_value_bbox[2] - date_value_bbox[0]) // 2)

        if random_msg:
            message_box_padding = 10
            wrapped_message = self.wrap_text(random_msg, font_random_msg, message_box_width - (2 * message_box_padding))
            if len(wrapped_message) > max_message_lines:
                wrapped_message = wrapped_message[:max_message_lines - 1]
                wrapped_message.append("...")
            current_message_box_height = len(wrapped_message) * font_random_msg.size + (2 * message_box_padding)
            message_box = Image.new("RGBA", (message_box_width, current_message_box_height), (0, 0, 0, 200))
            message_box_draw = ImageDraw.Draw(message_box)
            message_box_draw.rounded_rectangle((0, 0, message_box_width, current_message_box_height), fill=(0, 0, 0, 200), radius=10)
            message_text_y = message_box_padding
            for line in wrapped_message:
                message_text_bbox = message_box_draw.textbbox((0, 0), line, font=font_random_msg)
                message_text_x = (message_box_width - (message_text_bbox[2] - message_text_bbox[0])) // 2
                message_box_draw.text((message_text_x, message_text_y), line, fill=(255, 255, 255), font=font_random_msg)
                message_text_y += font_random_msg.size

        target_hex_color = self.rank_blink_colors.get(rank_str, "#808080")
        rank_color_end = self._hex_to_rgb(target_hex_color)
        rank_color_start = (0, 0, 0)

        base_text_color = (255, 255, 255) if rank_str in inverted_text_roles else (0, 0, 0)

        if not animated:
            output = io.BytesIO()
            static_draw.text((right_column_x_start, rank_y), f"{rank_str}", fill=rank_color_end, font=font_rank_blinking)
            static_draw.text((username_x_aligned, username_y), discord_username, fill=base_text_color, font=font_username)
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

            # Draw roles for static card (using combined roles)
            current_tag_draw_x = right_column_x_start
            current_tag_draw_y = roles_y
            
            for tag_data in all_roles_combined:
                tag_text = tag_data['name']
                category_dot_color = tag_data['color']
                
                text_bbox = static_draw.textbbox((0, 0), tag_text, font=font_tag)
                text_width = text_bbox[2] - text_bbox[0]
                
                tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)

                # Check for line wrap
                if current_tag_draw_x + tag_width > right_column_x_start + message_box_width:
                    current_tag_draw_x = right_column_x_start
                    current_tag_draw_y += tag_line_height + tag_spacing_y

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

            if random_msg:
                static_card_base.paste(message_box, (right_column_x_start, random_msg_y), message_box)
            static_card_base.save(output, format="PNG")
            output.seek(0)
            return output, "png"

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
            frame = static_card_base.copy()
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

                brightness = sum(current_color) / 3
                current_text_color = (0, 0, 0) if brightness > 128 else (255, 255, 255)

            draw.text((username_x_aligned, username_y), discord_username, fill=current_text_color, font=font_username)
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

            # Draw roles for animated card (using combined roles)
            current_tag_draw_x = right_column_x_start
            current_tag_draw_y = roles_y
            
            for tag_data in all_roles_combined:
                tag_text = tag_data['name']
                category_dot_color = tag_data['color']
                
                text_bbox = draw.textbbox((0, 0), tag_text, font=font_tag)
                text_width = text_bbox[2] - text_bbox[0]
                
                tag_width = dot_diameter + dot_right_margin + text_width + (2 * tag_horizontal_padding)

                # Check for line wrap
                if current_tag_draw_x + tag_width > right_column_x_start + message_box_width:
                    current_tag_draw_x = right_column_x_start
                    current_tag_draw_y += tag_line_height + tag_spacing_y

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


            if random_msg:
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
            bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            if word_width > max_width:
                if current_line:
                    wrapped_lines.append(current_line.strip())
                    current_line = ""
                temp_word = ""
                for char in word:
                    test_temp = temp_word + char
                    temp_bbox = ImageDraw.Draw(Image.new("RGB", (1,1))).textbbox((0,0), test_temp, font=font)
                    if (temp_bbox[2] - temp_bbox[0]) <= max_width:
                        temp_word += char
                    else:
                        wrapped_lines.append(temp_word)
                        temp_word = char
                if temp_word:
                    wrapped_lines.append(temp_word)
            else:
                test_line = current_line + word + " "
                test_bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), test_line, font=font)
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

    @mf_card_group.command(name="card", description="View a member's MF Card.")
    @app_commands.describe(member="The member whose MF Card you want to view (defaults to you).")
    async def view_mf_card(self, interaction: discord.Interaction, member: discord.Member = None):
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

        # Retrieve all roles for each category
        all_main_genres_roles, all_daw_roles, all_instruments_roles = await self.bot.get_cog("MemberCards").get_roles_by_colors(member)
        
        # Prepare roles to display and count of extra roles
        # Only allow 2 of each in each division
        genres_to_display = all_main_genres_roles[:2]
        genres_extra_count = max(0, len(all_main_genres_roles) - 2)

        daws_to_display = all_daw_roles[:2]
        daws_extra_count = max(0, len(all_daw_roles) - 2)

        instruments_to_display = all_instruments_roles[:2]
        instruments_extra_count = max(0, len(all_instruments_roles) - 2)

        message_count = await cog.get_message_count(member)

        random_msg_content = ""
        random_msg_url = None
        try:
            retrieved_msg_data = await cog.get_random_message(member)
            if retrieved_msg_data and len(retrieved_msg_data) == 2:
                random_msg_content, random_msg_url = retrieved_msg_data
        except Exception as e:
            print(f"Error calling get_random_message for {member.display_name}: {e}")
            random_msg_content = ""
            random_msg_url = None

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
            genres_to_display=genres_to_display, genres_extra_count=genres_extra_count,
            daws_to_display=daws_to_display, daws_extra_count=daws_extra_count,
            instruments_to_display=instruments_to_display, instruments_extra_count=instruments_extra_count
        )

        filename = f"{discord_username}_mf_card.{file_ext}"
        file = discord.File(card_buffer, filename=filename)

        view = discord.ui.View()
        if release_link:
            view.add_item(discord.ui.Button(label=f"{discord_username}'s Latest Release", style=discord.ButtonStyle.link, url=release_link))

        await interaction.followup.send(file=file, view=view)

async def setup(bot):
    await bot.add_cog(GetMemberCard(bot))