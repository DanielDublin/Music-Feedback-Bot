import discord
import asyncio
import logging
from discord.ext import commands
from discord import app_commands
from cogs.aotw.create_poll import CreatePoll, PollView
from cogs.aotw.configure_channel import ConfigureChannel
from data.constants import AOTW_CHANNEL, AOTW_SUBMISSIONS, MODERATORS_CHANNEL_ID, AOTW_ROLE, AOTW_VOTES

logger = logging.getLogger(__name__)


def _log_task_error(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        logger.error("[AOTW] Background task error: %r", task.exception())


class AOTWEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_config = ConfigureChannel(bot)
        self._active_poll: CreatePoll | None = None

    async def cog_load(self):
        poll = CreatePoll.restore(self.bot)
        if poll is None:
            return
        view = PollView(poll, poll.names, poll.emojis, poll.messages)
        self.bot.add_view(view, message_id=poll._poll_message_id)
        self._active_poll = poll
        logger.info("[AOTW] Restored active poll from disk (message ID: %s, %d voters)", poll._poll_message_id, len(poll.voters))

    async def wait_for_winner_response(self, winner_info, winner_channel, winner_member):
        """
        Listens for the winner's response in their private channel
        winner_channel: The newly created private channel for the winner
        winner_member: The Discord Member object of the winner
        """
        mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)
        if mod_channel is None:
            logger.error("wait_for_winner_response: MODERATORS_CHANNEL_ID %s not cached; aborting", MODERATORS_CHANNEL_ID)
            return

        # Give the winner permissions to see and use the channel
        try:
            await winner_channel.set_permissions(winner_member, view_channel=True, send_messages=True)
            await mod_channel.send(f"✅ Set permissions for {winner_member.name} in {winner_channel.name}")
        except Exception as e:
            await mod_channel.send(f"❌ Error setting permissions for {winner_member.name}: {e}")
        
        def check(m):
            return (
                m.channel.id == winner_channel.id and
                not m.author.bot and
                m.author.id == winner_member.id
            )
        
        try:
            await mod_channel.send(f"⏳ Waiting for {winner_member.name}'s response in channel {winner_channel.mention}...")
            
            # Wait for winner to respond in their private channel
            message = await self.bot.wait_for('message', check=check, timeout=86400.0)  # 24 hours
            
            # Notify moderators
            await mod_channel.send(
                f"AOTW NOTICE - **{message.author}** sent a message in <#{message.channel.id}>: {message.content}"
            )

            # give AOTW role
            try:
                aotw_role = message.guild.get_role(AOTW_ROLE)
                await message.author.add_roles(aotw_role)
                await mod_channel.send(f"✅ Gave AOTW role to {message.author.name}")
            except Exception as e:
                await mod_channel.send(f"❌ Error giving AOTW role: {e}")

            try:
                await message.reply("Thank you! And congrats again on winning Artist of the Week!")
            except Exception as e:
                await mod_channel.send(f"❌ Error replying to winner: {e}")
            
            # Continue configuring the AOTW system
            await self.channel_config.initialize_channels()

            # delete the previous message in aotw channel
            try:
                async for msg in self.channel_config.aotw_channel.history(limit=1):
                    await msg.delete()
                    await mod_channel.send("✅ Deleted previous message from AOTW channel")
                    break
            except Exception as e:
                await mod_channel.send(f"❌ Error deleting message from AOTW channel: {e}")

            # Delete the aotw-q-a channel (the public submissions channel)
            try:
                await self.channel_config.purge_channel()
                await mod_channel.send("✅ Purged Q&A channel")
            except Exception as e:
                await mod_channel.send(f"❌ Error purging Q&A channel: {e}")

            # Change permissions for Q&A
            try:
                await self.channel_config.winner_perms()
                await mod_channel.send("✅ Changed Q&A channel permissions")
            except Exception as e:
                await mod_channel.send(f"❌ Error changing Q&A permissions: {e}")

            # Post the announcement in aotw channel
            try:
                await self.channel_config.aotw_winner_announcement(AOTW_VOTES, message)
                await mod_channel.send("✅ Posted winner announcement in AOTW channel")
            except Exception as e:
                await mod_channel.send(f"❌ Error posting winner announcement: {e}")

            # Announce Q&A channel
            try:
                await self.channel_config.qa_announcement(winner_info['name'])
                await mod_channel.send("✅ Posted Q&A announcement")
            except Exception as e:
                await mod_channel.send(f"❌ Error posting Q&A announcement: {e}")

            
        except asyncio.TimeoutError:
            await mod_channel.send(f"⚠️ AOTW winner {winner_info['name']} didn't respond within 24 hours!")
        except Exception as e:
            await mod_channel.send(f"❌ Unexpected error in winner listener for {winner_info['name']}: {e}")

    @app_commands.command(name = "aotw_voting", description = "Setup poll and channels for AOTW voting")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_voting(self, interaction):

        channel_id = AOTW_SUBMISSIONS
        mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

        await interaction.response.defer()

        if mod_channel is None:
            logger.error("aotw_voting: MODERATORS_CHANNEL_ID %s not cached; aborting", MODERATORS_CHANNEL_ID)
            await interaction.followup.send("❌ Moderators channel not found — aborting.", ephemeral=True)
            return

        try:
            await self.channel_config.initialize_channels()
            await mod_channel.send("✅ Channels initialized")
        except Exception as e:
            await mod_channel.send(f"❌ Error initializing channels: {e}")

        # clear votes channel so vote tracking starts fresh for the new cycle
        try:
            votes_channel = self.bot.get_channel(AOTW_VOTES)
            if votes_channel:
                await votes_channel.purge(limit=None)
                await mod_channel.send("✅ Cleared votes channel for new cycle")
            else:
                await mod_channel.send("⚠️ WARNING: Could not find votes channel to clear")
        except Exception as e:
            await mod_channel.send(f"❌ Error clearing votes channel: {e}")

        # change perms for aotw submissions
        try:
            await self.channel_config.change_voting_perms()
            await mod_channel.send("✅ Changed voting permissions")
        except Exception as e:
            await mod_channel.send(f"❌ Error changing voting permissions: {e}")

        # change name + topic to aotw_voting
        try:
            await self.channel_config.change_name("aotw-voting")
            await mod_channel.send("✅ Changed channel name to aotw-voting")
        except Exception as e:
            await mod_channel.send(f"❌ Error changing channel name: {e}")

        # delete any messages with a file
        try:
            await self.channel_config.check_for_not_links()
            await mod_channel.send("✅ Deleted messages with files")
        except Exception as e:
            await mod_channel.send(f"❌ Error deleting file messages: {e}")

        # create the poll in aotw submissions
        poll = CreatePoll(self.bot)
        try:
            names = await poll.scrape_channel_for_names(interaction, channel_id)
            embed, emojis = await poll.create_embed(interaction, names)
            await poll.react_to_embed(interaction, embed, emojis, names)
            self._active_poll = poll
            await mod_channel.send("✅ Poll created")
        except Exception as e:
            await mod_channel.send(f"❌ Error creating poll: {e}")

        # send announcement under poll
        try:
            await self.channel_config.send_voting_announcement()
            await mod_channel.send("✅ Sent voting announcement")
        except Exception as e:
            await mod_channel.send(f"❌ Error sending voting announcement: {e}")

        # create event for voting
        try:
            await self.channel_config.schedule_voting_event()
            await mod_channel.send("✅ Scheduled voting event")
        except Exception as e:
            await mod_channel.send(f"❌ Error scheduling voting event: {e}")

        # reminders for gen chat
        try:
            # cancel any previously running reminder loop before starting a new one
            old_config = getattr(self.bot, '_aotw_config', None)
            if old_config is not None:
                old_config.stop_voting_reminders()
            await self.channel_config.schedule_general_chat_reminders()
            self.bot._aotw_config = self.channel_config  # save instance so aotw_winner can stop its task
            await mod_channel.send("✅ Scheduled general chat reminders")
        except Exception as e:
            await mod_channel.send(f"❌ Error scheduling reminders: {e}")

        await interaction.followup.send("✅ AOTW Voting setup complete!", ephemeral=True)


    @app_commands.command(name = "aotw_submissions", description = "Setup poll and channels for AOTW submissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_submissions(self, interaction):

        channel_id = AOTW_SUBMISSIONS
        mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

        await interaction.response.defer()

        if mod_channel is None:
            logger.error("aotw_submissions: MODERATORS_CHANNEL_ID %s not cached; aborting", MODERATORS_CHANNEL_ID)
            await interaction.followup.send("❌ Moderators channel not found — aborting.", ephemeral=True)
            return

        try:
            await self.channel_config.initialize_channels()
            await mod_channel.send("✅ Channels initialized")
        except Exception as e:
            await mod_channel.send(f"❌ Error initializing channels: {e}")

        # check aotw_channel announcement and post
        try:
            formatted_six_months = await self.channel_config.calculate_six_months()
            await self.channel_config.check_aotw_channel_announcement(formatted_six_months)
            await mod_channel.send("✅ AOTW channel announcement checked")
        except Exception as e:
            await mod_channel.send(f"❌ Error checking aotw_channel announcement: {e}")

        try:
            # purge aotw submissions
            await self.channel_config.purge_channel()
            await mod_channel.send("✅ AOTW submissions purged")
        except Exception as e:
            await mod_channel.send(f"❌ Error purging aotw submissions: {e}")

        try:
            # rename to aotw submissions + topic
            await self.channel_config.change_name("aotw-submissions")
            await mod_channel.send("✅ Name changed to aotw-submissions")
        except Exception as e:
            await mod_channel.send(f"❌ Error changing name: {e}")

        try:
            # change perms
            await self.channel_config.change_submissions_perms()
            await mod_channel.send("✅ Permissions changed")
        except Exception as e:
            await mod_channel.send(f"❌ Error changing permissions: {e}")

        try:
            # post submissions announcement
            formatted_one_week, formatted_two_weeks = await self.channel_config.calculate_two_weeks()
            await self.channel_config.send_submissions_announcement(formatted_one_week, formatted_two_weeks, formatted_six_months)
            await mod_channel.send("✅ Submissions announcement sent")
        except Exception as e:
            await mod_channel.send(f"❌ Error sending submissions announcement: {e}")

        await interaction.followup.send("✅ AOTW Submissions setup complete!", ephemeral=True)

    @app_commands.command(name = "aotw_winner", description = "Setup poll and channels for AOTW winner")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_winner(self, interaction):

        await interaction.response.defer()

        mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)
        if mod_channel is None:
            logger.error("aotw_winner: MODERATORS_CHANNEL_ID %s not cached; aborting", MODERATORS_CHANNEL_ID)
            await interaction.followup.send("❌ Moderators channel not found — aborting.", ephemeral=True)
            return

        try:
            await self.channel_config.initialize_channels()
            await mod_channel.send("✅ Channels initialized")
        except Exception as e:
            await mod_channel.send(f"❌ Error initializing channels: {e}")

        try:
            # end the aotw event
            await self.channel_config.end_aotw_event()
            await mod_channel.send("✅ AOTW voting event ended")
            # stop voting reminders — must use the original instance that started the task
            voting_config = getattr(self.bot, '_aotw_config', None)
            if voting_config is not None:
                voting_config.stop_voting_reminders()
                self.bot._aotw_config = None
            else:
                self.channel_config.stop_voting_reminders()  # fallback (no-op if task not running)
            await mod_channel.send("✅ Stopped voting reminders")
        except Exception as e:
            await mod_channel.send(f"❌ Error ending aotw event: {e}")

        try:
            # remove role from current AOTW
            await self.channel_config.remove_aotw_role(interaction)
            await mod_channel.send("✅ Removed AOTW role from current holder")
        except Exception as e:
            await mod_channel.send(f"❌ Error removing AOTW role: {e}")

        # Create poll instance
        poll = CreatePoll(self.bot)

        # FIRST: Scrape channel to get all submissions with links BEFORE purging
        try:
            names = await poll.scrape_channel_for_names(interaction, AOTW_SUBMISSIONS)
            await mod_channel.send(f"✅ Scraped {len(names)} submissions")
        except Exception as e:
            await mod_channel.send(f"❌ Error scraping channel: {e}")
            await interaction.followup.send("❌ Error reading submissions!")
            return

        # Clear persisted poll state — winner is being determined
        if self._active_poll:
            self._active_poll._clear_state()
            self._active_poll = None
        else:
            CreatePoll._clear_state()

        # SECOND: Determine the winner from votes
        try:
            winner_data = await poll.determine_the_winner()
            
            if winner_data is None:
                await interaction.followup.send("❌ No votes found!")
                return
            
            winners = winner_data['winners']
            max_votes = winner_data['votes']
            
            if len(winners) > 1:
                await interaction.followup.send(f"⚠️ It's a tie! Winners: {', '.join(winners)} with {max_votes} votes each")
                return
            
            winner_name = winners[0]
            await mod_channel.send(f"✅ Winner determined: {winner_name} with {max_votes} votes")
        except Exception as e:
            await mod_channel.send(f"❌ Error determining winner: {e}")
            await interaction.followup.send("❌ Error determining winner!")
            return

        # THIRD: Get the winner's link from scraped data
        try:
            winner_link = poll.messages.get(winner_name, "No link provided")
            
            # Send to votes channel for record keeping
            votes_channel = self.bot.get_channel(AOTW_VOTES)
            if votes_channel:
                await votes_channel.send(f"**WINNER:** {winner_name}\n**Link:** {winner_link}\n**Votes:** {max_votes}")
                await mod_channel.send("✅ Sent winner info to votes channel")
            else:
                await mod_channel.send("⚠️ WARNING: Could not find votes channel!")
        except Exception as e:
            await mod_channel.send(f"❌ Error recording winner info: {e}")
        
        # Create winner info dict
        winner_info = {
            'name': winner_name,
            'link': winner_link
        }

        # FOURTH: Change the public channel name to Q&A
        try:
            await self.channel_config.change_name("aotw-q-a")
            await mod_channel.send("✅ Changed channel name to aotw-q-a")
        except Exception as e:
            await mod_channel.send(f"❌ Error changing channel name: {e}")

        # FIFTH: Purge the public voting/Q&A channel
        try:
            await self.channel_config.purge_channel()
            await mod_channel.send("✅ Purged voting channel")
        except Exception as e:
            await mod_channel.send(f"❌ Error purging channel: {e}")

        # SIXTH: Send announcement to the now-empty public channel
        try:
            await self.channel_config.submissions_channel.send("Determining our next Artist of the Week!")
            await mod_channel.send("✅ Sent announcement to submissions channel")
        except Exception as e:
            await mod_channel.send(f"❌ Error sending announcement: {e}")

        # SEVENTH: Create PRIVATE channel and send congrats message to winner
        try:
            winner_channel = await self.channel_config.send_message_to_winner(interaction, winner_info)
            await mod_channel.send(f"✅ Created winner channel: {winner_channel.name} (ID: {winner_channel.id})")
        except Exception as e:
            await mod_channel.send(f"❌ Error creating winner channel: {e}")
            await interaction.followup.send("❌ Error creating winner channel!")
            return
        
        # Get the winner as a Discord Member object
        winner_member = discord.utils.get(interaction.guild.members, display_name=winner_name)
        if not winner_member:
            for member in interaction.guild.members:
                if member.name == winner_name or member.display_name == winner_name:
                    winner_member = member
                    break
        
        if not winner_member:
            await mod_channel.send(f"❌ ERROR: Could not find member object for {winner_name}")
            await interaction.followup.send(f"⚠️ Warning: Could not find member {winner_name}. Listener may not work!")
            return
        
        await mod_channel.send(f"✅ Found winner member: {winner_member.name} (ID: {winner_member.id})")
        
        # EIGHTH: Start background listener for winner's response IN THE PRIVATE CHANNEL
        try:
            _task = asyncio.create_task(self.wait_for_winner_response(winner_info, winner_channel, winner_member))
            _task.add_done_callback(_log_task_error)
            await mod_channel.send(f"✅ Started listener for {winner_name} in channel {winner_channel.mention}")
            await interaction.followup.send(f"✅ AOTW Winner setup complete! Waiting for {winner_name}'s response in <#{winner_channel.id}>...")
        except Exception as e:
            await mod_channel.send(f"❌ Error creating listener task: {e}")
            await interaction.followup.send(f"⚠️ Setup complete but listener may not be active!")


    @app_commands.command(name ="initial_atow_message", description = "Post in Artist of the Week channel initial message")
    @app_commands.checks.has_permissions(administrator=True)
    async def initial_atow_message(self, interaction):

        await interaction.response.defer()
        mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)

        try:
            formatted_six_months = await self.channel_config.calculate_six_months()
            await self.channel_config.check_aotw_channel_announcement(formatted_six_months)
            await mod_channel.send("✅ Initial AOTW message posted")
        except Exception as e:
            await mod_channel.send(f"❌ Error posting initial AOTW message: {e}")
        
        await interaction.followup.send("✅ Initial AOTW message posted!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AOTWEvent(bot))