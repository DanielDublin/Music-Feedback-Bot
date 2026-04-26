import discord
import logging

logger = logging.getLogger(__name__)


async def handle_exception(ctx, error):
    cog_name = "Unknown"
    try:
        cog_name = getattr(ctx.command.cog, "qualified_name", "Unknown Cog")
        if cog_name is None:
            cog_name = "Unknown"
            logger.info("someone tried to use a command that doesnt exist")
    except Exception as cog_error:
        try:
            await ctx.send(f"No such command exists.")
            return
        except Exception as e:
            logger.error(f"No permissions to send message\n{e}\n{cog_error}")

    try:
        if isinstance(error, discord.ext.commands.CommandOnCooldown):
            await ctx.send(f'This command is on cooldown, you can use it in {round(error.retry_after, 2)}s')
        elif isinstance(error, discord.ext.commands.MissingPermissions):
            await ctx.send(f"You don't have permissions to use the command.")
        elif isinstance(error, discord.ext.commands.CheckFailure):
            await ctx.send(f"You don't meet the requirements to use the command.")
        elif isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send(f"Invalid argument in the command. Please check your input.")
        else:
            orig = getattr(error, 'original', error)
            logger.error(f"UNHANDLED ERROR in {cog_name}: {orig!r}", exc_info=(type(orig), orig, orig.__traceback__))
            await ctx.send(f"An error occurred while executing the command.")
    except Exception as e:
        logger.error(f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n{e}", exc_info=True)
