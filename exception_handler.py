import discord

# Define a function to handle exceptions
async def handle_exception(ctx, error):
    # Get the cog name if available
    cog_name = "Unknown"
    try:
        cog_name = getattr(ctx.command.cog, "qualified_name", "Unknown Cog")
        if cog_name is None:
            cog_name = "Unknown"
            print("someone tried to use a command that doesnt exist")
        print(f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n")
    except Exception as cog_error:
        try:
                await ctx.send(f"No such command exists.")
                return
        except Exception as e:
            print("No permissions to send message\n"+str(e)+"\n"+str(cog_error))

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
            # Handle other unexpected errors
            await ctx.send(f"An error occurred while executing the command.")
    except Exception as e:
        print(f"ERROR IN HANDLE EXCEPTION from cog {cog_name}\n{str(e)}")