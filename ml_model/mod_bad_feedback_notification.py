import discord
import logging
from data.constants import MODERATORS_CHANNEL_ID, AUDIO_FEEDBACK, CO_DEV_ID, FEEDBACK_ACCESS_CHANNEL_ID

logger = logging.getLogger(__name__)


class _BadFeedbackView(discord.ui.View):
    """Moderator action buttons for a bad-feedback alert."""

    def __init__(self, bot, message, feedback_text, log_callback):
        super().__init__(timeout=300)
        self.bot = bot
        self.message = message
        self.feedback_text = feedback_text
        self.log_callback = log_callback
        self.handled = False

    async def _mark_done(self, interaction: discord.Interaction, label: str):
        self.handled = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"[{label}]", view=self)
        self.stop()

    @discord.ui.button(label="✅ Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.info("Moderator %s dismissed bad feedback alert", interaction.user.name)
        if self.log_callback:
            await self.log_callback(f"✅ Bad feedback alert dismissed by {interaction.user.name}")
        await self._mark_done(interaction, "Dismissed")

    @discord.ui.button(label="❌ Notify User", style=discord.ButtonStyle.danger)
    async def notify_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        audio_feedback_channel = self.bot.get_channel(AUDIO_FEEDBACK)
        if audio_feedback_channel:
            await audio_feedback_channel.send(
                f"{self.message.author.mention} Please provide more detailed and constructive feedback. "
                f"Check out <#{FEEDBACK_ACCESS_CHANNEL_ID}> if you need help.",
                allowed_mentions=discord.AllowedMentions(users=True)
            )
            logger.info("User %s notified about bad feedback", self.message.author.name)
            if self.log_callback:
                await self.log_callback(f"✅ User {self.message.author.name} notified to improve feedback")
        else:
            logger.error("Could not find audio feedback channel %s", AUDIO_FEEDBACK)
            if self.log_callback:
                await self.log_callback(f"❌ Audio feedback channel {AUDIO_FEEDBACK} not found")
        await self._mark_done(interaction, "User Notified")

    async def on_timeout(self):
        self.handled = True
        logger.info("Bad feedback alert timed out")
        if self.log_callback:
            await self.log_callback("⏱️ Bad feedback alert timed out with no moderator action")


class FeedbackNotifier:
    """Handles notifications for feedback quality issues"""

    def __init__(self, bot):
        self.bot = bot

    async def notify_bad_feedback(self, message, feedback_text, log_callback=None):
        """
        Send notification to moderators about bad feedback.

        Args:
            message: The original Discord message containing the feedback
            feedback_text: The extracted feedback text
            log_callback: Optional async function for logging (takes message and optional error)
        """
        try:
            mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

            if not mod_channel:
                error_msg = f"❌ Moderators channel {MODERATORS_CHANNEL_ID} not found for bad feedback notification"
                logger.error(error_msg)
                if log_callback:
                    await log_callback(error_msg)
                return False

            # Truncate feedback preview
            feedback_preview = feedback_text[:200]
            if len(feedback_text) > 200:
                feedback_preview += "..."

            view = _BadFeedbackView(self.bot, message, feedback_text, log_callback)

            await mod_channel.send(
                f"⚠️ <@{CO_DEV_ID}> Bad feedback detected from {message.author.mention} in {message.channel.mention}:\n"
                f"```{feedback_preview}```\n"
                f"[Jump to message]({message.jump_url})",
                view=view,
                allowed_mentions=discord.AllowedMentions(users=True)
            )

            logger.info("Bad feedback notification sent to moderators")
            if log_callback:
                await log_callback(f"✅ Bad feedback notification sent for message {message.id}")

            return True

        except Exception:
            logger.error("Error sending bad feedback notification", exc_info=True)
            if log_callback:
                await log_callback("❌ Error sending bad feedback notification")
            return False

    async def send_prediction_result(
        self,
        message: discord.Message,
        result: dict,
        feedback_text: str,
    ) -> discord.Message | None:
        """
        Builds the prediction embed, sends it to DEV_SPAM, adds reactions.
        Returns the sent mod_message (used by FeedbackMonitor to track pending validation),
        or None if the send fails.
        """
        from data.constants import DEV_SPAM, CO_DEV_ID

        dev_spam = self.bot.get_channel(DEV_SPAM)
        if not dev_spam:
            logger.error("send_prediction_result: DEV_SPAM channel %s not found", DEV_SPAM)
            return None

        feedback_preview = feedback_text[:500] + ("..." if len(feedback_text) > 500 else "")
        embed = discord.Embed(
            title="🤖 Feedback Quality Check",
            description=f"**Prediction:** {result['prediction']}",
            color=discord.Color.green() if result['is_good'] else discord.Color.red()
        )
        embed.add_field(name="Feedback Content", value=f"```{feedback_preview}```", inline=False)
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Confidence", value=f"{result['probability']:.1%}", inline=True)
        embed.add_field(name="Original Message", value=f"[Jump to message]({message.jump_url})", inline=False)
        embed.set_footer(text=f"Message ID: {message.id}")
        embed.timestamp = message.created_at

        try:
            mod_message = await dev_spam.send(
                content=f"<@{CO_DEV_ID}> New feedback!",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True)
            )
        except Exception:
            logger.error("send_prediction_result: failed to send embed to DEV_SPAM", exc_info=True)
            return None

        try:
            await mod_message.add_reaction("✅")
            await mod_message.add_reaction("❌")
        except Exception:
            logger.warning("send_prediction_result: failed to add reactions (non-critical)")

        return mod_message
