import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from cogs.aotw.create_poll import CreatePoll
from cogs.aotw.configure_channel import ConfigureChannel
from data.constants import AOTW_CHANNEL, AOTW_SUBMISSIONS, MODERATORS_CHANNEL_ID, AOTW_ROLE, AOTW_VOTES


class AOTWEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def wait_for_winner_response(self, winner_info, winner_channel, winner_member):
        """
        Listens for the winner's response in their private channel
        winner_channel: The newly created private channel for the winner
        winner_member: The Discord Member object of the winner
        """
        # Give the winner permissions to see and use the channel
        try:
            await winner_channel.set_permissions(winner_member, view_channel=True, send_messages=True)
            print(f"✅ Set permissions for {winner_member.name} in {winner_channel.name}")
        except Exception as e:
            print(f"❌ Error setting permissions: {e}")
        
        def check(m):
            # Check if message is from the winner in their private channel
            print(f"Check triggered: channel={m.channel.id}, author={m.author.name}, bot={m.author.bot}")
            return (
                m.channel.id == winner_channel.id and  # Check the WINNER'S channel
                not m.author.bot and
                m.author.id == winner_member.id  # Use member ID for reliable matching
            )
        
        try:
            print(f"⏳ Waiting for {winner_member.name}'s response in channel {winner_channel.id}...")
            # Wait for winner to respond in their private channel
            message = await self.bot.wait_for('message', check=check, timeout=86400.0)  # 24 hours
            
            print(f"✅ Winner {message.author.name} responded: {message.content[:50]}...")  # Debug log
            
            # Notify moderators
            mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(
                    f"AOTW NOTICE - **{message.author}** sent a message in <#{message.channel.id}>: {message.content}"
                )

            # give AOTW role
            aotw_role = message.guild.get_role(AOTW_ROLE)
            await message.author.add_roles(aotw_role)

            await message.reply("Thank you! And congrats again on winning Artist of the Week!")
            
            # Continue configuring the AOTW system
            config = ConfigureChannel(self.bot)
            await config.initialize_channels()

            # delete the previous message in aotw channel
            try:
            # Get the last message in the AOTW announcement channel
                async for msg in config.aotw_channel.history(limit=1):
                    await msg.delete()
                    print("✅ Deleted previous message from AOTW channel")
                    break
            except Exception as e:
                print(f"❌ Error deleting message from AOTW channel: {e}")

            # Delete the aotw-q-a channel (the public submissions channel)
            await config.purge_channel()

            # Change permissions for Q&A
            await config.winner_perms()

            # Post the announcement in aotw channel
            await config.aotw_winner_announcement(config.aotw_channel, winner_info['name'], winner_info['link'], message)

            # Announce Q&A channel
            await config.qa_announcement(config.submissions_channel, winner_info['name'])

            
        except asyncio.TimeoutError:
            print(f"Winner {winner_info['name']} didn't respond within 24 hours")
            # Optionally notify mods
            mod_channel = self.bot.get_channel(MODERATORS_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(f"⚠️ AOTW winner {winner_info['name']} didn't respond within 24 hours!")

    @app_commands.command(name = "aotw_voting", description = "Setup poll and channels for AOTW voting")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_voting(self, interaction):

        channel_id = AOTW_SUBMISSIONS

        await interaction.response.defer()
        config = ConfigureChannel(self.bot)

        await config.initialize_channels()

        # # check aotw_channel announcement and post
        # formatted_six_months = await config.calculate_six_months()
        # await config.check_aotw_channel_announcement(formatted_six_months)

        # change perms for aotw submissions
        await config.change_voting_perms()

        # change name + topic to aotw_voting
        await config.change_name("aotw-voting")

        # delete any messages with a file
        await config.check_for_not_links()

        # create the poll in aotw submissions
        poll = CreatePoll(self.bot)
        try:
            names = await poll.scrape_channel_for_names(interaction, channel_id)
            embed, emojis = await poll.create_embed(interaction, names)
            await poll.react_to_embed(interaction, embed, emojis, names)
            print("Poll created")
        except Exception as e:
            print(f"Error creating poll: {e}")

        # send announcement under poll
        await config.send_voting_announcement()

        # create event for voting
        await config.schedule_voting_event()

        # reminders for gen chat
        await config.schedule_general_chat_reminders()

        await interaction.followup.send("✅ AOTW Voting setup complete!", ephemeral=True)


    @app_commands.command(name = "aotw_submissions", description = "Setup poll and channels for AOTW submissions")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_submissions(self, interaction):

        channel_id = AOTW_SUBMISSIONS

        await interaction.response.defer()
        config = ConfigureChannel(self.bot)

        try:
            await config.initialize_channels()
            print("Channels initialized")
        except Exception as e:
            print(f"Error initializing channels: {e}")

        # check aotw_channel announcement and post
        try:
            formatted_six_months = await config.calculate_six_months()
            await config.check_aotw_channel_announcement(formatted_six_months)
            print("AOTW channel announcement checked")
        except Exception as e:
            print(f"Error checking aotw_channel announcement: {e}")

        try:
            # purge aotw submissions
            await config.purge_channel()
            print("AOTW submissions purged")
        except Exception as e:
            print(f"Error purging aotw submissions: {e}")

        try:
            # rename to aotw submissions + topic
            await config.change_name("aotw-submissions")
            print("Name changed")
        except Exception as e:
            print(f"Error changing name: {e}")

        try:
            # change perms
            await config.change_submissions_perms()
            print("Perms changed")
        except Exception as e:
            print(f"Error changing perms: {e}")

        try:
            # post submissions announcement
            formatted_one_week, formatted_two_weeks = await config.calculate_two_weeks()
            await config.send_submissions_announcement(formatted_one_week, formatted_two_weeks, formatted_six_months)
            print("Submissions announcement sent")
        except Exception as e:
            print(f"Error sending submissions announcement: {e}")

        await interaction.followup.send("✅ AOTW Submissions setup complete!", ephemeral=True)

    @app_commands.command(name = "aotw_winner", description = "Setup poll and channels for AOTW winner")
    @app_commands.checks.has_permissions(administrator=True)
    async def aotw_winner(self, interaction):

        await interaction.response.defer()
        config = ConfigureChannel(self.bot)

        try:
            await config.initialize_channels()
            print("Channels initialized")
        except Exception as e:
            print(f"Error initializing channels: {e}")

        # remove role from current AOTW
        await config.remove_aotw_role(interaction)

        # Create poll instance
        poll = CreatePoll(self.bot)

        # FIRST: Scrape channel to get all submissions with links BEFORE purging
        try:
            names = await poll.scrape_channel_for_names(interaction, AOTW_SUBMISSIONS)
            print(f"Scraped {len(names)} submissions")
            print(f"Messages dict: {poll.messages}")  # Debug
        except Exception as e:
            print(f"Error scraping channel: {e}")
            await interaction.followup.send("❌ Error reading submissions!")
            return

        # SECOND: Determine the winner from votes
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

        # THIRD: Get the winner's link from scraped data
        winner_link = poll.messages.get(winner_name, "No link provided")
        print(f"Winner: {winner_name}, Link: {winner_link}")
        
        # Send to votes channel for record keeping
        votes_channel = self.bot.get_channel(1429975150039924806)
        if votes_channel:
            await votes_channel.send(f"**WINNER:** {winner_name}\n**Link:** {winner_link}\n**Votes:** {max_votes}")
            print("✅ Sent winner info to votes channel")
        else:
            print("⚠️ WARNING: Could not find votes channel!")
        
        # Create winner info dict
        winner_info = {
            'name': winner_name,
            'link': winner_link
        }

        # FOURTH: Change the public channel name to Q&A
        await config.change_name("aotw-q-a")

        # FIFTH: Purge the public voting/Q&A channel
        await config.purge_channel()

        # dont need to change perms because everyone has no messages from voting

        # SIXTH: Send announcement to the now-empty public channel
        await config.submissions_channel.send("Determining our next Artist of the Week!")

        # SEVENTH: Create PRIVATE channel and send congrats message to winner
        winner_channel = await config.send_message_to_winner(interaction, winner_info)
        print(f"✅ Created winner channel: {winner_channel.name} (ID: {winner_channel.id})")
        
        # Get the winner as a Discord Member object
        winner_member = interaction.guild.get_member_named(winner_name)
        if not winner_member:
            # Try finding by display name or searching through members
            winner_member = discord.utils.get(interaction.guild.members, name=winner_name)
        
        if not winner_member:
            # Last resort: search through all members
            for member in interaction.guild.members:
                if member.name == winner_name or member.display_name == winner_name:
                    winner_member = member
                    break
        
        if not winner_member:
            print(f"❌ ERROR: Could not find member object for {winner_name}")
            await interaction.followup.send(f"⚠️ Warning: Could not find member {winner_name}. Listener may not work!")
            return
        
        print(f"✅ Found winner member: {winner_member.name} (ID: {winner_member.id})")
        
        # EIGHTH: Start background listener for winner's response IN THE PRIVATE CHANNEL
        try: 
            asyncio.create_task(self.wait_for_winner_response(winner_info, winner_channel, winner_member))
            print(f"✅ Started listener for {winner_name} in channel {winner_channel.id}")
            await interaction.followup.send(f"✅ AOTW Winner setup complete! Waiting for {winner_name}'s response in <#{winner_channel.id}>...")
        except Exception as e:
            print(f"❌ Error creating listener task: {e}")
            await interaction.followup.send(f"⚠️ Setup complete but listener may not be active!")


    @app_commands.command(name ="initial_atow_message", description = "Post in Artist of the Week channel initial message")
    @app_commands.checks.has_permissions(administrator=True)
    async def initial_atow_message(self, interaction):

        await interaction.response.defer()

        config = ConfigureChannel(self.bot)

        await config.check_aotw_channel_announcement()
        
        await interaction.followup.send("✅ Initial AOTW message posted!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AOTWEvent(bot))