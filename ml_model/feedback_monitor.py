"""
Feedback Quality Monitor Cog
Monitors messages in the feedback channel and validates feedback quality
"""

import discord
from discord.ext import commands
from ml_model.ml_model_loader import predict_feedback_quality
from data.constants import AUDIO_FEEDBACK, FEEDBACK_CHANNEL_ID, MODERATORS_CHANNEL_ID, DEV_SPAM
from ml_model.export_json import ExportJson
import asyncio
import json
import traceback

class FeedbackMonitor(commands.Cog):
    """Monitors and validates feedback quality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_validations = {}  # Store message_id -> original_message mapping
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready"""
        print(f"✅ FeedbackMonitor cog loaded")
        print(f"   Monitoring channel: {AUDIO_FEEDBACK}")
        print(f"   Sending results to: {MODERATORS_CHANNEL_ID}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages in the feedback channel that start with <MFR"""

        print("📩 New message received for feedback monitoring")
        
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
        
        # Extract feedback text after the command
        feedback_text = message.content.strip()[4:].strip()  # Remove '<MFR' and spaces
        
        # Ignore if no feedback text provided
        if len(feedback_text) < 10:
            print("⚠️ Feedback too short, ignoring")
            return
        
        print(f"🔍 Processing feedback from {message.author.name}")
        
        # Predict feedback quality
        try:
            result = await predict_feedback_quality(feedback_text)
            print(f"✅ Prediction complete: {result['prediction']}")
        except Exception as e:
            print(f"❌ Error in predict_feedback_quality: {e}")
            traceback.print_exc()
            return
        
        # Get mod channel
        try:
            dev_spam = self.bot.get_channel(DEV_SPAM)
            if not dev_spam:
                print(f"❌ Could not find dev spam channel {DEV_SPAM}")
                return
            print(f"✅ Found dev spam channel")
        except Exception as e:
            print(f"❌ Error getting dev spam channel: {e}")
            traceback.print_exc()
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
            return
        
        # Send to mod channel with reaction buttons
        try:
            await dev_spam.send(
                f"<@{412733389196623879}> New feedback!",
                allowed_mentions=discord.AllowedMentions(users=True)
            )
            print("✅ Mention sent")
        except Exception as e:
            print(f"❌ Error sending mention: {e}")
            traceback.print_exc()
            # Continue anyway
        
        try:
            mod_message = await dev_spam.send(embed=embed)
            print(f"✅ Embed sent, message ID: {mod_message.id}")
        except Exception as e:
            print(f"❌ Error sending embed: {e}")
            traceback.print_exc()
            return
        
        # Add reaction buttons for validation
        try:
            await mod_message.add_reaction("✅")
            await mod_message.add_reaction("❌")
            print("✅ Reactions added")
        except Exception as e:
            print(f"❌ Error adding reactions: {e}")
            traceback.print_exc()
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
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle validation reactions from moderators"""
        
        # Ignore bot reactions
        if user.bot:
            return
        
        # Only process reactions in mod channel
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
                await self._handle_validation(reaction.message, validation_data, True, user)
            elif str(reaction.emoji) == "❌":
                print(f"❌ Incorrect prediction validation by {user.name}")
                await self._handle_validation(reaction.message, validation_data, False, user)
        except Exception as e:
            print(f"❌ Error handling reaction: {e}")
            traceback.print_exc()
    
    async def _handle_validation(self, mod_message, validation_data, is_correct, validator):
        """Handle validation of prediction"""
        
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
            data = []
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            traceback.print_exc()
            return
        
        # Append new entry
        try:
            data.append(feedback_entry)
            print(f"✅ Entry appended to data list")
        except Exception as e:
            print(f"❌ Error appending entry: {e}")
            traceback.print_exc()
            return
        
        # Export using ExportJson
        try:
            exporter = ExportJson(self.bot)
            exporter.export_to_json(data, filename)
            print(f"✅ Data exported to {filename}")
        except Exception as e:
            print(f"❌ Error exporting to JSON: {e}")
            traceback.print_exc()
            return
        
        # Check if we need to send to mod channel
        try:
            entry_count = await exporter.count_entries(filename)
            print(f"📝 Total feedback entries: {entry_count}")
        except Exception as e:
            print(f"❌ Error counting entries: {e}")
            traceback.print_exc()
        
        # Optional: Remove reactions after validation
        try:
            await mod_message.clear_reactions()
            print("✅ Reactions cleared")
        except Exception as e:
            print(f"⚠️ Could not clear reactions: {e}")
            # Not critical, continue
    
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
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error generating stats: {str(e)}")
            print(f"❌ Error in feedback_stats: {e}")
            traceback.print_exc()
    
    @commands.command(name='testfeedback', aliases=['tfb'])
    @commands.has_permissions(manage_messages=True)
    async def test_feedback(self, ctx, *, feedback_text):
        """Test the feedback quality model manually"""
        
        try:
            result = await predict_feedback_quality(feedback_text)
        except Exception as e:
            await ctx.send(f"❌ Error predicting: {str(e)}")
            print(f"❌ Error in test_feedback prediction: {e}")
            traceback.print_exc()
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
        except Exception as e:
            await ctx.send(f"❌ Error creating response: {str(e)}")
            print(f"❌ Error in test_feedback response: {e}")
            traceback.print_exc()

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(FeedbackMonitor(bot))