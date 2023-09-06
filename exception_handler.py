import discord

# Define a function to handle exceptions
async def handle_exception(ctx, error):
    # Get the cog name if available
    cog_name = getattr(ctx.command.cog, "qualified_name", "Unknown Cog")

    if isinstance(error, discord.ext.commands.CommandNotFound):
        await ctx.send(f"Command not found in the '{cog_name}' cog. Check your command syntax.")
    elif isinstance(error, discord.ext.commands.MissingPermissions):
        await ctx.send(f"You don't have permission to use a command in the '{cog_name}' cog.")
    elif isinstance(error, discord.ext.commands.CheckFailure):
        await ctx.send(f"You don't meet the requirements to use a command in the '{cog_name}' cog.")
    elif isinstance(error, discord.ext.commands.BadArgument):
        await ctx.send(f"Invalid argument in the '{cog_name}' cog. Please check your input.")
    else:
        # Handle other unexpected errors
        await ctx.send(f"An error occurred in the '{cog_name}' cog: {error}")