import re
import asyncio
import time
import math
import random
from typing import List, Dict, Union
from google import genai
from google.genai import types

class Translator:
    def __init__(self, api_keys: List[str] = None, proxy_urls: List[str] = None, max_rpm: int = 3):
        self.api_keys = api_keys if api_keys else []
        self.proxy_urls = proxy_urls if proxy_urls else []
        self.max_rpm = max_rpm
        self.current_key_index = 0
        self.api_lock = asyncio.Lock()
        self.key_usage = {key: [] for key in self.api_keys}
        self.blacklisted_keys = {} # key: resume_time
        self.gemini_model = 'gemini-3.5-flash'
        
        # 1:1 Mapping logic: Assign each key to a specific proxy (Sticky Session)
        self.key_to_proxy = {}
        if self.api_keys:
            for i, key in enumerate(self.api_keys):
                if self.proxy_urls:
                    # Map key to proxy in a round-robin way if proxy count != key count
                    proxy = self.proxy_urls[i % len(self.proxy_urls)]
                    self.key_to_proxy[key] = proxy
                else:
                    self.key_to_proxy[key] = None

    async def _get_next_client(self):
        """Shared Key Pool with Sticky Proxy Mapping."""
        if not self.api_keys:
            return None, None, None
        
        while True:
            key = None
            proxy = None
            async with self.api_lock:
                now = time.time()
                self.blacklisted_keys = {k: t for k, t in self.blacklisted_keys.items() if t > now}
                
                attempts = 0
                while attempts < len(self.api_keys):
                    current_key_candidate = self.api_keys[self.current_key_index]
                    self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
                    attempts += 1
                    
                    if current_key_candidate in self.blacklisted_keys:
                        continue
                        
                    self.key_usage[current_key_candidate] = [t for t in self.key_usage[current_key_candidate] if now - t < 60]
                    
                    if len(self.key_usage[current_key_candidate]) < self.max_rpm:
                        key = current_key_candidate
                        proxy = self.key_to_proxy.get(key)
                        self.key_usage[key].append(now)
                        break
            
            if key:
                # Add a small random jitter to prevent synchronized requests
                await asyncio.sleep(random.uniform(0.1, 0.5))
                
                # Configure client with proxy if available
                # Note: Google GenAI SDK handles proxies via environment variables or specific config
                # For this implementation, we assume the proxy is set via environment or handled by the caller
                client_config = {}
                if proxy:
                    # In a real scenario, we would pass proxy to the client constructor or set os.environ
                    # For now, we return the proxy info for logging/tracking
                    pass
                
                return genai.Client(api_key=key), key, proxy
            
            await asyncio.sleep(2)

    async def _blacklist_key(self, key: str, duration: int = 60):
        async with self.api_lock:
            self.blacklisted_keys[key] = time.time() + duration
            print(f"Key {key[:8]}... blacklisted for {duration}s.")

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
        for res in results:
            if isinstance(res, list):
                all_translated_lines.extend(res)
            else:
                # Handle unexpected non-list results
                all_translated_lines.append(str(res))
        
        return "\n".join(all_translated_lines[:len(input_lines)])

    async def _translate_chunk(self, lines: List[str], target_lang: str, start_index: int) -> List[str]:
        max_retries = 5
        numbered_input = "\n".join([f"L{start_index + i + 1}: {line}" for i, line in enumerate(lines)])
        config = types.GenerateContentConfig(max_output_tokens=32768, temperature=0.3)
        
        prompt = f"""You are a professional translator specializing in {target_lang}. 
        Translate the following numbered lines accurately.
        - Start every line with its marker (e.g., 'L{start_index + 1}:').
        - Translate all {len(lines)} lines.
        """
        
        for attempt in range(max_retries):
            client, key, proxy = await self._get_next_client()
            if not client: return [f"[Error: No Keys]"] * len(lines)

            try:
                # Using the mapped proxy for this specific request
                # In a real environment, you might need to set HTTP_PROXY environment variable
                # or use a client that supports per-request proxies.
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

                return [val if val is not None else f"[Missing: {lines[i]}]" for i, val in enumerate(chunk_output)]

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    await self._blacklist_key(key)
                
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt) # Exponential backoff
                    continue
                return [f"[Error: {str(e)}]"] * len(lines)
        
        return [f"[Error: Max Retries]"] * len(lines)
