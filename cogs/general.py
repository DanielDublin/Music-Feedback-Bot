import discord
from discord.ext import commands
from database.db import init_database


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def add_points(self, ctx, points: int):
        """Add points to a user."""
        pool = await init_database()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                user_id = ctx.author.id
                await cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = await cursor.fetchone()
                if user:
                    new_points = user['points'] + points
                    await cursor.execute("UPDATE users SET points = %s WHERE id = %s", (new_points, user_id))
                else:
                    await cursor.execute("INSERT INTO users (id, name, points) VALUES (%s, %s, %s)", (user_id, ctx.author.display_name, points))

        await ctx.send(f"You now have {new_points} points!")

def setup(bot):
    bot.add_cog(General(bot))