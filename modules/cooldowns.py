from discord.ext import commands
from data.constants import BOT_DEV_ID, CO_DEV_ID

BYPASS_IDS = (BOT_DEV_ID, CO_DEV_ID)


def admin_bypass_cooldown(rate: int, per: float, bucket_type: commands.BucketType = commands.BucketType.user):
    """Cooldown decorator that grants admins and dev IDs a full bypass."""
    def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return None
        if ctx.author.id in BYPASS_IDS:
            return None
        return commands.Cooldown(rate, per)
    return commands.dynamic_cooldown(predicate, bucket_type)
