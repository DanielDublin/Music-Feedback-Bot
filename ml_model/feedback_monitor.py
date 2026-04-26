"""
Feedback Quality Monitor Cog
Monitors messages in the feedback channel and validates feedback quality
"""

import discord
import logging
from dataclasses import dataclass
from discord.ext import commands, tasks
from ml_model.ml_model_loader import predict_feedback_quality
from data.constants import AUDIO_FEEDBACK, FEEDBACK_CHANNEL_ID, MODERATORS_CHANNEL_ID, DEV_SPAM
from ml_model.export_json import ExportJson
from ml_model.mod_bad_feedback_notification import FeedbackNotifier
import asyncio
import json
from datetime import timezone, timedelta


@dataclass
class PendingValidation:
    original_message: discord.Message
    feedback_text: str
    prediction: dict
    mod_message_id: int
    validated: bool = False

logger = logging.getLogger(__name__)


def _log_task_error(task: asyncio.Task):
    """Callback to log unhandled exceptions from background tasks."""
    if not task.cancelled() and task.exception():
        logger.error("Background task error: %r", task.exception())


class FeedbackMonitor(commands.Cog):
    """Monitors and validates feedback quality"""

    def __init__(self, bot):
        self.bot = bot
        self.pending_validations = {}
        self.listener_active = True
        self.notifier = FeedbackNotifier(bot)

    @tasks.loop(hours=24, reconnect=True)
    async def cleanup_pending_validations(self):
        """Remove entries older than 48 hours to prevent unbounded growth"""
        cutoff = discord.utils.utcnow() - timedelta(hours=48)
        stale = [
            mid for mid, data in self.pending_validations.items()
            if data.original_message.created_at.replace(tzinfo=timezone.utc) < cutoff
        ]
        for mid in stale:
            self.pending_validations.pop(mid, None)
        if stale:
            logger.debug("Cleaned up %d stale pending validations", len(stale))

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            if not self.cleanup_pending_validations.is_running():
                self.cleanup_pending_validations.start()
            logger.info(
                "FeedbackMonitor started — monitoring: %s, results to: %s, listener active: %s",
                AUDIO_FEEDBACK, DEV_SPAM, self.listener_active
            )
        except Exception:
            logger.error("Error in on_ready", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages in the feedback channel that start with <MFR"""

        try:
            if not self.listener_active:
                logger.warning("on_message called but listener is marked inactive")
                return

            if message.author.bot:
                return

            if message.channel.id != AUDIO_FEEDBACK:
                return

            content_lower = message.content.strip().lower()
            if not content_lower.startswith('<mfr'):
                return

            logger.info("Processing feedback from %s (ID: %s)", message.author.name, message.author.id)

            feedback_text = message.content.strip()[4:].strip()

            if not feedback_text:
                logger.warning("Empty feedback text from %s", message.author.name)
                return

            logger.debug("Processing feedback from %s", message.author.name)

            try:
                result = await predict_feedback_quality(feedback_text)

                if result is None:
                    logger.error("predict_feedback_quality returned None for message %s", message.id)
                    return

                if not isinstance(result, dict) or 'prediction' not in result:
                    logger.error("Invalid result structure for message %s: %s", message.id, result)
                    return

                logger.debug("Prediction complete: %s", result['prediction'])
            except Exception:
                logger.error("Error in predict_feedback_quality for message %s", message.id, exc_info=True)
                return

            if not result['is_good']:
                _task = asyncio.create_task(self.notifier.notify_bad_feedback(
                    message,
                    feedback_text,
                ))
                _task.add_done_callback(_log_task_error)

            mod_message = await self.notifier.send_prediction_result(message, result, feedback_text)
            if mod_message is None:
                return

            logger.info(
                "Feedback processed — prediction: %s, confidence: %.1f%%, message ID: %s",
                result['prediction'], result['probability'] * 100, mod_message.id
            )

            try:
                self.pending_validations[mod_message.id] = PendingValidation(
                    original_message=message,
                    feedback_text=feedback_text,
                    prediction=result,
                    mod_message_id=mod_message.id,
                )
            except Exception:
                logger.error("Error storing validation data", exc_info=True)

        except Exception:
            logger.error("Unhandled exception in on_message listener", exc_info=True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle validation reactions from moderators"""

        try:
            if user.bot:
                return

            if reaction.message.channel.id != DEV_SPAM:
                return

            if reaction.message.id not in self.pending_validations:
                return

            validation_data = self.pending_validations[reaction.message.id]

            if validation_data.validated:
                logger.debug("Message %s already validated", reaction.message.id)
                return

            try:
                if str(reaction.emoji) == "✅":
                    logger.info("Correct prediction validation by %s (ID: %s)", user.name, user.id)
                    await self._handle_validation(reaction.message, validation_data, True, user)
                elif str(reaction.emoji) == "❌":
                    logger.info("Incorrect prediction validation by %s (ID: %s)", user.name, user.id)
                    await self._handle_validation(reaction.message, validation_data, False, user)
            except Exception:
                logger.error("Error handling reaction", exc_info=True)

        except Exception:
            logger.error("Unhandled exception in on_reaction_add listener", exc_info=True)

    async def _handle_validation(self, mod_message, validation_data, is_correct, validator):
        """Handle validation of prediction"""

        try:
            logger.debug("Processing validation: is_correct=%s", is_correct)

            validation_data.validated = True

            try:
                embed = mod_message.embeds[0]

                if is_correct:
                    embed.color = discord.Color.blue()
                    embed.title = "✅ Validated: Correct Prediction"
                    status_text = "✅ Model prediction was **CORRECT**"
                    rating = 1
                else:
                    embed.color = discord.Color.orange()
                    embed.title = "❌ Validated: Incorrect Prediction"
                    status_text = "❌ Model prediction was **INCORRECT**"
                    rating = 0

                embed.add_field(
                    name="Validation Status",
                    value=f"{status_text}\nValidated by: {validator.mention}",
                    inline=False
                )

                await mod_message.edit(embed=embed)
            except Exception:
                logger.error("Error updating validation embed", exc_info=True)

            logger.info(
                "Validation: %s | Correct: %s | Validator: %s",
                validation_data.prediction['prediction'], is_correct, validator.name
            )

            try:
                feedback_entry = {
                    "message_id": validation_data.original_message.id,
                    "feedback": validation_data.feedback_text,
                    "rating": rating,
                    "timestamp": validation_data.original_message.created_at.isoformat()
                }
            except Exception:
                logger.error("Error creating feedback entry", exc_info=True)
                return

            filename = "feedback_json.json"
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
            except FileNotFoundError:
                data = []
                logger.debug("No existing file %s, starting fresh", filename)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in %s, starting fresh", filename)
                data = []
            except Exception:
                logger.error("Error reading %s", filename, exc_info=True)
                return

            try:
                data.append(feedback_entry)
            except Exception:
                logger.error("Error appending feedback entry", exc_info=True)
                return

            try:
                exporter = ExportJson(self.bot)
                await exporter.export_to_json(data, filename)
                logger.info("Feedback saved to %s (rating: %d)", filename, rating)
            except Exception:
                logger.error("Error exporting to JSON", exc_info=True)
                return

            try:
                entry_count = await exporter.count_entries(filename)
                logger.debug("Total feedback entries: %d", entry_count)
            except Exception:
                logger.warning("Error counting entries (non-critical)", exc_info=True)

            self.pending_validations.pop(mod_message.id, None)

            try:
                await mod_message.clear_reactions()
            except Exception:
                logger.warning("Could not clear reactions (non-critical)")

        except Exception:
            logger.error("Unhandled exception in _handle_validation", exc_info=True)

    @commands.command(name='feedbackstats', aliases=['fbstats'])
    @commands.has_permissions(manage_messages=True)
    async def feedback_stats(self, ctx):
        """Show feedback validation statistics"""

        try:
            total = len(self.pending_validations)
            validated = sum(1 for v in self.pending_validations.values() if v.validated)
            pending = total - validated

            embed = discord.Embed(
                title="📊 Feedback Validation Statistics",
                color=discord.Color.blue()
            )

            embed.add_field(name="Total Predictions", value=str(total), inline=True)
            embed.add_field(name="Validated", value=str(validated), inline=True)
            embed.add_field(name="Pending", value=str(pending), inline=True)
            embed.add_field(name="Listener Active", value="✅ Yes" if self.listener_active else "❌ No", inline=True)

            await ctx.send(embed=embed)
            logger.info(
                "Stats requested by %s: %d total, %d validated, %d pending",
                ctx.author.name, total, validated, pending
            )
        except Exception:
            await ctx.send("❌ Error generating stats")
            logger.error("Error in feedback_stats", exc_info=True)

    @commands.command(name='testfeedback', aliases=['tfb'])
    @commands.has_permissions(manage_messages=True)
    async def test_feedback(self, ctx, *, feedback_text):
        """Test the feedback quality model manually"""

        try:
            result = await predict_feedback_quality(feedback_text)

            if result is None:
                await ctx.send("❌ Error: Model returned no prediction")
                logger.error("test_feedback: Model returned None for user %s", ctx.author.name)
                return

            if not isinstance(result, dict) or 'prediction' not in result:
                await ctx.send("❌ Error: Invalid model response structure")
                logger.error("test_feedback: Invalid result structure: %s", result)
                return

        except Exception:
            await ctx.send("❌ Error predicting")
            logger.error("Error in test_feedback prediction", exc_info=True)
            return

        try:
            embed = discord.Embed(
                title="🧪 Feedback Quality Test",
                description=f"**Prediction:** {result['prediction']}",
                color=discord.Color.green() if result['is_good'] else discord.Color.red()
            )

            embed.add_field(name="Confidence", value=f"{result['probability']:.1%}", inline=True)
            embed.add_field(name="Input", value=f"```{feedback_text[:500]}```", inline=False)

            await ctx.send(embed=embed)
            logger.info(
                "Test feedback by %s: %s (%.1f%%)",
                ctx.author.name, result['prediction'], result['probability'] * 100
            )
        except Exception:
            await ctx.send("❌ Error creating response")
            logger.error("Error in test_feedback response", exc_info=True)

    @commands.command(name='fblistener', aliases=['fbcheck'])
    @commands.has_permissions(administrator=True)
    async def check_listener(self, ctx):
        """Check if feedback listener is active and reset if needed"""

        try:
            status = "✅ Active" if self.listener_active else "❌ Inactive"

            embed = discord.Embed(
                title="🔍 Feedback Listener Status",
                description=f"**Status:** {status}",
                color=discord.Color.green() if self.listener_active else discord.Color.red()
            )

            embed.add_field(name="Pending Validations", value=str(len(self.pending_validations)), inline=True)
            embed.add_field(name="Monitoring Channel", value=f"<#{AUDIO_FEEDBACK}>", inline=True)

            await ctx.send(embed=embed)
            logger.info("Listener check by %s: %s", ctx.author.name, status)

        except Exception:
            await ctx.send("❌ Error")
            logger.error("Error in check_listener command", exc_info=True)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(FeedbackMonitor(bot))
