"""
Feedback Quality Monitor Cog
Monitors messages in the feedback channel and validates feedback quality
"""

import discord
from discord.ext import commands
from ml_model.ml_model_loader import predict_feedback_quality
from data.constants import AUDIO_FEEDBACK, FEEDBACK_CHANNEL_ID, MODERATORS_CHANNEL_ID, DEV_SPAM, BOT_LOG, CO_DEV_ID
from ml_model.export_json import ExportJson
from ml_model.mod_bad_feedback_notification import FeedbackNotifier
import asyncio
import json
import traceback

class FeedbackMonitor(commands.Cog):
    """Monitors and validates feedback quality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_validations = {}  # Store message_id -> original_message mapping
        self.listener_active = True
        self.notifier = FeedbackNotifier(bot)  # Add notifier instance
        
    async def log_to_bot_log(self, message: str, error: Exception = None):
        """Send detailed logs to BOT_LOG channel"""
        try:
            log_channel = self.bot.get_channel(BOT_LOG)
            if log_channel is None:
                print(f"[FeedbackMonitor] BOT_LOG channel not found: {message}")
                return
            
            timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            
            if error:
                # Format error with full traceback
                error_details = ''.join(traceback.format_exception(type(error), error, error.__traceback__))
                full_message = f"```\n[{timestamp}] FeedbackMonitor Error\n{message}\n\nTraceback:\n{error_details}\n```"
                
                # Split if too long (Discord 2000 char limit)
                if len(full_message) > 1990:
                    await log_channel.send(f"```\n[{timestamp}] FeedbackMonitor Error\n{message}\n```")
                    # Send traceback in chunks
                    for i in range(0, len(error_details), 1800):
                        await log_channel.send(f"```\n{error_details[i:i+1800]}\n```")
                else:
                    await log_channel.send(full_message)
            else:
                # Regular info message
                await log_channel.send(f"```\n[{timestamp}] FeedbackMonitor: {message}\n```")
                
        except Exception as e:
            # Fallback to console if BOT_LOG fails
            print(f"[FeedbackMonitor] Failed to log to BOT_LOG: {e}")
            print(f"[FeedbackMonitor] Original message: {message}")
            if error:
                traceback.print_exception(type(error), error, error.__traceback__)
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready"""
        try:
            print(f"✅ FeedbackMonitor cog loaded")
            print(f"   Monitoring channel: {AUDIO_FEEDBACK}")
            print(f"   Sending results to: {DEV_SPAM}")
            
            await self.log_to_bot_log(
                f"🚀 FeedbackMonitor started\n"
                f"   Monitoring: {AUDIO_FEEDBACK}\n"
                f"   Results to: {DEV_SPAM}\n"
                f"   Listener active: {self.listener_active}"
            )
        except Exception as e:
            print(f"❌ Error in on_ready: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("❌ Error during FeedbackMonitor startup", e)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages in the feedback channel that start with <MFR"""
        
        try:
            # Check if listener is active
            if not self.listener_active:
                await self.log_to_bot_log("⚠️ on_message called but listener is marked inactive")
                return
            
            # Ignore bot messages
            if message.author.bot:
                return
            
            # Only monitor the feedback channel
            if message.channel.id != AUDIO_FEEDBACK:
                return
            
            # Only process if message starts with <MFR or <mfr
            content_lower = message.content.strip().lower()
            if not content_lower.startswith('<mfr'):
                return
            
            # Log that we're processing
            await self.log_to_bot_log(f"🔍 Processing feedback from {message.author.name} (ID: {message.author.id})")
            
            # Extract feedback text after the command
            feedback_text = message.content.strip()[4:].strip()  # Remove '<MFR' and spaces
            
            if not feedback_text:
                await self.log_to_bot_log(f"⚠️ Empty feedback text from {message.author.name}")
                return
        
            print(f"🔍 Processing feedback from {message.author.name}")
            
            # Predict feedback quality
            try:
                result = await predict_feedback_quality(feedback_text)
                
                # Check if result is None
                if result is None:
                    print(f"❌ predict_feedback_quality returned None")
                    await self.log_to_bot_log(f"❌ ML prediction returned None for message {message.id}")
                    return
                
                # Validate result structure
                if not isinstance(result, dict) or 'prediction' not in result:
                    print(f"❌ Invalid result structure: {result}")
                    await self.log_to_bot_log(f"❌ ML prediction returned invalid structure for message {message.id}")
                    return
                
                print(f"✅ Prediction complete: {result['prediction']}")
            except Exception as e:
                print(f"❌ Error in predict_feedback_quality: {e}")
                traceback.print_exc()
                await self.log_to_bot_log(f"❌ ML prediction failed for message {message.id}", e)
                return
            
            # Get dev spam channel
            try:
                dev_spam = self.bot.get_channel(DEV_SPAM)
                if not dev_spam:
                    print(f"❌ Could not find dev spam channel {DEV_SPAM}")
                    await self.log_to_bot_log(f"❌ DEV_SPAM channel {DEV_SPAM} not found")
                    return
                print(f"✅ Found dev spam channel")
            except Exception as e:
                print(f"❌ Error getting dev spam channel: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error getting DEV_SPAM channel", e)
                return
            
            # Create embed with prediction
            try:
                embed = discord.Embed(
                    title="🤖 Feedback Quality Check",
                    description=f"**Prediction:** {result['prediction']}",
                    color=discord.Color.green() if result['is_good'] else discord.Color.red()
                )
                
                # Add feedback content (truncated if too long)
                feedback_preview = feedback_text[:500]
                if len(feedback_text) > 500:
                    feedback_preview += "..."
                
                embed.add_field(
                    name="Feedback Content",
                    value=f"```{feedback_preview}```",
                    inline=False
                )
                
                embed.add_field(
                    name="Author",
                    value=f"{message.author.mention} (`{message.author.id}`)",
                    inline=True
                )
                
                embed.add_field(
                    name="Confidence",
                    value=f"{result['probability']:.1%}",
                    inline=True
                )
                
                embed.add_field(
                    name="Original Message",
                    value=f"[Jump to message]({message.jump_url})",
                    inline=False
                )
                
                embed.set_footer(text=f"Message ID: {message.id}")
                embed.timestamp = message.created_at
                print("✅ Embed created")
            except Exception as e:
                print(f"❌ Error creating embed: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error creating embed", e)
                return
            
            # Notify mods if it's bad feedback using the notifier
            if not result['is_good']:
                await self.notifier.notify_bad_feedback(
                    message, 
                    feedback_text,
                    log_callback=self.log_to_bot_log
                )
            
            # Send to dev spam channel with reaction buttons
            try:
                mod_message = await dev_spam.send(
                    content=f"<@{CO_DEV_ID}> New feedback!",
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(users=True)
                )
                print(f"✅ Embed sent, message ID: {mod_message.id}")
                await self.log_to_bot_log(
                    f"✅ Feedback processed successfully\n"
                    f"   Prediction: {result['prediction']}\n"
                    f"   Confidence: {result['probability']:.1%}\n"
                    f"   Message ID: {mod_message.id}"
                )
            except Exception as e:
                print(f"❌ Error sending embed: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error sending embed to DEV_SPAM", e)
                return
            
            # Add reaction buttons for validation
            try:
                await mod_message.add_reaction("✅")
                await mod_message.add_reaction("❌")
                print("✅ Reactions added")
            except Exception as e:
                print(f"❌ Error adding reactions: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("⚠️ Error adding reactions (non-critical)", e)
                # Continue anyway
            
            # Store for validation tracking
            try:
                self.pending_validations[mod_message.id] = {
                    'original_message': message,
                    'feedback_text': feedback_text,
                    'prediction': result,
                    'validated': False,
                    'mod_message_id': mod_message.id
                }
                print("✅ Validation data stored")
            except Exception as e:
                print(f"❌ Error storing validation data: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error storing validation data", e)
                
        except Exception as e:
            # Catch-all for any unexpected errors in the entire listener
            print(f"💥 CRITICAL: Unhandled exception in on_message listener: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("💥 CRITICAL: Unhandled exception in on_message listener", e)
            # DO NOT re-raise - we want the listener to keep running
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle validation reactions from moderators"""
        
        try:
            # Ignore bot reactions
            if user.bot:
                return
            
            # Only process reactions in dev spam channel
            if reaction.message.channel.id != DEV_SPAM:
                return
            
            # Check if this is a validation message
            if reaction.message.id not in self.pending_validations:
                return
            
            validation_data = self.pending_validations[reaction.message.id]
            
            # Already validated
            if validation_data['validated']:
                print(f"⚠️ Message {reaction.message.id} already validated")
                return
            
            # Process validation
            try:
                if str(reaction.emoji) == "✅":
                    print(f"✅ Correct prediction validation by {user.name}")
                    await self.log_to_bot_log(f"✅ Validation: CORRECT by {user.name} (ID: {user.id})")
                    await self._handle_validation(reaction.message, validation_data, True, user)
                elif str(reaction.emoji) == "❌":
                    print(f"❌ Incorrect prediction validation by {user.name}")
                    await self.log_to_bot_log(f"❌ Validation: INCORRECT by {user.name} (ID: {user.id})")
                    await self._handle_validation(reaction.message, validation_data, False, user)
            except Exception as e:
                print(f"❌ Error handling reaction: {e}")
                traceback.print_exc()
                await self.log_to_bot_log(f"❌ Error handling validation reaction", e)
                
        except Exception as e:
            # Catch-all for any unexpected errors
            print(f"💥 CRITICAL: Unhandled exception in on_reaction_add listener: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("💥 CRITICAL: Unhandled exception in on_reaction_add listener", e)
            # DO NOT re-raise
    
    async def _handle_validation(self, mod_message, validation_data, is_correct, validator):
        """Handle validation of prediction"""
        
        try:
            print(f"🔄 Processing validation: is_correct={is_correct}")
            
            # Mark as validated
            validation_data['validated'] = True
            
            # Update embed
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
                
                # Add validation info
                embed.add_field(
                    name="Validation Status",
                    value=f"{status_text}\nValidated by: {validator.mention}",
                    inline=False
                )
                
                await mod_message.edit(embed=embed)
                print("✅ Embed updated")
            except Exception as e:
                print(f"❌ Error updating embed: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error updating validation embed", e)
            
            # Log validation
            print(f"📊 Validation: {validation_data['prediction']['prediction']} | "
                  f"Correct: {is_correct} | Validator: {validator.name}")
            
            # Export validated feedback to JSON
            try:
                feedback_entry = {
                    "message_id": validation_data['original_message'].id,
                    "feedback": validation_data['feedback_text'],
                    "rating": rating,
                    "timestamp": validation_data['original_message'].created_at.isoformat()
                }
                print(f"✅ Feedback entry created")
            except Exception as e:
                print(f"❌ Error creating feedback entry: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error creating feedback entry", e)
                return
            
            # Read existing data
            filename = "feedback_json.json"
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                print(f"✅ Loaded existing data from {filename}")
            except FileNotFoundError:
                data = []
                print(f"⚠️ No existing file, starting fresh")
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid JSON in {filename}, starting fresh: {e}")
                await self.log_to_bot_log(f"⚠️ Invalid JSON in {filename}, starting fresh", e)
                data = []
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
                traceback.print_exc()
                await self.log_to_bot_log(f"❌ Error reading {filename}", e)
                return
            
            # Append new entry
            try:
                data.append(feedback_entry)
                print(f"✅ Entry appended to data list")
            except Exception as e:
                print(f"❌ Error appending entry: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error appending feedback entry", e)
                return
            
            # Export using ExportJson
            try:
                exporter = ExportJson(self.bot)
                exporter.export_to_json(data, filename)
                print(f"✅ Data exported to {filename}")
                await self.log_to_bot_log(f"💾 Feedback saved to {filename} (Rating: {rating})")
            except Exception as e:
                print(f"❌ Error exporting to JSON: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("❌ Error exporting to JSON", e)
                return
            
            # Check if we need to send to mod channel
            try:
                entry_count = await exporter.count_entries(filename)
                print(f"📝 Total feedback entries: {entry_count}")
            except Exception as e:
                print(f"❌ Error counting entries: {e}")
                traceback.print_exc()
                await self.log_to_bot_log("⚠️ Error counting entries (non-critical)", e)
            
            # Remove from pending_validations now that it's been handled
            self.pending_validations.pop(mod_message.id, None)

            # Optional: Remove reactions after validation
            try:
                await mod_message.clear_reactions()
                print("✅ Reactions cleared")
            except Exception as e:
                print(f"⚠️ Could not clear reactions: {e}")
                # Not critical, continue
                
        except Exception as e:
            # Catch-all for validation handler
            print(f"💥 CRITICAL: Unhandled exception in _handle_validation: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("💥 CRITICAL: Unhandled exception in _handle_validation", e)
    
    @commands.command(name='feedbackstats', aliases=['fbstats'])
    @commands.has_permissions(manage_messages=True)
    async def feedback_stats(self, ctx):
        """Show feedback validation statistics"""
        
        try:
            total = len(self.pending_validations)
            validated = sum(1 for v in self.pending_validations.values() if v['validated'])
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
            await self.log_to_bot_log(f"📊 Stats requested by {ctx.author.name}: {total} total, {validated} validated, {pending} pending")
        except Exception as e:
            await ctx.send(f"❌ Error generating stats: {str(e)}")
            print(f"❌ Error in feedback_stats: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("❌ Error in feedback_stats command", e)
    
    @commands.command(name='testfeedback', aliases=['tfb'])
    @commands.has_permissions(manage_messages=True)
    async def test_feedback(self, ctx, *, feedback_text):
        """Test the feedback quality model manually"""
        
        try:
            result = await predict_feedback_quality(feedback_text)
            
            # Check if result is None
            if result is None:
                await ctx.send("❌ Error: Model returned no prediction")
                await self.log_to_bot_log(f"❌ test_feedback: Model returned None for user {ctx.author.name}")
                return
            
            # Validate result structure
            if not isinstance(result, dict) or 'prediction' not in result:
                await ctx.send(f"❌ Error: Invalid model response structure")
                await self.log_to_bot_log(f"❌ test_feedback: Invalid result structure: {result}")
                return
                
        except Exception as e:
            await ctx.send(f"❌ Error predicting: {str(e)}")
            print(f"❌ Error in test_feedback prediction: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("❌ Error in test_feedback prediction", e)
            return
        
        try:
            embed = discord.Embed(
                title="🧪 Feedback Quality Test",
                description=f"**Prediction:** {result['prediction']}",
                color=discord.Color.green() if result['is_good'] else discord.Color.red()
            )
            
            embed.add_field(
                name="Confidence",
                value=f"{result['probability']:.1%}",
                inline=True
            )
            
            embed.add_field(
                name="Input",
                value=f"```{feedback_text[:500]}```",
                inline=False
            )
            
            await ctx.send(embed=embed)
            await self.log_to_bot_log(f"🧪 Test feedback by {ctx.author.name}: {result['prediction']} ({result['probability']:.1%})")
        except Exception as e:
            await ctx.send(f"❌ Error creating response: {str(e)}")
            print(f"❌ Error in test_feedback response: {e}")
            traceback.print_exc()
            await self.log_to_bot_log("❌ Error in test_feedback response", e)
    
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
            await self.log_to_bot_log(f"🔍 Listener check by {ctx.author.name}: {status}")
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")
            await self.log_to_bot_log("❌ Error in check_listener command", e)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(FeedbackMonitor(bot))