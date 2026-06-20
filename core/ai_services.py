import os
import asyncio
import streamlit as st
from typing import List, Optional, Dict, Union

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

class GeminiService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model_name = 'gemini-3.5-flash' # Latest model released May 2026
        if genai:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def validate_key(self) -> bool:
        if not self.client:
            return False
        try:
            # Simple test call
            self.client.models.generate_content(model=self.model_name, contents="Hello")
            return True
        except Exception:
            return False

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using Gemini Multimodal"""
        if not self.client: return None
        
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            
            prompt = "Please transcribe this audio file into Burmese text accurately. Provide only the transcript."
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/mp3")
                ]
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Transcription Error: {str(e)}")
            return None

    async def generate_script(self, text: str, duration: Optional[float] = None) -> Optional[str]:
        """Generate Burmese Recap Script"""
        if not self.client: return None
        
        duration_info = f" (Target length for {duration/60:.1f} minutes)" if duration else ""
        prompt = f"""
        You are a professional Burmese movie recap writer.
        Based on this content:
        {text}
        
        Create an engaging Burmese movie recap script{duration_info}.
        Requirements:
        1. Conversational Burmese
        2. Clear sections (Intro, Summary, Key Scenes, Conclusion)
        3. Engaging and emotional tone
        
        Provide only the script text.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Script Generation Error: {str(e)}")
            return None

    async def refine_script(self, script: str, instruction: str) -> Optional[str]:
        """Refine script based on user instruction"""
        if not self.client: return None
        prompt = f"Refine this Burmese movie script based on: {instruction}\n\nScript:\n{script}"
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Refinement Error: {str(e)}")
            return None
