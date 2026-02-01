"""
API-based Translator using GPT-4o-mini for full translation
With parallel API calls for faster processing
"""
import os
from typing import List, Dict, Tuple
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import config from project root
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import config as _config

class APITranslator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key, timeout=120.0)
        self.lang_names = {k: v["name"] for k, v in _config.LANGUAGES.items()}

    def _translate_single_batch(self, batch_info: Tuple[int, List[str], str]) -> Tuple[int, List[str]]:
        batch_idx, batch_texts, lang_name = batch_info
        combined_text = "\n\n---\n\n".join([f"[{idx+1}] {text}" for idx, text in enumerate(batch_texts)])
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a professional translator specializing in Islamic religious texts. Translate the following English hadith texts to {lang_name}. Maintain religious terminology accurately and preserve meaning precisely. Keep narrator attributions if present. Return translations in the same format, numbered [1], [2], etc. Each translation should be on a separate line."},
                    {"role": "user", "content": combined_text}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            result = response.choices[0].message.content.strip()
            lines = [line.strip() for line in result.split('\n') if line.strip()]
            batch_translated = []
            for line in lines:
                if ']' in line:
                    line = line.split(']', 1)[1].strip()
                batch_translated.append(line)
            while len(batch_translated) < len(batch_texts):
                batch_translated.append(batch_texts[len(batch_translated)])
            return (batch_idx, batch_translated[:len(batch_texts)])
        except Exception as e:
            return (batch_idx, batch_texts)

    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        if not texts:
            return []
        lang_name = self.lang_names.get(target_language, target_language.capitalize())
        batch_size = 15
        max_parallel = 3
        batches = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batches.append((i // batch_size, batch_texts, lang_name))
        results = [None] * len(batches)
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            future_to_batch = {executor.submit(self._translate_single_batch, b): b[0] for b in batches}
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    idx, translated_texts = future.result()
                    results[idx] = translated_texts
                except Exception:
                    results[batch_idx] = batches[batch_idx][1]
        translated = []
        for batch_result in results:
            if batch_result:
                translated.extend(batch_result)
        return translated
