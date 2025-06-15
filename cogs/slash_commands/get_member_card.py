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
        self.font_path = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/BebasNeue-Regular.ttf"
        self.italic_font_path = None
        self.background_images_dir = "/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/images/"

        self.background_map = {
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

    def generate_card(self, pfp_image_pil, discord_username, server_name, rank_str, numeric_points, message_count, join_date, card_size, font_path, animated=True, random_msg="", is_top_feedback=False):
        frames = []
        num_frames = 100  # 100 frames for slower fading (~7.5s per loop)
        frame_duration = 75  # 75ms per frame

        font_username = ImageFont.truetype(font_path, 30)
        font_date_label = ImageFont.truetype(font_path, 20)
        font_date_value = ImageFont.truetype(font_path, 25)
        font_points_messages = ImageFont.truetype(font_path, 25)
        font_rank_blinking = ImageFont.truetype(font_path, 55)
        font_top_mfr = ImageFont.truetype(font_path, 30)
        font_random_msg = ImageFont.truetype(self.italic_font_path or font_path, 18)

        card_width, card_height = card_size

        # Load the banner (keeping original 800x40px dimensions) and crop 5px from top and bottom
        banner = Image.open("/Users/doll/Desktop/programming/MFbot/MFbot/Music-Feedback-Bot/media/Bebas_Neue/images/banner.png").convert("RGBA")  # Original 800x40px
        banner = banner.crop((0, 5, 800, 35))  # Crop: (left, top, right, bottom) - removes 5px top and 5px bottom
        banner_width, banner_height = banner.size
        amplitude = 50  # Reduced amplitude for less dramatic movement
        center_x = (card_width // 2) - (banner_width // 2)  # Center the banner (-100px to align 400px with 300px center)

        # Custom fading background for Artist of the Week
        if rank_str == "Artist of the Week" and animated:
            base_card_content = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            # New sequence: White -> Color1 -> Color2 -> White
            flash_colors = [
                (255, 255, 255),  # White
                self._hex_to_rgb("d585eb"),  # Color 1
                self._hex_to_rgb("3bc4ed"),  # Color 2
                (255, 255, 255)   # Back to White
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

        # Shift all elements down by 15px
        pfp_x, pfp_y = 50, 65  # Increased from 50 to 65
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
        rank_y = pfp_y + 10
        top_mfr_icon_size = 30
        top_mfr_text_padding = 8
        top_mfr_block_y = rank_y + font_rank_blinking.size + 10

        if is_top_feedback:
            top_mfr_content_height = max(top_mfr_icon_size, font_top_mfr.size)
            random_msg_y = top_mfr_block_y + top_mfr_content_height + 20
        else:
            random_msg_y = top_mfr_block_y + font_top_mfr.size + 20

        message_box_width = card_width - right_column_x_start - 30
        max_message_lines = 3

        static_card_base = base_card_content.copy()
        static_draw = ImageDraw.Draw(static_card_base)

        # These elements should always be drawn, regardless of animation or rank
        # Calculate text positions once
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
            message_box_draw.rounded_rectangle((0, 0, message_box_width, current_message_box_height), fill=(0, 0, 0, 200), radius=50)
            message_text_y = message_box_padding
            for line in wrapped_message:
                message_text_bbox = message_box_draw.textbbox((0, 0), line, font=font_random_msg)
                message_text_x = (message_box_width - (message_text_bbox[2] - message_text_bbox[0])) // 2
                message_box_draw.text((message_text_x, message_text_y), line, fill=(255, 255, 255), font=font_random_msg)
                message_text_y += font_random_msg.size

        target_hex_color = self.rank_blink_colors.get(rank_str, "#808080")
        rank_color_end = self._hex_to_rgb(target_hex_color)
        rank_color_start = (0, 0, 0) # This will be (0,0,0) for non-AOTW, or used in the pulse for AOTW

        if not animated: # For static PNG cards
            output = io.BytesIO()
            static_draw.text((right_column_x_start, rank_y), f"{rank_str}", fill=rank_color_end, font=font_rank_blinking)
            static_draw.text((username_x_aligned, username_y), discord_username, fill=(0, 0, 0), font=font_username)
            static_draw.text((label_x_aligned, member_since_label_y), joined_label, fill=(0, 0, 0), font=font_date_label)
            static_draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=(0, 0, 0), font=font_date_value)
            if is_top_feedback:
                top_mfr_static_color = (59, 196, 237)
                top_mfr_text_end_x, top_mfr_text_y = self._draw_top_mfr_badge(static_draw, top_mfr_block_y, right_column_x_start, font_top_mfr, top_mfr_icon_size, top_mfr_text_padding, top_mfr_static_color)
                mf_points_static_text = f" - MF Points: {numeric_points}"
                mf_points_x = top_mfr_text_end_x + 5
                mf_points_y = top_mfr_text_y
                static_draw.text((mf_points_x, mf_points_y), mf_points_static_text, fill=(0, 0, 0), font=font_top_mfr)
            else:
                mf_points_only_text = f"MF Points: {numeric_points}"
                mf_points_only_y = top_mfr_block_y + (top_mfr_icon_size - font_top_mfr.size) // 2
                static_draw.text((right_column_x_start, mf_points_only_y), mf_points_only_text, fill=(0, 0, 0), font=font_top_mfr)
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

        # Create gradient for shiny effect (transparent-white-transparent)
        gradient_width = int(math.sqrt(card_width**2 + card_height**2)) * 2  # Diagonal length
        gradient_height = 100  # Width of the flash band
        gradient = Image.new("RGBA", (gradient_width, gradient_height), (0, 0, 0, 0))
        gradient_draw = ImageDraw.Draw(gradient)
        for x in range(gradient_width):
            alpha = 0
            if x > gradient_width // 3 and x < 2 * gradient_width // 3:
                alpha = int(128 * math.sin(math.pi * (x - gradient_width // 3) / (gradient_width // 3)))  # Peak at 128
            gradient_draw.line((x, 0, x, gradient_height), fill=(255, 255, 255, alpha))
        gradient = gradient.rotate(45, expand=True)

        # Animation loop
        for i in range(num_frames):
            frame = static_card_base.copy()
            draw = ImageDraw.Draw(frame)
            pulse_progress = (math.sin(2 * math.pi * i / num_frames) + 1) / 2
            current_rank_pulse_color = (
                int(rank_color_start[0] + (rank_color_end[0] - rank_color_start[0]) * pulse_progress),
                int(rank_color_start[1] + (rank_color_end[1] - rank_color_start[1]) * pulse_progress),
                int(rank_color_start[2] + (rank_color_end[2] - rank_color_start[2]) * pulse_progress)
            )

            # Custom fading background for Artist of the Week
            if rank_str == "Artist of the Week" and animated:
                # Calculate the segment of the animation we are in
                segment_length = num_frames / (len(flash_colors) - 1)
                segment_index = int(i / segment_length)
                
                # Ensure segment_index does not exceed valid indices
                if segment_index >= len(flash_colors) - 1:
                    segment_index = len(flash_colors) - 2 

                # Calculate progress within the current segment
                segment_progress = (i % segment_length) / segment_length

                color1 = flash_colors[segment_index]
                color2 = flash_colors[segment_index + 1]

                current_color = (
                    int(color1[0] + (color2[0] - color1[0]) * segment_progress),
                    int(color1[1] + (color2[1] - color1[1]) * segment_progress),
                    int(color1[2] + (color2[2] - color1[2]) * segment_progress)
                )
                draw.rectangle((0, 0, card_width, card_height), fill=current_color)

                # Dynamically determine text color based on background brightness for AOTW
                brightness = sum(current_color) / 3  # Average of RGB
                text_color_dynamic = (0, 0, 0) if brightness > 128 else (255, 255, 255)
                draw.text((username_x_aligned, username_y), discord_username, fill=text_color_dynamic, font=font_username)
                draw.text((label_x_aligned, member_since_label_y), joined_label, fill=text_color_dynamic, font=font_date_label)
                draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=text_color_dynamic, font=font_date_value)
                if random_msg:
                    frame.paste(message_box, (right_column_x_start, random_msg_y), message_box)
            else: # For all other ranks (non-AOTW animated cards)
                # Set a default text color for non-AOTW cards
                default_text_color = (0, 0, 0) # Black for better contrast on typical backgrounds
                draw.text((username_x_aligned, username_y), discord_username, fill=default_text_color, font=font_username)
                draw.text((label_x_aligned, member_since_label_y), joined_label, fill=default_text_color, font=font_date_label)
                draw.text((date_value_x_aligned, join_date_value_y), joined_date_str, fill=default_text_color, font=font_date_value)
                if random_msg:
                    frame.paste(message_box, (right_column_x_start, random_msg_y), message_box)


            # Animate the banner with centered and reduced movement, shifted down 15px
            progress = i / num_frames  # 0 to 1 over the cycle
            x_offset = int(amplitude * math.sin(2 * math.pi * progress))  # Oscillate within 50px range
            x = center_x + x_offset  # Adjust position based on center
            # Crop to card width (600px) by pasting only the visible portion
            visible_banner = banner.crop((max(0, -x), 0, min(banner_width, card_width - x), banner_height))
            frame.paste(visible_banner, (max(0, x), 15), visible_banner)  # Shift down by 15px

            # Shiny effect for "MF Gilded" and "The Real MFrs"
            if rank_str in ["MF Gilded", "The Real MFrs"]:
                total_cycle_frames = int(60 / (frame_duration / 1000))  # 15s in frames
                cycle_frame = (i * 2) % (total_cycle_frames // num_frames * num_frames)  # Slow down flash cycle
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
                current_top_mfr_pulse_color = (
                    int(top_mfr_color_start[0] + (top_mfr_color_end[0] - top_mfr_color_start[0]) * pulse_progress),
                    int(top_mfr_color_start[1] + (top_mfr_color_end[1] - top_mfr_color_start[1]) * pulse_progress),
                    int(top_mfr_color_start[2] + (top_mfr_color_end[2] - top_mfr_color_start[2]) * pulse_progress)
                )
                top_mfr_text_end_x, top_mfr_text_y = self._draw_top_mfr_badge(draw, top_mfr_block_y, right_column_x_start, font_top_mfr, top_mfr_icon_size, top_mfr_text_padding, current_top_mfr_pulse_color)
                mf_points_static_text = f" - MF Points: {numeric_points}"
                mf_points_x = top_mfr_text_end_x + 5
                mf_points_y = top_mfr_text_y
                draw.text((mf_points_x, mf_points_y), mf_points_static_text, fill=(0, 0, 0), font=font_top_mfr)
            else:
                mf_points_only_text = f"MF Points: {numeric_points}"
                mf_points_only_y = top_mfr_block_y + (top_mfr_icon_size - font_top_mfr.size) // 2
                draw.text((right_column_x_start, mf_points_only_y), mf_points_only_text, fill=(0, 0, 0), font=font_top_mfr)

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
            is_top_feedback=is_top_feedback
        )
        filename = f"{discord_username}_mf_card.{file_ext}"
        file = discord.File(card_buffer, filename=filename)
        view = discord.ui.View()
        if release_link:
            view.add_item(discord.ui.Button(label=f"{discord_username}'s Latest Release", style=discord.ButtonStyle.link, url=release_link))
        await interaction.followup.send(file=file, view=view)

async def setup(bot):
    await bot.add_cog(GetMemberCard(bot))