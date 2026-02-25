"""
Google Cloud Speech STT Fallback
Drop-in replacement when Muxlisa fails
"""

import base64
import os
from google.cloud import speech_v1
from app.schemas.ai import STTResponse
from loguru import logger

class GoogleSpeechSTT:
    """Fallback STT using Google Cloud Speech"""
    
    def __init__(self):
        # Set credentials from environment
        # Get your key from: https://console.cloud.google.com/apis/credentials
        self.credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_PATH")
        if self.credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
        
        self.client = speech_v1.SpeechClient()
    
    async def speech_to_text(self, audio_bytes: bytes, audio_format: str = "wav") -> STTResponse:
        """Convert speech to text using Google Cloud Speech"""
        try:
            # Configure recognition
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="uz-UZ",  # Uzbek
                alternative_language_codes=["ru-RU", "en-US"],  # Fallbacks
                enable_automatic_punctuation=True,
            )
            
            audio = speech_v1.RecognitionAudio(content=audio_bytes)
            
            # Perform recognition
            response = self.client.recognize(config=config, audio=audio)
            
            if response.results:
                transcript = response.results[0].alternatives[0].transcript
                confidence = response.results[0].alternatives[0].confidence
                language = response.results[0].language_code[:2]  # uz, ru, en
                
                logger.info(f"✅ Google STT: '{transcript}' ({language}, {confidence:.2f})")
                
                return STTResponse(
                    transcript=transcript,
                    language=language,
                    confidence=confidence,
                )
            else:
                logger.warning("Google STT returned no results")
                return STTResponse(transcript="", language="uz", confidence=0.0)
                
        except Exception as e:
            logger.error(f"Google STT failed: {e}")
            return STTResponse(transcript="", language="uz", confidence=0.0)


# Usage in muxlisa_service.py:
# from app.ai.google_stt import GoogleSpeechSTT
# 
# if muxlisa fails (status 500):
#     fallback = GoogleSpeechSTT()
#     return await fallback.speech_to_text(audio_bytes)
