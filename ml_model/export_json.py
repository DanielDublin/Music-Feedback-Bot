import asyncio
import discord
import json
import logging
from data.constants import EXPORTS_CHANNEL, CO_DEV_ID

logger = logging.getLogger(__name__)


class ExportJson:

    def __init__(self, client):
        self.client = client

    def _write_json(self, data: list, filename: str) -> None:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def _read_json(self, filename: str) -> list:
        with open(filename, 'r') as f:
            return json.load(f)

    async def export_to_json(self, data, filename="feedback_json.json") -> bool:
        await asyncio.to_thread(self._write_json, data, filename)
        logger.debug("Exported feedback data to %s", filename)
        return True

    async def count_entries(self, filename="feedback_json.json") -> int:
        try:
            data = await asyncio.to_thread(self._read_json, filename)

            if len(data) >= 20:
                mod_channel = self.client.get_channel(EXPORTS_CHANNEL)

                if mod_channel is None:
                    logger.error("Could not find exports channel %s", EXPORTS_CHANNEL)
                    return len(data)

                discord_file = discord.File(filename)
                await mod_channel.send(
                    f"<@{CO_DEV_ID}> New Export!",
                    allowed_mentions=discord.AllowedMentions(users=True)
                )
                await mod_channel.send(file=discord_file, content=f"📊 Feedback export - {len(data)} entries")
                logger.info("Sent %d feedback entries to exports channel", len(data))

                await asyncio.to_thread(self._write_json, [], filename)
                logger.debug("Cleared %s", filename)

            return len(data)

        except FileNotFoundError:
            logger.warning("Feedback file not found: %s", filename)
            return 0
        except json.JSONDecodeError:
            logger.error("Invalid JSON in %s", filename)
            return 0
        except Exception:
            logger.error("Error in count_entries", exc_info=True)
            return 0
