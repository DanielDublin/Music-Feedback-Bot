import discord
import datetime
import asyncio
from data.constants import AOTW_CHANNEL, AOTW_SUBMISSIONS, STAGEHANDS, SUPPORTING_ACTS, HEADLINERS, AOTW_ROLE, FANS, GROUPIES, GENERAL_CHAT_CHANNEL_ID, MODMAIL_CATEGORY_ID
from discord.ext import tasks

class ConfigureChannel:
    def __init__(self, bot):
        self.bot = bot
        self.submissions_channel = None
        self.aotw_channel = None
        self.guild = None

    async def initialize_channels(self):
        self.submissions_channel = self.bot.get_channel(AOTW_SUBMISSIONS)
        self.aotw_channel = self.bot.get_channel(AOTW_CHANNEL)
        if self.submissions_channel:
            self.guild = self.submissions_channel.guild

    async def check_aotw_channel_announcement(self, formatted_six_months):

        # INDENTS MATTER!
        message = f"""**Artist of the Week** is a biweekly event open to Stagehands, Supporting Acts, Headliners, and Moderators. The purpose of this event is to highlight a server member who has recently released an original song/cover.

If you have won Artist of the Week in the past two cycles (within the last month), you are not eligible to submit. Tracks that use AI are allowed to be submitted, but a disclaimer must be added alongside the post.

__AOTW perks:__
- 2 full weeks with the <@&{AOTW_ROLE}> role
- Priority at In-The-Mix
- Server-wide announcement
- Q&A session

*How it works:*
Submissions can be made to #aotw-voting upon announcement on Sunday until Thursday. A popular vote is held on Friday and Saturday. A winner is selected and required to provide a short bio with any important information or pictures related to their content.

For now, we will consider artists who have released new music-related content __since {formatted_six_months}__."""

        # Check if announcement exists
        found = False
        announcement_msg = None
        async for msg in self.aotw_channel.history(limit=10):
            if "**Artist of the Week** is a biweekly event" in msg.content:
                # Found announcement - update if date is outdated
                if msg.content != message:
                    await msg.edit(content=message)
                found = True
                announcement_msg = msg
                break
        
        # if no announcement found, send new one
        if not found:
            await self.aotw_channel.send(message)

    async def calculate_six_months(self):
        six_months = datetime.datetime.now() - datetime.timedelta(days=180)
        # six_months = six_months = datetime.datetime(2025, 3, 1)
        formatted_six_months = six_months.strftime("%B %Y")

        return formatted_six_months

    async def purge_channel(self):
        """Purge all messages from the submissions channel with rate limit handling"""
        try:
            # Purge handles bulk delete efficiently (messages < 14 days old)
            deleted = await self.submissions_channel.purge(limit=None)
            print(f"✅ Bulk deleted {len(deleted)} messages")
            
            # Check if there are any remaining messages (older than 14 days)
            remaining = []
            async for msg in self.submissions_channel.history(limit=10):
                remaining.append(msg)
            
            # If there are old messages, delete them individually with delays
            if remaining:
                print(f"⚠️ Found {len(remaining)} old messages (>14 days), deleting individually...")
                for msg in remaining:
                    try:
                        await msg.delete()
                        await asyncio.sleep(1)  # 1 second delay between deletes
                    except discord.HTTPException as e:
                        if e.status == 429:
                            print("⚠️ Rate limited, waiting 5 seconds...")
                            await asyncio.sleep(5)
                            await msg.delete()
                        else:
                            print(f"❌ Error deleting message: {e}")
                            
        except discord.HTTPException as e:
            if e.status == 429:
                print("⚠️ Rate limited on purge, waiting 60 seconds...")
                await asyncio.sleep(60)
                await self.purge_channel()  # Retry
            else:
                print(f"❌ Error purging channel: {e}") 
    
    async def change_name(self, command_name):
        # change aotw submissions/voting channel name and topic
        # submissions > voting > q-a > submissions
        
        if command_name == "aotw-q-a":
            try:
                await self.submissions_channel.edit(
                    name="aotw-q-a",
                    topic="Ask the current Artist of the Week anything about their music, creative process, or upcoming projects!")
                print("name changed to aotw-q-a")
            except Exception as e:
                print(f"Error changing name: {e}")
        
        elif command_name == "aotw-submissions":
            try:
                await self.submissions_channel.edit(
                    name="aotw-submissions",
                    topic="Submit a link to your finished music for the chance to become our next Artist of the Week! Submissions run Sunday-Thursday.")
                print("name changed to aotw-submissions")
            except Exception as e:
                print(f"Error changing name: {e}")
        
        elif command_name == "aotw-voting":
            print("name is aotw-submissions")
            try:
                await self.submissions_channel.edit(
                    name="aotw-voting",
                    topic="Vote for one of our Artists to become the next Artist of the Week! Voting is open Friday-Saturday. Winner announced Sunday.")
                print("name changed to aotw-voting")
            except Exception as e:
                print(f"Error changing name: {e}")


    async def send_submissions_announcement(self, formatted_one_week, formatted_two_weeks, formatted_six_months):
        # send to aotw submissions/poting

        if self.submissions_channel.name == "aotw-submissions":
        
            submissions_announcement = f"Hey <@&{STAGEHANDS}>, <@&{SUPPORTING_ACTS}>, and <@&{HEADLINERS}>!\n\nIt's time to start submitting to have the chance to become our next <@&{AOTW_ROLE}> ({formatted_one_week} - {formatted_two_weeks})! Please post your musical content released after the start of __{formatted_six_months}__. More info in <#{AOTW_CHANNEL}>.\n\nYou are not allowed to submit if you have won AOTW in the past two cycles (the last month).\n\nTracks that use AI are allowed to be submitted, but a disclaimer must be added alongside the post.\n\n*Submissions run from Sunday-Thursday; voting takes place Friday-Saturday. AOTW is announced the following Sunday.*"

            await self.submissions_channel.send(submissions_announcement)

    async def send_voting_announcement(self):

        # INDENTS MATTER!
        voting_announcement = """**SUBMISSIONS ARE CLOSED\nVOTING IS NOW OPEN!!!**

Please select an option in the above anonymous poll to vote for your favorite

__Voting Guidelines:__
1. You may only vote once.
2. You are not allowed to vote for yourself.
3. If found manipulating votes, you will be kicked from the server."""

        await self.submissions_channel.send(voting_announcement)

    async def calculate_two_weeks(self):
        date_today = datetime.date.today()
        # win in a week from when submissions open, then they have the role for 2 weeks 
        date_one_week = date_today + datetime.timedelta(days=7)
        date_two_weeks = date_today + datetime.timedelta(days=20)

        formatted_one_week = date_one_week.strftime("%B %d, %Y")
        formatted_two_weeks = date_two_weeks.strftime("%B %d, %Y")

        return formatted_one_week, formatted_two_weeks
    
    async def change_submissions_perms(self):
        # set FANS send messages to OFF
        # await self.submissions_channel.set_permissions(self.guild.get_role(FANS), send_messages=False, view_channel=True, embed_links=False, attach_files=False, add_reactions=False, use_external_emojis=False, use_external_stickers=False, use_external_apps=False)

        # # set GROUPIES send messages to OFF
        # await self.submissions_channel.set_permissions(self.guild.get_role(GROUPIES), send_messages=False, view_channel=True, embed_links=False, attach_files=False, add_reactions=False, use_external_emojis=False, use_external_stickers=False, use_external_apps=False)

        # # set EVERYONE add reactions, external emoji, external stickers OFF
        # # add pin_messages = False once supported by Discord version
        # await self.submissions_channel.set_permissions(self.guild.default_role, add_reactions=False, use_external_emojis=False, use_external_stickers=False, view_channel=True, send_messages=True, embed_links=True, attach_files=True, mention_everyone=False, manage_messages=False, use_external_apps=False)

        # FANS - disable send_messages only
        fans_overwrite = self.submissions_channel.overwrites_for(self.guild.get_role(FANS))
        fans_overwrite.send_messages = False
        await self.submissions_channel.set_permissions(self.guild.get_role(FANS), overwrite=fans_overwrite)

        # GROUPIES - disable send_messages only
        groupies_overwrite = self.submissions_channel.overwrites_for(self.guild.get_role(GROUPIES))
        groupies_overwrite.send_messages = False
        await self.submissions_channel.set_permissions(self.guild.get_role(GROUPIES), overwrite=groupies_overwrite)

        # EVERYONE - disable reactions and external emojis/stickers only
        everyone_overwrite = self.submissions_channel.overwrites_for(self.guild.default_role)
        everyone_overwrite.add_reactions = False
        everyone_overwrite.use_external_emojis = False
        everyone_overwrite.use_external_stickers = False
        everyone_overwrite.send_messages = True
        await self.submissions_channel.set_permissions(self.guild.default_role, overwrite=everyone_overwrite)


    async def change_voting_perms(self):
        # set EVERYONE send messages to OFF
        # set EVERYONE add reactions, external emoji, external stickers OFF
        # await self.submissions_channel.set_permissions(self.guild.default_role, send_messages=False, add_reactions=False, use_external_emojis=False, use_external_stickers=False)


            # Get existing overwrite for @everyone
        everyone_overwrite = self.submissions_channel.overwrites_for(self.guild.default_role)
        
        # Set EVERYONE send messages to OFF
        # Set EVERYONE add reactions, external emoji, external stickers OFF
        everyone_overwrite.send_messages = False
        everyone_overwrite.add_reactions = False
        everyone_overwrite.use_external_emojis = False
        everyone_overwrite.use_external_stickers = False
        
        await self.submissions_channel.set_permissions(self.guild.default_role, overwrite=everyone_overwrite)


    async def check_for_not_links(self):
        # delete any messages that have a file attached (aotw accepts links only)
        messages = [msg async for msg in self.submissions_channel.history(limit=100)]
        for msg in messages:
            if msg.attachments:
                await msg.delete()

    async def schedule_voting_event(self):

        # delay or else it's in the past
        start_time = discord.utils.utcnow() + datetime.timedelta(minutes=2)
        end_time = start_time + datetime.timedelta(days=2)

        event = await self.guild.create_scheduled_event(
        name="VOTING OPEN - Artist of the Week",
        description="Vote for your favorite artist! Check #aotw-voting to cast your vote anonymously.",
        start_time=start_time,
        end_time=end_time,
        entity_type=discord.EntityType.external,
        # get the link to the voting channel
        location="aotw-voting channel",
        privacy_level=discord.PrivacyLevel.guild_only
        )

        return event
    
    async def end_voting_event(self):

        for event in self.guild.scheduled_events:
            if "Artist of the Week" in event.name and event.status == discord.EventStatus.active:
                await event.edit(
                    end_time=discord.utils.utcnow(),
                    status=discord.EventStatus.completed
                )
                break

    async def schedule_general_chat_reminders(self):
        channel = self.guild.get_channel(GENERAL_CHAT_CHANNEL_ID)

        embed = discord.Embed(
            title="VOTING OPEN - Artist of the Week",
            description="Votings are open! Check #aotw-voting to vote for your favorite artist!",
            color=discord.Color.blue()
        )

        # # send message immediatel when voting opens
        # await channel.send(embed=embed)

        # start reminder loop
        if not self.voting_reminder_task.is_running():
            self.voting_reminder_task.start()

    async def end_aotw_event(self):
        for event in self.guild.scheduled_events:
            if "Artist of the Week" in event.name and event.status == discord.EventStatus.active:
                try:
                    await event.edit(status=discord.EventStatus.completed)
                    print("✅ Ended AOTW voting event")
                except discord.HTTPException as e:
                    print(f"❌ Error ending event: {e}")
                break
    
    @tasks.loop(hours=12)
    async def voting_reminder_task(self):
        # send reminder every 24 hours in chat
        channel = self.bot.get_channel(GENERAL_CHAT_CHANNEL_ID)
        
        embed = discord.Embed(
            title="VOTING IS OPEN!",
            description=f"Don't forget to vote! Check <#{AOTW_SUBMISSIONS}> to cast your vote!",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
    
    def stop_voting_reminders(self):
        """Stop reminders when voting ends"""
        if self.voting_reminder_task.is_running():
            self.voting_reminder_task.cancel()

    async def send_message_to_winner(self, interaction, winner):

        print("Sending message to winner")
        guild = interaction.guild

        print(guild)
        channel_name = f"{winner['name']}-AOTW"
        print("channel name:", channel_name)

        category = guild.get_channel(MODMAIL_CATEGORY_ID)

        new_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            reason=f"Channel created for Artist of the Week: {winner['name']}"
        )
        print("channel created")

        # Find the winner member object to create a proper mention
        winner_member = discord.utils.get(guild.members, display_name=winner['name'])
        if not winner_member:
            winner_member = discord.utils.get(guild.members, name=winner['name'])
        if not winner_member:
            for member in guild.members:
                if member.name == winner['name'] or member.display_name == winner['name']:
                    winner_member = member
                    break
        
        # Use mention if found, otherwise use plain name
        if winner_member:
            winner_mention = winner_member.mention
        else:
            winner_mention = winner['name']
            print(f"⚠️ WARNING: Could not find member {winner['name']} to mention")

        message = f"# Congratulations {winner_mention} for winning Artist of the Week!\n\nWhen you can, could you please give a little more information about the release? What were some of your inspirations and thoughts behind the project? What else are you planning to release in the future?\n\nFeel free to provide links to your socials as well!"

        # send the congrats message to the channel
        await new_channel.send(message)

        print("message sent, channel:", new_channel)

        # return new channel so that listener can wait for it
        return new_channel

    async def aotw_winner_announcement(self, votes_channel_id, message):
        """
        Fetch winner info from votes channel and post announcement
        votes_channel_id: The ID of the aotw-votes channel
        message: The winner's bio message from their private channel
        """
        
        # Fetch winner info from aotw-votes channel
        votes_channel = self.bot.get_channel(votes_channel_id)
        winner_name = None
        winner_link = None
        
        if votes_channel:
            async for msg in votes_channel.history(limit=1):
                # Parse the most recent message to get winner info
                if "**WINNER:**" in msg.content:
                    lines = msg.content.split('\n')
                    for line in lines:
                        if "**WINNER:**" in line:
                            winner_name = line.replace("**WINNER:**", "").strip()
                        elif "**Link:**" in line:
                            # Extract everything after "**Link:**"
                            link_content = line.replace("**Link:**", "").strip()
                            
                            # Find URL in the content (look for http:// or https://)
                            import re
                            url_pattern = r'(https?://[^\s]+)'
                            url_match = re.search(url_pattern, link_content)
                            
                            if url_match:
                                winner_link = url_match.group(1)
                            else:
                                # If no URL found, use the whole content
                                winner_link = link_content
                    break
        
        if not winner_name:
            print("⚠️ WARNING: Could not find winner info in votes channel")
            return
        
        # Find the winner member object to create a proper mention
        winner_member = discord.utils.get(self.guild.members, display_name=winner_name)
        if not winner_member:
            winner_member = discord.utils.get(self.guild.members, name=winner_name)
        if not winner_member:
            for member in self.guild.members:
                if member.name == winner_name or member.display_name == winner_name:
                    winner_member = member
                    break
        
        # Use mention if found, otherwise use plain name
        if winner_member:
            name_mention = winner_member.mention
        else:
            name_mention = winner_name
            print(f"⚠️ WARNING: Could not find member {winner_name} to mention")

        await self.aotw_channel.send(f"""**Say congrats to our <@&{AOTW_ROLE}>, {name_mention}!!!**
                                    
    Here is a statement from our artist:
                                    
    {message.content}                              
                                    
    {winner_link}""")

    async def qa_announcement(self, name):
        
        # Find the winner member object to create a proper mention
        winner_member = discord.utils.get(self.guild.members, display_name=name)
        if not winner_member:
            winner_member = discord.utils.get(self.guild.members, name=name)
        if not winner_member:
            for member in self.guild.members:
                if member.name == name or member.display_name == name:
                    winner_member = member
                    break
        
        # Use mention if found, otherwise use plain name
        if winner_member:
            name_mention = winner_member.mention
        else:
            name_mention = name
            print(f"⚠️ WARNING: Could not find member {name} to mention")

        await self.submissions_channel.send(f"@here Say congrats to our <@&{AOTW_ROLE}>, {name_mention}!!! Use this channel to ask them any questions about their music (winning track and artist bio in <#{AOTW_CHANNEL}>)!", allowed_mentions=discord.AllowedMentions(everyone=True))

    async def winner_perms(self):

        # set groupies, fans, and everyone send messages to ON
        # await self.aotw_channel.set_permissions(self.guild.get_role(GROUPIES), send_messages=True)
        # await self.aotw_channel.set_permissions(self.guild.get_role(FANS), send_messages=True)
        # await self.aotw_channel.set_permissions(self.guild.default_role, send_messages=True)
        # # reactions on for everyone
        # await self.aotw_channel.set_permissions(self.guild.default_role, add_reactions=True)
        # await self.aotw_channel.set_permissions(self.guild.default_role, use_external_emojis=True)
        # await self.aotw_channel.set_permissions(self.guild.default_role, use_external_stickers=True)

        # Get existing overwrites for each role
        groupies_overwrite = self.submissions_channel.overwrites_for(self.guild.get_role(GROUPIES))
        groupies_overwrite.send_messages = True
        
        fans_overwrite = self.submissions_channel.overwrites_for(self.guild.get_role(FANS))
        fans_overwrite.send_messages = True
        
        everyone_overwrite = self.submissions_channel.overwrites_for(self.guild.default_role)
        everyone_overwrite.send_messages = True
        everyone_overwrite.add_reactions = True
        everyone_overwrite.use_external_emojis = True
        everyone_overwrite.use_external_stickers = True
        
        # Set groupies, fans, and everyone send messages to ON
        await self.submissions_channel.set_permissions(self.guild.get_role(GROUPIES), overwrite=groupies_overwrite)
        await self.submissions_channel.set_permissions(self.guild.get_role(FANS), overwrite=fans_overwrite)
        # Reactions on for everyone
        await self.submissions_channel.set_permissions(self.guild.default_role, overwrite=everyone_overwrite)

    async def remove_aotw_role(self, interaction):

        aotw_role = discord.utils.get(interaction.guild.roles, name="Artist of the Week")
        if aotw_role:
            for member in interaction.guild.members:
                if aotw_role in member.roles:
                    try:
                        await member.remove_roles(aotw_role)
                        print(f"✅ Removed AOTW role from {member.name}")
                    except Exception as e:
                        print(f"❌ Failed to remove role from {member.name}: {e}")
        else:
            print(f"⚠️ AOTW role '{AOTW_ROLE}' not found")