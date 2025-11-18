import discord
import asyncio
from data.constants import EVENT_VC, ITM_CHANNEL, ITM_ROLE, SUBMISSIONS_CHANNEL_ID, EVENT_CATEGORY, MOD_SUBMISSION_LOGGER_CHANNEL_ID, GENERAL_CHAT_CHANNEL_ID, MODERATORS_CHANNEL_ID #submissions_channel_id = event-text // mod_submission_logger_channel_id = event-submissions


class StartInTheMix:
    def __init__(self, bot):
        self.bot = bot

    async def send_announcement(self, interaction):
    
        guild = interaction.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)

        event_submissions = guild.get_channel(MOD_SUBMISSION_LOGGER_CHANNEL_ID)
        itm_channel = guild.get_channel(ITM_CHANNEL)
        event_category = guild.get_channel(EVENT_CATEGORY)
        event_text = guild.get_channel(SUBMISSIONS_CHANNEL_ID)
        event_vc = guild.get_channel(EVENT_VC)
        general_chat = guild.get_channel(GENERAL_CHAT_CHANNEL_ID)

        # make event?

        # purge the submissions channel
        try:
            await event_submissions.purge(limit=5)
            await mod_chat.send("✅ Purged submissions channel")
            await asyncio.sleep(0.5)
        except Exception as e:
            await mod_chat.send(f"❌ Failed to purge submissions channel: {e}")

        # clear the previous announcement
        try:
            # Only purge if there are messages
            messages = [msg async for msg in itm_channel.history(limit=1)]
            if messages:
                await itm_channel.purge(limit=1)
            await mod_chat.send("✅ Cleared previous ITM announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to clear ITM announcement: {e}")

        # change category name
        try:
            await event_category.edit(name="In-The-Mix")
            await mod_chat.send("✅ Changed category name")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to change category name: {e}")

        # open the channel view for everyone
        try:
            await itm_channel.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened ITM channel view")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open ITM channel view: {e}")

        # open event-text view for everyone
        try:
            await event_text.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened event-text view")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open event-text view: {e}")

        # open the vc view for everyone + change name
        try:
            await event_vc.edit(name="IN-THE-MIX")
            await event_vc.set_permissions(guild.default_role, view_channel=True)
            await mod_chat.send("✅ Opened VC and changed name")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to open VC/change name: {e}")

        # send announcement to itm event channel
        try:
            await itm_channel.send(
                f"<@&{ITM_ROLE}> is starting in 5 minutes!\n\n"
                f"Submissions are now **open** for next week's event. Use `?suggest (link)` in <#{SUBMISSIONS_CHANNEL_ID}> to get your song played!"
            )
            await mod_chat.send("✅ Sent ITM channel announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to send ITM announcement: {e}")

        # send message to general chat
        try:
            await general_chat.send(
                f"<@&{ITM_ROLE}> is starting in 5 minutes!\n\n"
                f"Submissions are now **open** for next week's event. Use `?suggest (link)` in <#{SUBMISSIONS_CHANNEL_ID}> to get your song played!"
            )
            await mod_chat.send("✅ Sent general chat announcement")
        except Exception as e:
            await mod_chat.send(f"❌ Failed to send general chat announcement: {e}")

    

    async def join_vc(self, interaction):

        guild = interaction.guild
        mod_chat = guild.get_channel(MODERATORS_CHANNEL_ID)

        try:
            guild = interaction.guild
            event_vc = guild.get_channel(EVENT_VC)

            await event_vc.connect()
            await mod_chat.send("✅ Bot joined VC")

        except Exception as e:
            await mod_chat.send(f"❌ Failed to join VC: {e}")