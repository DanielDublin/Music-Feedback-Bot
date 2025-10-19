"""
Feedback Quality Monitor Cog
Monitors messages in the feedback channel and validates feedback quality
"""

import discord
from discord.ext import commands
from ml_model.ml_model_loader import predict_feedback_quality
import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Channel IDs
FEEDBACK_CHANNEL_ID = 732356488151957516  # Channel to monitor for feedback
MOD_CHANNEL_ID = 1137143797361422458      # Channel to send validation results

class FeedbackMonitor(commands.Cog):
    """Monitors and validates feedback quality"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_validations = {}  # Store message_id -> original_message mapping
        self.db_pool = None  # Placeholder for potential database pool (e.g., aiomysql)

    async def cog_unload(self):
        """Clean up resources when cog is unloaded"""
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()
            logging.info("FeedbackMonitor database connection closed")

    @commands.Cog.listener()
    async def on_ready(self):
        """Called when bot is ready"""
        logging.info(f"✅ FeedbackMonitor cog loaded")
        logging.info(f"   Monitoring channel: {FEEDBACK_CHANNEL_ID}")
        logging.info(f"   Sending results to: {MOD_CHANNEL_ID}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitor messages in the feedback channel that start with <mfr or <mf"""
        
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only monitor the feedback channel
        if message.channel.id != FEEDBACK_CHANNEL_ID:
            return
        
        # Only process if message starts with <mfr or <mf (case-insensitive)
        content_lower = message.content.strip().lower()
        logging.info(f"Processing message: {content_lower}")
        if not (content_lower.startswith('<mfr') or content_lower.startswith('<mf')):
            return
        
        # Extract feedback text after the command
        feedback_text = message.content.strip()[4:].strip()  # Remove prefix and spaces
        
        
        # Predict feedback quality
        try:
            logging.info(f"Predicting feedback quality for: {feedback_text}")
            result = await predict_feedback_quality(feedback_text)
            if result is None:
                mod_channel = self.bot.get_channel(MOD_CHANNEL_ID)
                if mod_channel:
                    await mod_channel.send("❌ Error: Feedback model unavailable. Check server logs.")
                logging.error("Feedback prediction failed: Model unavailable")
                return
            logging.info(f"Prediction result: {result}")
            
            # Get mod channel
            mod_channel = self.bot.get_channel(MOD_CHANNEL_ID)
            if not mod_channel:
                logging.error(f"Could not find mod channel {MOD_CHANNEL_ID}")
                return
            
            logging.info(f"Sending result to mod channel: {mod_channel}")
            # Create embed with prediction
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
            
            # Send to mod channel with reaction buttons
            mod_message = await mod_channel.send(embed=embed)
            
            # Add reaction buttons for validation
            await mod_message.add_reaction("✅")  # Correct prediction
            await mod_message.add_reaction("❌")  # Incorrect prediction
            
            # Store for validation tracking
            self.pending_validations[mod_message.id] = {
                'original_message': message,
                'prediction': result,
                'validated': False
            }
            
        except Exception as e:
            logging.error(f"Error processing feedback: {e}", exc_info=True)
            mod_channel = self.bot.get_channel(MOD_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(f"❌ Error processing feedback: {str(e)}")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle validation reactions from moderators"""
        
        # Ignore bot reactions
        if user.bot:
            return
        
        # Only process reactions in mod channel
        if reaction.message.channel.id != MOD_CHANNEL_ID:
            return
        
        # Check if this is a validation message
        if reaction.message.id not in self.pending_validations:
            return
        
        validation_data = self.pending_validations[reaction.message.id]
        
        # Already validated
        if validation_data['validated']:
            return
        
        # Process validation
        if str(reaction.emoji) == "✅":
            # Correct prediction
            await self._handle_validation(reaction.message, validation_data, True, user)
            
        elif str(reaction.emoji) == "❌":
            # Incorrect prediction
            await self._handle_validation(reaction.message, validation_data, False, user)
    
    async def _handle_validation(self, mod_message, validation_data, is_correct, validator):
        """Handle validation of prediction"""

        logging.info(f"Validating prediction: {validation_data['prediction']['prediction']} | "
                     f"Correct: {is_correct} | Validator: {validator.name}")
        
        # Mark as validated
        validation_data['validated'] = True
        
        # Update embed
        embed = mod_message.embeds[0]
        
        if is_correct:
            embed.color = discord.Color.blue()
            embed.title = "✅ Validated: Correct Prediction"
            status_text = "✅ Model prediction was **CORRECT**"
        else:
            embed.color = discord.Color.orange()
            embed.title = "❌ Validated: Incorrect Prediction"
            status_text = "❌ Model prediction was **INCORRECT**"
        
        # Add validation info
        embed.add_field(
            name="Validation Status",
            value=f"{status_text}\nValidated by: {validator.mention}",
            inline=False
        )
        
        await mod_message.edit(embed=embed)
        
        # Log validation (you can save this to a database later)
        logging.info(f"📊 Validation: {validation_data['prediction']['prediction']} | "
                     f"Correct: {is_correct} | Validator: {validator.name}")
        
        # Optional: Remove reactions after validation
        await mod_message.clear_reactions()
    
    @commands.command(name='feedbackstats', aliases=['fbstats'])
    @commands.has_permissions(manage_messages=True)
    async def feedback_stats(self, ctx):
        """Show feedback validation statistics"""
        
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
    
    @commands.command(name='testfeedback', aliases=['tfb'])
    @commands.has_permissions(manage_messages=True)
    async def test_feedback(self, ctx, *, feedback_text):
        """Test the feedback quality model manually"""
        
        try:
            result = await predict_feedback_quality(feedback_text)
            if result is None:
                await ctx.send("❌ Error: Feedback model unavailable. Check server logs.")
                logging.error("Feedback test failed: Model unavailable")
                return
            
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
            await ctx.send(f"❌ Error: {str(e)}")
            logging.error(f"Error in test_feedback: {e}", exc_info=True)

async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(FeedbackMonitor(bot))