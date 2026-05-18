"""Admin runtime commands: /reload and /status.

The module-level extension_autocomplete is shared with the signature cog —
it has to be importable as a callable from the @app_commands.autocomplete
decorator, which is applied at class-body evaluation time.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)


async def extension_autocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=ext, value=ext)
        for ext in interaction.client.extensions
        if current.lower() in ext.lower()
    ][:25]


class AdminRuntimeImpl:
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def handle_reload(self, interaction: discord.Interaction, extension: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.bot.reload_extension(extension)
            await interaction.followup.send(f"Reloaded `{extension}`.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Failed to reload `{extension}`: {e}", ephemeral=True)

    async def handle_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        latency = round(self.bot.latency * 1000)
        cog_names = "\n".join(self.bot.cogs.keys()) or "none"
        embed = discord.Embed(title="Bot Status", color=0x7e016f)
        embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
        embed.add_field(name="Cogs loaded", value=str(len(self.bot.cogs)), inline=True)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Loaded cogs", value=cog_names, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
