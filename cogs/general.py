from os import makedirs
import discord
from discord.ext import commands
from datetime import datetime
import database.db as db
from data.constants import FEEDBACK_CHANNEL_ID, FEEDBACK_ACCESS_CHANNEL_ID, SERVER_OWNER_ID


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # MF points - Shows how many points the current user has
    @commands.command(aliases=["balance"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def points(self, ctx: discord.Message, user: discord.Member = None):

        # Gathering data
        if user is None:
            user = ctx.author

        guild = ctx.guild
        points = await db.fetch_points(str(user.id))
        rank = await db.fetch_rank(str(user.id))
        pfp = user.avatar.url
        
        msg_out1 = f"You have **{points}** MF point(s)."
        msg_out2 = f"Your MF Rank is **#{rank}** out of **{guild.member_count}**."
        if ctx.author.id != user.id:
            msg_out1 = f"{user.mention} has **{points}** MF point(s)."
            msg_out2 = f"Their MF Rank is **#{rank}** out of **{guild.member_count}**."

        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name=f"Music Feedback: {user.display_name}", icon_url=guild.icon.url)
        embed.set_thumbnail(url=pfp)
        embed.add_field(name="__MF Points__", value=msg_out1, inline=False)
        embed.add_field(name="__MF Rank__", value=msg_out2,
                        inline=False)
        embed.timestamp = datetime.now()
        await ctx.channel.send(embed=embed)

    # MF leaderboard
    @commands.command(aliases=["leaderboard"])
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def top(self, ctx: discord.Member):

        top_users = await db.fetch_top_users()
        guild = ctx.guild
        names = ''
        avatar = guild.icon.url

        for user_id, user_data in top_users.items():
            rank = user_data["rank"]
            points = user_data["points"]
            names += f"{rank} - <@{user_id}> | **{points}** MF point(s)\n"

            if rank == 1:
                user = discord.utils.get(guild.members, id=int(user_id))
                if user is not None:
                    avatar = user.avatar.url

        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name="Top Music Feedbackers", icon_url=guild.icon.url)
        embed.add_field(name="Members", value=names, inline=False)
        embed.set_thumbnail(url=avatar)
        await ctx.channel.send(embed=embed)

        # Add points

    @commands.command(name="R")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def MFR_command(self, ctx: discord.Message):

        await db.add_points(str(ctx.author.id), 1)
        mention = ctx.author.mention
        points = int(await db.fetch_points(str(ctx.author.id)))
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(name="Feedback Notice",
                        value=f"{mention} has **given feedback** and now has **{points}** MF point(s).", inline=False)

        await ctx.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).",
                               delete_after=4)
        await channel.send(embed=embed)  # Logs channel



    async def send_messages_to_user(self, message: discord.Message):
        out_message = "Hey, you've run into an error when submitting for feedback.\n"\
                      "Make sure you are using the correct bot commands.\n"\
                      "> <MFR is for giving feedback\n"\
                      "> <MFS is for submitting feedback\n"\
                      "_THIS IS A 1-for-1 SYSTEM AND **__YOU MUST GIVE FEEDBACK FIRST TO GET FEEDBACK__**_\n"\
                      "\nRe-read the #Feedback-Access (https://discord.com/channels/732355624259813531/953764384495251477/959150439692128277) "\
                      "for more information or contact the Moderators.\n"\
                      "\n**Here is a copy of the message that was deleted:**\n"

        await message.author.send(out_message, suppress_embeds=True)
        await message.author.send(f"```{message.content}```")


    # Use points
    @commands.command(name="S")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def MFs_command(self, ctx: discord.Message):

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        points = int(await db.fetch_points(str(ctx.author.id)))
        mention = ctx.author.mention

        if points:  # user have points, reduce them and send message + log
            points -= 1
            await db.reduce_points(str(ctx.author.id), 1)
            await ctx.channel.send(f"{mention} have used 1 MF point. You now have **{points}** MF point(s).",
                                   delete_after=4)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="Feedback Notice",
                            value=f"{mention} has **submitted** a work for feedback and now"
                                  f" has **{points}** MF point(s).",
                            inline=False)
            await channel.send(embed=embed)

        else:  # User doesn't have points

            try:
                
                await self.send_messages_to_user(ctx.message)
                await ctx.channel.send(
                    f"{mention}, you do not have any MF points."
                    f" Please give feedback first.\nYour request was DMed to you for future"
                    f" reference. Please re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions.",
                    delete_after=60)
            except Exception:
                await ctx.channel.send(f'{mention}, you do not have any MF points. Please give feedback first.'
                                       f'\n**ATTENTION**: _We could not DM you with a copy of your submission.'
                                       f'\n Please contact Moderators for help or re-read'
                                       f' <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions._',
                                       delete_after=60)

            await ctx.message.delete()
            await channel.send(f"<@{SERVER_OWNER_ID}>:")

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name="**ALERT**",
                            value=f"{mention} tried sending a track for feedback with **0** MF points.", inline=False)
            await channel.send(embed=embed)

    
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def creator(self, ctx: discord.Member):
        out_msg = f"Ask FlamingCore / Officer Toast.\nCome on then, Ping him.\n**I dare you**.\n"
        await ctx.channel.send(out_msg)

async def setup(bot):
    await bot.add_cog(General(bot))
