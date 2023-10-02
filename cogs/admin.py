import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server."""
        await member.kick(reason=reason)
        await ctx.send(f"{member.display_name} has been kicked for the reason: {reason}")

    @commands.command()
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member from the server."""
        await member.ban(reason=reason)
        await ctx.send(f"{member.display_name} has been banned for the reason: {reason}")

    @commands.command()
    async def unban(self, ctx, *, member):
        """Unban a member from the server."""
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user

            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.send(f"{user.mention} has been unbanned.")
                return

async def setup(bot):
    await bot.add_cog(Admin(bot))
