import discord
import asyncio
import os
from elevenlabs.client import ElevenLabs
from io import BytesIO


class ElevenLabsTTS:
    """Handles all ElevenLabs text-to-speech functionality"""
    
    def __init__(self, api_key=os.getenv('ELEVENLABS_API_KEY')):
        self.client = ElevenLabs(api_key=api_key)
        
    def get_voices(self):
        """Get list of available voices"""
        try:
            voices = self.client.voices.get_all()
            return voices.voices
        except Exception as e:
            print(f"Error getting voices: {e}")
            return None
    
    async def synthesize_speech(self, text, voice_id="JBFqnCBsd6RMkjVDRZzb"):
        """
        Generate speech from text using ElevenLabs
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID from ElevenLabs
        
        Popular Voice IDs:
            - "JBFqnCBsd6RMkjVDRZzb" - George (male, warm & authoritative)
            - "21m00Tcm4TlvDq8ikWAM" - Rachel (female, calm)
            - "AZnzlk1XvdvUeBnXmlld" - Domi (female, strong)
            - "EXAVITQu4vr4xnSDxMaL" - Bella (female, soft)
            - "ErXwobaYiN019PkySvjV" - Antoni (male, calm)
            - "MF3mGyEYCl7XYWbV9V6O" - Elli (female, emotional)
            - "TxGEqnHWrfWFTfGW9XjX" - Josh (male, young)
            - "VR6AewLTigWG4xSOukaG" - Arnold (male, crisp)
            - "pNInz6obpgDQGcFmaJgB" - Adam (male, deep)
            - "yoZ06aMxZJJ28mfd3POQ" - Sam (male, raspy)
        
        Returns:
            BytesIO object containing the audio data
        """
        try:
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_flash_v2_5",  # 50% cheaper than multilingual_v2!
                output_format="mp3_44100_128"
            )
            
            # Collect all audio chunks into a BytesIO object
            audio_data = BytesIO()
            for chunk in audio_generator:
                audio_data.write(chunk)
            
            audio_data.seek(0)
            return audio_data
                
        except Exception as e:
            print(f"Error synthesizing speech: {e}")
            return None
    
    def get_character_usage(self):
        """Check how many characters you've used"""
        try:
            user = self.client.user.get()
            subscription = user.subscription
            return {
                'character_count': subscription.character_count,
                'character_limit': subscription.character_limit,
                'remaining': subscription.character_limit - subscription.character_count
            }
        except Exception as e:
            print(f"Error getting usage: {e}")
            return None
    
    async def play_tts_in_vc(self, voice_client, text, voice_id="TxGEqnHWrfWFTfGW9XjX"):
        """
        Play a TTS announcement in the voice channel
        
        Args:
            voice_client: Discord voice client
            text: Text to announce
            voice_id: ElevenLabs voice ID (default is Josh - energetic male)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate speech
            audio_stream = await self.synthesize_speech(text, voice_id)
            
            if audio_stream is None:
                return False
            
            # Save to temporary file
            temp_file = 'temp_announcement.mp3'
            with open(temp_file, 'wb') as f:
                f.write(audio_stream.read())
            
            # Play in Discord
            audio_source = discord.FFmpegPCMAudio(temp_file)
            voice_client.play(audio_source)
            
            # Wait for playback to finish
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            # Clean up
            os.remove(temp_file)
            return True
            
        except Exception as e:
            print(f"Failed to play announcement: {e}")
            return False