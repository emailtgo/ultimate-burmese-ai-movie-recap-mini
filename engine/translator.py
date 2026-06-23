import re
import asyncio
import time
import math
from typing import List, Dict, Union
from google import genai
from google.genai import types

class Translator:
    def __init__(self, api_keys: List[str] = None, max_rpm: int = 3): # Lowered RPM to be safer
        self.api_keys = api_keys if api_keys else []
        self.max_rpm = max_rpm
        self.current_key_index = 0
        self.api_lock = asyncio.Lock()
        self.key_usage = {key: [] for key in self.api_keys}
        self.blacklisted_keys = {} # key: resume_time
        self.gemini_model = 'gemini-3.5-flash'

    async def _get_next_client(self):
        """Enhanced Shared Key Pool with Blacklisting for 429 errors."""
        if not self.api_keys:
            return None, None
        
        while True:
            key = None
            async with self.api_lock:
                now = time.time()
                # Clean up blacklisted keys
                self.blacklisted_keys = {k: t for k, t in self.blacklisted_keys.items() if t > now}
                
                attempts = 0
                while attempts < len(self.api_keys):
                    current_key_candidate = self.api_keys[self.current_key_index]
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    attempts += 1
                    
                    # Skip blacklisted keys
                    if current_key_candidate in self.blacklisted_keys:
                        continue
                        
                    # Clean up old timestamps
                    self.key_usage[current_key_candidate] = [t for t in self.key_usage[current_key_candidate] if now - t < 60]
                    
                    if len(self.key_usage[current_key_candidate]) < self.max_rpm:
                        key = current_key_candidate
                        self.key_usage[key].append(now)
                        break
            
            if key:
                return genai.Client(api_key=key), key
            
            # If all keys are used up or blacklisted, wait
            await asyncio.sleep(5)

    async def _blacklist_key(self, key: str, duration: int = 60):
        """Temporarily disable a key that returned 429."""
        async with self.api_lock:
            self.blacklisted_keys[key] = time.time() + duration
            print(f"Key {key[:8]}... blacklisted for {duration}s due to 429 error.")

    async def translate_batch_parallel(self, text: str, target_lang: str, chunk_to_split: int = 5) -> str:
        input_lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        if not input_lines: return ""
        
        total_lines = len(input_lines)
        lines_per_chunk = math.ceil(total_lines / chunk_to_split)
        
        chunks = []
        for i in range(0, total_lines, lines_per_chunk):
            chunks.append(input_lines[i : i + lines_per_chunk])
        
        if len(chunks) > chunk_to_split:
            last_chunk = chunks.pop()
            chunks[-1].extend(last_chunk)

        tasks = []
        current_start_index = 0
        for chunk in chunks:
            tasks.append(self._translate_chunk(chunk, target_lang, current_start_index))
            current_start_index += len(chunk)
        
        results = await asyncio.gather(*tasks)
        
        all_translated_lines = []
        for i, res in enumerate(results):
            if isinstance(res, list):
                all_translated_lines.extend(res)
            else:
                all_translated_lines.extend([f"[Chunk Error: {res}]"] * len(chunks[i]))
        
        return "\n".join(all_translated_lines[:len(input_lines)])

    async def _translate_chunk(self, lines: List[str], target_lang: str, start_index: int, as_string: bool = False) -> Union[List[str], str]:
        max_retries = 5 # Increased retries
        retry_delay = 5
        
        numbered_input = "\n".join([f"L{start_index + i + 1}: {line}" for i, line in enumerate(lines)])
        config = types.GenerateContentConfig(max_output_tokens=32768, temperature=0.3)
        
        prompt = f"""You are a professional translator specializing in {target_lang}. 
        Translate the following numbered lines accurately.
        - Start every line with its marker (e.g., 'L{start_index + 1}:').
        - Translate all {len(lines)} lines.
        """
        
        for attempt in range(max_retries):
            client, key = await self._get_next_client()
            if not client: return [f"[Error: No Keys]"] * len(lines)

            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.gemini_model,
                    contents=f"{prompt}\n\n{numbered_input}",
                    config=config
                )
                translated_raw = response.text.strip()
                
                chunk_output = [None] * len(lines)
                parts = re.split(r"((?:L|Line)\s*\d+\s*[:\-\.\s]+)", translated_raw, flags=re.IGNORECASE)
                
                for i in range(1, len(parts), 2):
                    marker_part = parts[i]
                    text_part = parts[i+1]
                    try:
                        line_match = re.search(r"\d+", marker_part)
                        if line_match:
                            line_num = int(line_match.group())
                            idx = line_num - start_index - 1
                            if 0 <= idx < len(lines):
                                chunk_output[idx] = text_part.strip().split('\n')[0].strip()
                    except: continue
                
                if None in chunk_output and attempt < max_retries - 1:
                    continue 

                final_output = [val if val is not None else f"[Missing: {lines[i]}]" for i, val in enumerate(chunk_output)]
                return "\n".join(final_output) if as_string else final_output

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    await self._blacklist_key(key) # Disable this key for a while
                    if attempt < max_retries - 1:
                        continue # Try again with a different key
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return [f"[Error: {error_msg}]"] * len(lines)
        
        return [f"[Error: Max Retries]"] * len(lines)

    async def _rewrite_text_with_ai(self, original_text: str, target_duration: float, current_tts_duration: float, lang: str) -> str:
        return original_text
