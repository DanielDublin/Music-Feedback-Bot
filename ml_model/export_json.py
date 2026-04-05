import discord
import json
from data.constants import EXPORTS_CHANNEL, CO_DEV_ID

class ExportJson:

    def __init__(self, client):
        """Initialize with Discord client to access channels"""
        self.client = client

    # take data from feedback monitor and export to json file
    def export_to_json(self, data, filename="feedback_json.json"):

        with open(filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)

        print(f"✅ Exported feedback data to {filename}")
        return True
    
    async def count_entries(self, filename="feedback_json.json"):
        """Check entry count and send to mod channel if >= 20"""
        try:
            with open(filename, 'r') as json_file:
                data = json.load(json_file)

                if len(data) >= 20:
                    # Get the mod channel
                    mod_channel = self.client.get_channel(EXPORTS_CHANNEL)
                    
                    if mod_channel is None:
                        print(f"❌ Could not find channel with ID {EXPORTS_CHANNEL}")
                        return len(data)

                    file_path = filename  # Use the filename parameter consistently
                    
                    # Create a discord.File object
                    discord_file = discord.File(file_path)
                    
                    # Send the file to the channel  
                    await mod_channel.send(
                        f"<@{CO_DEV_ID}> New Export!",
                        allowed_mentions=discord.AllowedMentions(users=True)  # Changed from roles=True
                    )
                    await mod_channel.send(file=discord_file, content=f"📊 Feedback export - {len(data)} entries")
                    print(f"✅ Sent {len(data)} feedback entries to mod channel")

                    # Once sent, clear the file
                    with open(filename, 'w') as json_file:
                        json.dump([], json_file, indent=4)
                    
                    print(f"🧹 Cleared {filename}")

                return len(data)

        except FileNotFoundError:
            print("⚠️ Feedback file not found")
            return 0
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {filename}")
            return 0
        except Exception as e:
            print(f"❌ Error in count_entries: {e}")
            return 0