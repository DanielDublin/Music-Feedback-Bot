import database.db as db
from .embeds import Embeds
import discord
from data.constants import ADMINS_ROLE_ID

class PointsLogic:
    def __init__(self, bot, user_thread, ctx=None):
        self.bot = bot
        self.user_thread = user_thread
        self.ctx = ctx
        self.embeds = Embeds(bot, user_thread)

    # async def send_embed_new_thread():
    #     pass

    async def send_embed_existing_thread(self, user_id=None, ticket_counter=None, thread=None, called_from_zero=False):
        if user_id is None:
            user_id = self.ctx.author.id
            print("user_id is None")

        if ticket_counter is None:
            ticket_counter = self.user_thread.get(self.ctx.author.id, [None, 0])[1]
            print("ticket_counter is None")

        points = await db.fetch_points(str(user_id))

        print(f"{called_from_zero}")

        if called_from_zero:
            print("called_from_zero")
            try:
                await self.handle_zero_points_submission(self.ctx, thread, ticket_counter)
            except Exception as e:
                await self.ctx.send(f"An error occurred: {str(e)}")
            return

    async def handle_zero_points_submission(self, ctx, thread, ticket_counter):

        embed = await self.embeds.mfs_with_zero_points(ctx, ticket_counter, thread)
        await thread.send(f"<@&{ADMINS_ROLE_ID}>")
        await thread.send(embed=embed)

