import os
import asyncio
import time
import streamlit as st
from typing import List, Optional, Dict, Union
from google import genai
from google.genai import types

class GeminiService:
    def __init__(self, api_keys: List[str], max_rpm: int = 9):
        self.api_keys = api_keys if api_keys else []
        self.max_rpm = max_rpm
        self.current_key_index = 0
        self.api_lock = asyncio.Lock()
        self.key_usage = {key: [] for key in self.api_keys}
        self.model_name = 'gemini-3.5-flash'

    async def _get_next_client(self):
        """Rotate through API keys with rate limit awareness (Original Logic)"""
        if not self.api_keys:
            return None
        
        while True:
            key = None
            async with self.api_lock:
                attempts = 0
                while attempts < len(self.api_keys):
                    current_key_candidate = self.api_keys[self.current_key_index]
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    attempts += 1
                    
                    now = time.time()
                    # Clean up old timestamps (older than 60s)
                    self.key_usage[current_key_candidate] = [t for t in self.key_usage[current_key_candidate] if now - t < 60]
                    
                    if len(self.key_usage[current_key_candidate]) < self.max_rpm:
                        key = current_key_candidate
                        self.key_usage[key].append(now)
                        break
            
            if key:
                return genai.Client(api_key=key)
            
            # All keys are at limit, wait before retrying
            await asyncio.sleep(5) # Shorter wait for UI responsiveness

    async def validate_keys(self) -> Dict[str, Union[bool, int]]:
        """Validate all provided API keys"""
        valid_count = 0
        for key in self.api_keys:
            try:
                client = genai.Client(api_key=key)
                await asyncio.to_thread(client.models.generate_content, model=self.model_name, contents="Hello")
                valid_count += 1
            except Exception:
                continue
        return {"success": valid_count > 0, "count": valid_count}

    async def transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio using Gemini Multimodal with Key Rotation"""
        client = await self._get_next_client()
        if not client: return None
        
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            
            prompt = "Please transcribe this audio file into Burmese text accurately. Provide only the transcript."
            
            response = await asyncio.to_thread(
                client.models.generate_content,
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
        """Generate Burmese Recap Script with Key Rotation"""
        client = await self._get_next_client()
        if not client: return None
        
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
                client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Script Generation Error: {str(e)}")
            return None

    async def refine_script(self, script: str, instruction: str) -> Optional[str]:
        """Refine script with Key Rotation"""
        client = await self._get_next_client()
        if not client: return None
        
        prompt = f"Refine this Burmese movie script based on: {instruction}\n\nScript:\n{script}"
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            st.error(f"Refinement Error: {str(e)}")
            return None
