from os import makedirs
import discord
from discord.ext import commands
from datetime import datetime
import database.db as db
from data.constants import FEEDBACK_CHANNEL_ID, FEEDBACK_ACCESS_CHANNEL_ID, SERVER_OWNER_ID, FEEDBACK_CATEGORY_ID
from modules.genres import fetch_band_genres
from modules.similar_bands import fetch_similar_bands
from cogs.feedback_threads.modules.helpers import DiscordHelpers
from cogs.feedback_threads.modules.points_logic import PointsLogic
from cogs.feedback_threads.modules.threads_manager import ThreadsManager


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pfp_url =""
        self.helpers = DiscordHelpers(self.bot)
        self.deleted_messages = set() # store the messages deleted when mfs with 0 points

        
    def guild_only(ctx):
        return ctx.guild is not None
    

    async def handle_feedback_command_validity(self, ctx, mention):
        
        if ctx.channel.category is None or ctx.channel.category_id != FEEDBACK_CATEGORY_ID:  #  checks if its the right channels
            try:
                
                await self.send_messages_to_user(ctx.message)
                await ctx.channel.send(
                    f"{mention}, please use the correct channel to give feedback.\nYour request was DMed to you for future"
                    f" reference.\nPlease re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions.",
                    delete_after=60)
                await ctx.message.delete()
                return False
            except Exception:
                await ctx.channel.send(f'{mention}, you did not use the correct channel to use feedback.'
                                       f'\n**ATTENTION**: _We could not DM you with a copy of your submission.'
                                       f'\nPlease contact Moderators for help or re-read'
                                       f' <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions._',
                                       delete_after=60)
                await ctx.message.delete()
                return False
                

        if '<mfr' in ctx.message.content.lower().replace(' ','') and '<mfs' in ctx.message.content.lower().replace(' ',''):  # checks if no mfs + mfr
            try:
                
                await self.send_messages_to_user(ctx.message)
                await ctx.channel.send(
                    f'{mention}, you posted the commands in the wrong format, '
                    f'``<MFR`` and ``<MFS`` are 2 different commands.\nPlease repost them separately. Your request was DMed to you for future'
                    f" reference.\nPlease re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions.",
                    delete_after=60)
                await ctx.message.delete()
                return False
            except Exception:
                await ctx.channel.send(f'{mention}, you posted the commands in the wrong format, '
                                       f'``<MFR`` and ``<MFS`` are 2 different commands.'
                                       f'\n**ATTENTION**: _We could not DM you with a copy of your submission.'
                                       f'\nPlease contact Moderators for help or re-read'
                                       f' <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions._',
                                       delete_after=60)  
                await ctx.message.delete()
                return False
            
        return True

    # MF points - Shows how many points the current user has
    @commands.check(guild_only)
    @commands.command(help = f"Use to check how many MF points you have.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def points(self, ctx: discord.Message, user: discord.Member = None):

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

        # Gathering data
        if user is None:
            user = ctx.author

        guild = ctx.guild
        points = await db.fetch_points(str(user.id))
        rank = await db.fetch_rank(str(user.id))
        pfp = user.display_avatar.url
        
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
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await ctx.channel.send(embed=embed)

    # MF leaderboard
    @commands.check(guild_only)
    @commands.command(aliases=["leaderboard"],
                      help = f"(Use to see the leaderboard.")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def top(self, ctx: discord.Member):
        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url

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
                    avatar = user.display_avatar.url

        embed = discord.Embed(color=0x7e016f)
        embed.set_author(name="Top Music Feedbackers", icon_url=guild.icon.url)
        embed.add_field(name="Members", value=names, inline=False)
        embed.set_thumbnail(url=avatar)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await ctx.channel.send(embed=embed)

        # Add points
    @commands.check(guild_only)
    @commands.command(name="R",
                      help = f"Use to submit feedback.", brief = "@username")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def MFR_command(self, ctx: discord.Message):

        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            

        mention = ctx.author.mention    
        if not await self.handle_feedback_command_validity(ctx, mention):
            return

        await db.add_points(str(ctx.author.id), 1)
        
        points = int(await db.fetch_points(str(ctx.author.id)))
        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID) # feedback log channel

        await ctx.channel.send(f"{mention} has gained 1 MF point. You now have **{points}** MF point(s).", delete_after=4)

        # load cog needed to use variables
        feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx)

        await feedback_cog.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)

        thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)

        embed = discord.Embed(color=0x7e016f)
        embed.add_field(
            name=f"Feedback Notice - {self.helpers.get_formatted_time()}",
            value=(
                f"{mention} has **given feedback** and now has **{points}** MF point(s).\n\n"
                f"🔗 [Feedback Reply]({ctx.message.jump_url})\n"
                f"🟢 [Ticket #{ticket_counter}]({thread.jump_url})"
            ),
            inline=False
)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
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
    @commands.check(guild_only)
    @commands.command(name="S",
                      help = f"Use to ask for feedback.", brief = "(link, file, text)")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def MFs_command(self, ctx: discord.Message):


        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            

        mention = ctx.author.mention    
        if not await self.handle_feedback_command_validity(ctx, mention):
            return
        

        channel = self.bot.get_channel(FEEDBACK_CHANNEL_ID)
        points = int(await db.fetch_points(str(ctx.author.id)))

        # load cog needed to use variables
        feedback_cog, user_thread, sqlitedatabase = await self.helpers.load_threads_cog(ctx)

        if points:  # user have points, reduce them and send message + log

            points -= 1
            await db.reduce_points(str(ctx.author.id), 1)
            await ctx.channel.send(f"{mention} have used 1 MF point. You now have **{points}** MF point(s).",
                                   delete_after=4)
            
            # Check if user has a feedback thread
            # Called_from_zero used to flag if the member is using <MFS with no points
            await feedback_cog.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=False)

            thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(name=f"Feedback Notice - {self.helpers.get_formatted_time()}",
                            value=(
                                f"{mention} has **submitted** a work for feedback and now has **{points}** MF point(s).\n\n"
                                f"🔗 [Feedback Submission]({ctx.message.jump_url})\n"
                                f"🔴 [Ticket #{ticket_counter}]({thread.jump_url})"
                            ),
                            inline=False)
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=embed)

        else:  # User doesn't have points

            try:
                
                await self.send_messages_to_user(ctx.message)

                await ctx.channel.send(
                    f"{mention}, you do not have any MF points."
                    f" Please give feedback first.\nYour request was DMed to you for future"
                    f" reference.\nPlease re-read <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions.",
                    delete_after=60)
            except Exception:
                await ctx.channel.send(f'{mention}, you do not have any MF points. Please give feedback first.'
                                       f'\n**ATTENTION**: _We could not DM you with a copy of your submission.'
                                       f'\nPlease contact Moderators for help or re-read'
                                       f' <#{FEEDBACK_ACCESS_CHANNEL_ID}> for further instructions._',
                                       delete_after=60)
                
            # store the message id so that we can ensure it was deleted due to actually having 0 points
            self.deleted_messages.add(ctx.message.id)
            
            await ctx.message.delete()

            # Check if user has a feedback thread
            # Called_from_zero used to flag if the member is using <MFS with no points (TRUE to throw exception)
            await feedback_cog.threads_manager.check_if_feedback_thread(ctx=ctx, called_from_zero=True)

            thread, ticket_counter, points_logic, user_id = await self.helpers.load_feedback_cog(ctx)

            await channel.send(f"<@{SERVER_OWNER_ID}>:")

            embed = discord.Embed(color=0x7e016f)
            embed.add_field(
                name=f"ALERT - {self.helpers.get_formatted_time()}",
                value=(
                    f"{mention} tried sending a track for feedback with **0** MF points.\n\n"
                    f"⚠️ [Ticket #{ticket_counter}]({thread.jump_url})"
                ),
                inline=False
            )
            embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
            await channel.send(embed=embed)


    @commands.check(guild_only)
    @commands.command(help = "Use to present the band's genres.", brief = '(Band Name)')
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def genres(self, ctx: discord.Message, band_name: str):
        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
            
        words = ctx.message.content.split()
        band_name  = " ".join(words[2:])
        result, pfp_url = await fetch_band_genres(band_name)

        embed = discord.Embed(color=0x7e016f)
        embed.title = 'Genre Check'
        embed.add_field(name=f"{band_name.title()}:",value = result,inline=False)
        embed.set_thumbnail(url=pfp_url)
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await ctx.channel.send(embed=embed)
        
    @commands.check(guild_only)
    @commands.command(help = "Use to present 10 similar bands to a wanted band.", brief = '(Band Name)')
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def similar(self, ctx: discord.Message, band_name: str):
        if self.pfp_url == "":
            creator_user = await self.bot.fetch_user(self.bot.owner_id)
            self.pfp_url = creator_user.avatar.url
        
        words = ctx.message.content.split()
        band_name  = " ".join(words[2:])
        result = await fetch_similar_bands(band_name)
        

        embed = discord.Embed(color=0x7e016f)
        embed.title = 'Similar bands'
        embed.add_field(name=f"{band_name.title()}:",value = result,inline=False)
        embed.set_thumbnail(url='https://cdn-icons-png.flaticon.com/512/1753/1753311.png')
        embed.set_footer(text=f"Made by FlamingCore", icon_url=self.pfp_url)
        await ctx.channel.send(embed=embed)
        

        
     


async def setup(bot):
    await bot.add_cog(General(bot))