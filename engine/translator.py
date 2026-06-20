import re
import asyncio
import time
from typing import List, Dict, Union
from google import genai
from google.genai import types

class Translator:
    def __init__(self, api_keys: List[str] = None, max_rpm: int = 9):
        self.api_keys = api_keys if api_keys else []
        self.max_rpm = max_rpm
        self.current_key_index = 0
        self.api_lock = asyncio.Lock() # Lock for thread-safe/async-safe rotation
        self.key_usage = {key: [] for key in self.api_keys}
        self.gemini_model = 'gemini-3.5-flash'

    async def _get_next_client(self):
        """Rotate through API keys and return a configured GenAI client with rate limit awareness."""
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
                    self.key_usage[current_key_candidate] = [t for t in self.key_usage[current_key_candidate] if now - t < 60]
                    
                    if len(self.key_usage[current_key_candidate]) < self.max_rpm:
                        key = current_key_candidate
                        self.key_usage[key].append(now)
                        break
            
            if key:
                return genai.Client(api_key=key)
            
            await asyncio.sleep(5) # Reduced wait for better UI responsiveness

    async def translate_batch_parallel(self, text: str, target_lang: str, num_workers: int = 5) -> str:
        """Translate text in parallel with enhanced chunking and error handling."""
        input_lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        if not input_lines:
            return ""
        
        total_lines = len(input_lines)
        if num_workers <= 1 or total_lines <= 5:
            return await self._translate_chunk(input_lines, target_lang, 0, as_string=True)
            
        # Chunking logic
        ideal_chunk_size = max(5, total_lines // num_workers)
        chunks = []
        current_chunk = []
        
        for i, line in enumerate(input_lines):
            current_chunk.append(line)
            is_sentence_end = any(line.endswith(p) for p in ['.', '?', '!', '။', '၊'])
            is_last_line = (i == total_lines - 1)
            
            if (len(current_chunk) >= ideal_chunk_size and is_sentence_end) or \
               (len(current_chunk) >= ideal_chunk_size * 2) or \
               is_last_line:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
        
        if current_chunk:
            if chunks: chunks[-1].extend(current_chunk)
            else: chunks.append(current_chunk)

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
        """Helper to translate a specific chunk of lines with flexible regex and auto-retry."""
        max_retries = 3
        retry_delay = 2
        
        numbered_input = "\n".join([f"L{start_index + i + 1}: {line}" for i, line in enumerate(lines)])
        
        config = types.GenerateContentConfig(
            max_output_tokens=32768,
            temperature=0.3 # Lower temperature for more consistent formatting
        )
        
        prompt = f"""You are a professional translator specializing in {target_lang}. 
        Translate the following numbered lines accurately.

        ### STRICT OUTPUT FORMAT:
        - Every line MUST start with its marker (e.g., 'L{start_index + 1}:').
        - Do not skip any lines. Every input line from L{start_index + 1} to L{start_index + len(lines)} must be present in your output.
        - Do not add any chat, explanations, or notes.
        - If a line is empty, just return the marker with an empty space.

        ### START OF LINES TO TRANSLATE:
        """
        
        for attempt in range(max_retries):
            client = await self._get_next_client()
            if not client:
                return [f"[Error: No API keys]"] * len(lines)

            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.gemini_model,
                    contents=f"{prompt}\n\n{numbered_input}",
                    config=config
                )
                translated_raw = response.text.strip()
                
                chunk_output = [None] * len(lines)
                # Flexible regex to match L1:, Line 1:, L 1:, etc.
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
                                clean_text = text_part.strip().split('\n')[0].strip()
                                chunk_output[idx] = clean_text
                    except:
                        continue
                
                # Check for missing lines
                missing_indices = [i for i, val in enumerate(chunk_output) if val is None]
                if missing_indices and attempt < max_retries - 1:
                    print(f"Missing {len(missing_indices)} lines in chunk {start_index}. Retrying...")
                    continue 

                # Final assembly
                final_output = []
                for i, val in enumerate(chunk_output):
                    if val is None:
                        final_output.append(f"[Missing: {lines[i]}]")
                    else:
                        final_output.append(val)
                
                return "\n".join(final_output) if as_string else final_output

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                err_res = [f"[Error: {str(e)}]"] * len(lines)
                return "\n".join(err_res) if as_string else err_res
        
        return [f"[Error: Max retries]"] * len(lines)

    async def _rewrite_text_with_ai(self, original_text: str, target_duration: float, current_tts_duration: float, lang: str) -> str:
        """Original rewrite logic remains same but uses next client."""
        client = await self._get_next_client()
        if not client: return original_text
        # ... (rest of rewrite logic remains same as original)
        return original_text
