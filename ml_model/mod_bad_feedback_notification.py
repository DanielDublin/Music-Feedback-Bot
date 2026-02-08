import discord
from data.constants import MODERATORS_CHANNEL_ID, AUDIO_FEEDBACK
import asyncio


class FeedbackNotifier:
    """Handles notifications for feedback quality issues"""
    
    def __init__(self, bot):
        self.bot = bot
        # my ID
        self.moderator_user_id = 412733389196623879
    
    async def notify_bad_feedback(self, message, feedback_text, log_callback=None):
        """
        Send notification to moderators about bad feedback
        
        Args:
            message: The original Discord message containing the feedback
            feedback_text: The extracted feedback text
            log_callback: Optional async function for logging (takes message and optional error)
        """
        try:
            mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)
            
            if not mod_channel:
                error_msg = f"❌ Moderators channel {MODERATORS_CHANNEL_ID} not found for bad feedback notification"
                print(error_msg)
                if log_callback:
                    await log_callback(error_msg)
                return False
            
            # Truncate feedback preview
            feedback_preview = feedback_text[:200]
            if len(feedback_text) > 200:
                feedback_preview += "..."
            
            # Send notification with user mention
            notification_message = await mod_channel.send(
                f"⚠️ <@{self.moderator_user_id}> Bad feedback detected from {message.author.mention} in {message.channel.mention}:\n"
                f"```{feedback_preview}```\n"
                f"[Jump to message]({message.jump_url})",
                allowed_mentions=discord.AllowedMentions(users=True)
            )

            # Add reaction buttons
            await notification_message.add_reaction("✅")
            await notification_message.add_reaction("❌")
            
            print("✅ Bad feedback notification sent to moderators")
            if log_callback:
                await log_callback(f"✅ Bad feedback notification sent for message {message.id}")
            
            # Wait for moderator reaction (5 minutes timeout)
            def check(reaction, user):
                return (
                    reaction.message.id == notification_message.id and
                    user.id == self.moderator_user_id and
                    str(reaction.emoji) in ["✅", "❌"]
                )
            
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    timeout=300.0,  # 5 minutes
                    check=check
                )
                
                # If moderator reacted with ❌, notify the user
                if str(reaction.emoji) == "❌":
                    audio_feedback_channel = self.bot.get_channel(AUDIO_FEEDBACK)
                    
                    if audio_feedback_channel:
                        await audio_feedback_channel.send(
                            f"{message.author.mention} Please provide more detailed and constructive feedback. Check out <#959150439692128277> if you need help.",
                            allowed_mentions=discord.AllowedMentions(users=True)
                        )
                        
                        print(f"✅ User {message.author.name} notified about bad feedback")
                        if log_callback:
                            await log_callback(f"✅ User {message.author.name} notified to improve feedback")
                    else:
                        print(f"❌ Could not find audio feedback channel {AUDIO_FEEDBACK}")
                        if log_callback:
                            await log_callback(f"❌ Audio feedback channel {AUDIO_FEEDBACK} not found")
                
                # If ✅, do nothing (moderator dismissed the alert)
                elif str(reaction.emoji) == "✅":
                    print(f"✅ Moderator dismissed bad feedback alert")
                    if log_callback:
                        await log_callback(f"✅ Bad feedback alert dismissed by moderator")
                        
            except asyncio.TimeoutError:
                # No reaction within 5 minutes, do nothing
                print(f"⏱️ No moderator reaction within 5 minutes for message {message.id}")
                if log_callback:
                    await log_callback(f"⏱️ No moderator reaction within 5 minutes for message {message.id}")
            
            return True
            
        except Exception as e:
            error_msg = f"❌ Error sending bad feedback notification: {e}"
            print(error_msg)
            if log_callback:
                await log_callback("❌ Error sending bad feedback notification", e)
            return False