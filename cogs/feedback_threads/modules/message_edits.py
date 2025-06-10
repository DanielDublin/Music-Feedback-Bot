# import discord    
# import database.db as db
# from data.constants import FEEDBACK_ACCESS_CHANNEL_ID

# class MessageEdits:
#     def __init__(self, bot):
#         self.bot = bot

#     async def MFS_to_MFR_edit(self, before: discord.Message, after: discord.Message, formatted_time, message_link):
#             # Get the existing thread and ticket_counter
#             existing_thread, ticket_counter, base_timer_cog = await self.check_existing_thread_edit(after)

#             if "MFS" in before.content.upper() and "MFR" in after.content.upper():
#                 print("Processing MFS to MFR edit: Adding points.")
#                 if "Double Points" in base_timer_cog.timer_handler.active_timer:
#                     points_added = 3
#                 else:
#                     points_added = 2

#                 # Add points
#                 await db.add_points(str(after.author.id), points_added)

#                 # Update points after addition
#                 updated_points = await db.fetch_points(str(after.author.id))

#                 # Create the embed
#                 embed_title = "<MFS edited to <MFR"
#                 embed_description = f"Gained **{points_added}** points and now has **{updated_points}** MF points."

#                 # send information to user
#                 channel_message = await after.channel.send(
#                     f"{after.author.mention} edited their message from <MFS to <MFR and gained **{points_added}** MF Points. You now have **{updated_points}** MF Points."
#                     f"\n\nFor more information about the feedback commands, visit <#{FEEDBACK_CHANNEL_ID}>.")

#                 embed = await self.edit_embed(embed_title, formatted_time, embed_description, before, after, ticket_counter,
#                                 message_link)

#                 # sends message to channel + handles deletion, sends ticket to thread
#                 await asyncio.gather(
#                     self.thread_archive(existing_thread, embed),
#                     self.delete_channel_message_after_fail_edit(channel_message)
#                 )
#                 await asyncio.sleep(15)
#                 await channel_message.delete()