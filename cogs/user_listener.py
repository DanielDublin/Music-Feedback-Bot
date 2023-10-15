import discord
import soundcloud
import youtube_dl
import re
from discord.ext import commands
import database.db as db
from datetime import datetime



FEEDBACK_CHANNEL_ID = 1103427357781528597 #749443325530079314
SERVER_OWNER_ID = 167329255502512128 #412733389196623879
WARNING_CHANNEL =  1103427357781528597 #920730664029020180  #msb_log_channel channel


MODERATORS_ROLE_ID = 915720537660084244 #732377221905252374
SOUNDCLOUD_CLIENT_ID = 'YOUR_SOUNDCLOUD_CLIENT_ID'
YOUTUBE_API_KEY = 'YOUR_YOUTUBE_API_KEY'

# Initialize the SoundCloud and YouTube clients
soundcloud_client = soundcloud.Client(client_id=SOUNDCLOUD_CLIENT_ID)

youtube_dl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

# Regular expressions to match different YouTube URL formats
youtube_url_pattern = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/(.+)')

# Define a regular expression pattern to match SoundCloud URLs
soundcloud_url_pattern = re.compile(r'https?://soundcloud\.com/([A-Za-z0-9_-]+)')



# Function to extract the video ID from a YouTube content
def extract_youtube_video_id(content):
    match = youtube_url_pattern.match(content)
    if match:
        return match.group(4)
    return None


# Function to extract the video ID from a YouTube URL
def extract_soundcloud_username(content):
    soundcloud_match = soundcloud_url_pattern.search(content)
    
    if soundcloud_match:
        return soundcloud_match.group(1)
    return None



async def check_soundcloud(message):
    content =message.content
  

    # Search for a SoundCloud URL in the content
    soundcloud_user = extract_soundcloud_username(content)

    if soundcloud_user is None:
        return False


    try:
        # Get the author's profile
        profile = await message.author.fetch()

        # Check if the author's username or display name contains the SoundCloud username
        if (soundcloud_user in profile.name or soundcloud_user in profile.display_name or soundcloud_user in profile.bio):
            return True
        else:
          
            # Check if the link to SoundCloud is in the user's connections
            soundcloud_in_connections = any(
                soundcloud_user in connection.get('name', '') and connection.get('type') == discord.ConnectionType.soundcloud for connection in profile.connections
            )
            if  soundcloud_in_connections:
                return True
            else:
                return False
    except discord.errors.NotFound:
        print(f"Unable to fetch the user's profile.")
        

async def check_youtube(message):
    
    content = message.content
    
    # Extract YouTube video ID from the URL
    youtube_video_id = extract_youtube_video_id(content)

    try:
        # Get the author's profile
        profile = await message.author.fetch()

        # Get the YouTube video's details
        ydl = youtube_dl.YoutubeDL(youtube_dl_opts)
        with ydl:
            info = ydl.extract_info(f'https://www.youtube.com/watch?v={youtube_video_id}', download=False)
            creator = info.get('creator')

        # Check if the author's username or display name contains the YouTube creator's name
        if creator and (creator in profile.name or creator in profile.display_name or profile.bio):
            return True
        else:

            # Check if the link to YouTube is in the user's connections
            creator_in_youtube_connections = any(
                    creator in connection.get('name', '') and connection.get('type') == discord.ConnectionType.youtube for connection in profile.connections
                )
            if  creator_in_youtube_connections:
                return True
            else:
                return False
    except discord.errors.NotFound:
        print("Unable to fetch the user's profile.")


class User_listener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_message(self, ctx : discord.Message):
        if ctx.author.bot:
            return
        
        content = ctx.message.content
        if ctx.content.lower().startswith(".warn") and ctx.author.guild_permissions.kick_members:
            
            mentions = ctx.mentions
            if mentions is None:
                return        
            
            target_user = mentions[0]
            warnings = await db.add_warning_to_user(str(target_user.id))
             
            if warnings >= 3:
                warning_log_channel = self.bot.get_channel(WARNING_CHANNEL)
                 
               
                pfp = target_user.avatar.url            
                embed = discord.Embed(color = 0x7e016f)
                embed.set_author(name = f"Music Feedback: {target_user.name}", icon_url = ctx.guild.icon.url) 
                embed.set_thumbnail(url = pfp)
                embed.add_field(name = "__MF Warnings__", value = f"User has **{warnings}** warnings.", inline = False)
                embed.add_field(name="Use ``.warnings (user id)`` to see infractions:", value=f"{target_user.mention} | {target_user.id}", inline=False)
                embed.timestamp = datetime.now()
                await warning_log_channel.send(embed = embed) 
                await warning_log_channel.send(f"<@&{MODERATORS_ROLE_ID}>")
                
        elif 'soundcloud.com' in content and not ctx.author.guild_permissions.kick_members:
            is_promoting = await check_soundcloud(ctx.message)

        elif ('youtube.com' in content or 'youtu.be') and not ctx.author.guild_permissions.kick_members:
            is_promoting = await check_youtube(ctx.message)
            await ctx.message.channel.send(f"{message.author.name} is promoting their song on YouTube.")



                 
                
             

    @commands.Cog.listener()
    async def on_member_join(self, member : discord.Member):
        await db.add_user(str(member.id))
    

    # User left - reset his points
    @commands.Cog.listener()
    async def on_member_remove(self, member): 
        await db.reset_points(str(member.id))
        
    # User was banned - remove him from DB
    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        await db.remove_user(str(member.id))
    
    
   
async def setup(bot):
    await bot.add_cog(User_listener(bot))