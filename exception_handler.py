import discord

# Define a function to handle exceptions
async def handle_exception(ctx, error):
    # Get the cog name if available
    cog_name = "Unknown"
    try:
        cog_name = getattr(ctx.command.cog, "qualified_name", "Unknown Cog")
        if cog_name is None:
            cog_name = "Unknown"
    except Exception as cog_error:
        print("someone tried to use a command that doesnt exist")

        try:
                await ctx.send(f"No such command exists.")
        except Exception as e:
            print("No permissions to send message\n"+str(e))

    try:
        if isinstance(error, discord.ext.commands.MissingPermissions):
            await ctx.send(f"You don't have permission to use a command in the '{cog_name}' cog.")
        elif isinstance(error, discord.ext.commands.CheckFailure):
            await ctx.send(f"You don't meet the requirements to use a command in the '{cog_name}' cog.")
        elif isinstance(error, discord.ext.commands.BadArgument):
            await ctx.send(f"Invalid argument in the '{cog_name}' cog. Please check your input.")
        else:
            # Handle other unexpected errors
            await ctx.send(f"An error occurred in the '{cog_name}' cog: {error}")
    except Exception as e:
        print(f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n{str(e)}")