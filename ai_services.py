"""
AI Services Integration - Upgraded with Gemini 3.5 Flash Multimodal Support
Handles Gemini AI for both audio transcription and script generation.
OpenAI Whisper is removed to simplify requirements and API key management.
"""

import os
import tempfile
import asyncio
import re
import time
from typing import Optional, Dict, List, Union
import streamlit as st
from engine.translator import Translator

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None


# ============================================================================
# GEMINI AI - MULTIMODAL SERVICES (UPGRADED TO V3 LOGIC)
# ============================================================================

class AIScriptService:
    def __init__(self, api_keys: List[str], max_rpm: int = 9):
        self.translator = Translator(api_keys=api_keys, max_rpm=max_rpm)
        self.model_name = 'gemini-3.5-flash'

    async def transcribe_audio_gemini(self, audio_file_path: str) -> Optional[str]:
        """
        Transcribe audio file using Gemini 3.5 Flash (Multimodal)
        Replaces OpenAI Whisper.
        """
        if not self.translator.api_keys:
            st.error("Gemini API keys are required for transcription.")
            return None
        
        try:
            client = await self.translator._get_next_client()
            if not client:
                return None

            st.info("📤 Uploading audio to Gemini for transcription...")
            
            # Upload file to Gemini
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            
            # For Gemini API, we can send bytes directly for small files 
            # or use the File API for larger ones. Here we use direct generation for simplicity.
            prompt = "Please transcribe this audio file into Burmese text accurately. Provide only the transcript."
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")
                ]
            )
            
            if response.text:
                return response.text.strip()
            else:
                st.error("Gemini API returned empty transcript.")
                return None
        except Exception as e:
            st.error(f"Error transcribing audio with Gemini: {str(e)}")
            return None

    async def generate_movie_recap_script(
        self,
        transcript_or_text: str,
        video_duration: Optional[float] = None,
        custom_prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate Burmese movie recap script using Gemini 3.5 Flash
        """
        if not self.translator.api_keys:
            st.error("Gemini API keys are required for script generation.")
            return None
        
        try:
            client = await self.translator._get_next_client()
            if not client:
                return None

            duration_hint = ""
            if video_duration:
                target_words = int((video_duration / 60) * 130)
                duration_hint = f"\n\nEstimated target length: approximately {target_words} words (for {video_duration/60:.1f} minutes of video)."
            
            custom_instruction = f"\n\nAdditional instructions: {custom_prompt}" if custom_prompt else ""
            
            prompt = f"""
            You are a professional movie recap writer for Burmese audiences. 
            
            Please create an engaging and concise movie recap script in Burmese based on the following content:
            
            {transcript_or_text}
            
            Requirements:
            1. Write in clear, conversational Burmese language
            2. Keep the recap engaging and entertaining
            3. Include key plot points and important character developments
            4. Add some emotional depth and humor where appropriate
            5. Format the script with clear sections (Introduction, Plot Summary, Key Scenes, Conclusion)
            6. Make it suitable for voiceover narration{duration_hint}{custom_instruction}
            
            Please provide the script directly without any preamble or explanation.
            """
            
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            if response.text:
                return response.text.strip()
            else:
                st.error("Gemini API returned empty response.")
                return None
        except Exception as e:
            st.error(f"Error generating script with Gemini: {str(e)}")
            return None

    async def refine_script(
        self,
        original_script: str,
        refinement_instruction: str
    ) -> Optional[str]:
        """
        Refine or edit script using Gemini 3.5 Flash
        """
        if not self.translator.api_keys:
            return None
        
        try:
            client = await self.translator._get_next_client()
            if not client: return None

            prompt = f"Refine this Burmese script based on: {refinement_instruction}\n\nScript:\n{original_script}"
            response = await asyncio.to_thread(client.models.generate_content, model=self.model_name, contents=prompt)
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Error refining script: {str(e)}")
            return None


def extract_audio_from_video(video_file_path: str) -> Optional[str]:
    """
    Extract audio from video file using moviepy
    """
    try:
        from moviepy.editor import VideoFileClip
        video = VideoFileClip(video_file_path)
        if video.audio is None:
            return None
        audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
        video.audio.write_audiofile(audio_path, verbose=False, logger=None)
        video.close()
        return audio_path
    except Exception as e:
        st.error(f"Error extracting audio: {str(e)}")
        return None


def validate_api_keys(gemini_keys: List[str]) -> Dict[str, Union[bool, str]]:
    """
    Validate Gemini API keys
    """
    valid_count = sum(1 for key in gemini_keys if key and len(key) > 20)
    return {
        "gemini_valid": valid_count > 0,
        "gemini_message": f"✅ {valid_count} Gemini API key(s) active" if valid_count > 0 else "⚠️ No valid Gemini API keys"
    }
