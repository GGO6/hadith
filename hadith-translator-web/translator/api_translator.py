"""
API-based Translator using GPT-4o-mini for full translation.
Supports optional parallel requests; on 429/timeout waits then retries.
"""
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
from openai import OpenAI, APITimeoutError

logger = logging.getLogger("hadith.translator")

# Import config from project root
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
import config as _config


def _is_rate_limit(e: Exception) -> bool:
    return getattr(e, "status_code", None) == 429 or "429" in str(e) or "rate limit" in str(e).lower()


def _is_timeout(e: Exception) -> bool:
    if isinstance(e, APITimeoutError):
        return True
    msg = str(e).lower()
    return "timeout" in msg or "timed out" in msg or "read operation timed out" in msg


def _is_retryable(e: Exception) -> bool:
    return _is_rate_limit(e) or _is_timeout(e)


class APITranslator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        self.api_key = api_key
        self.model = model
        timeout_sec = float(os.getenv("OPENAI_TIMEOUT_SEC", "300"))
        self.client = OpenAI(api_key=self.api_key, timeout=timeout_sec, max_retries=0)
        self.lang_names = {k: v["name"] for k, v in _config.LANGUAGES.items()}

    def _translate_single_batch(self, batch_info: Tuple[int, List[str], str]) -> Tuple[int, List[str]]:
        batch_idx, batch_texts, lang_name = batch_info
        combined_text = "\n\n---\n\n".join([f"[{idx+1}] {text}" for idx, text in enumerate(batch_texts)])
        retry_wait = int(os.getenv("OPENAI_RATE_LIMIT_WAIT", "60"))
        max_retries = int(os.getenv("OPENAI_RATE_LIMIT_RETRIES", "5"))
        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"You are a professional translator specializing in Islamic religious texts. Translate the following English hadith texts into {lang_name} only. Output MUST be in {lang_name} only—never return the original English. Maintain religious terminology accurately and preserve meaning. Keep narrator attributions if present. Reply with numbered lines [1], [2], etc. Each line must be the translation in {lang_name} of the corresponding item."},
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
                if _is_retryable(e) and attempt < max_retries:
                    kind = "timeout" if _is_timeout(e) else "429 rate limit"
                    logger.warning("%s: waiting %s sec then retry (%s/%s)", kind, retry_wait, attempt + 1, max_retries)
                    time.sleep(retry_wait)
                    continue
                logger.exception("translate_batch failed: %s", e)
                return (batch_idx, batch_texts)
        return (batch_idx, batch_texts)

    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        if not texts:
            return []
        lang_name = self.lang_names.get(target_language, target_language.capitalize())
        batch_size = min(15, max(1, int(os.getenv("OPENAI_BATCH_SIZE", "12"))))
        delay_sec = float(os.getenv("OPENAI_DELAY_SEC", "2.0"))
        parallel = min(3, max(1, int(os.getenv("OPENAI_PARALLEL_REQUESTS", "2"))))
        translated = []
        batch_infos = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_infos.append((i // batch_size, batch_texts, lang_name))
        if parallel <= 1:
            for batch_info in batch_infos:
                _, batch_result = self._translate_single_batch(batch_info)
                translated.extend(batch_result)
                if batch_info[0] < len(batch_infos) - 1:
                    time.sleep(delay_sec)
            return translated
        round_delay = delay_sec
        for round_start in range(0, len(batch_infos), parallel):
            chunk = batch_infos[round_start : round_start + parallel]
            with ThreadPoolExecutor(max_workers=len(chunk)) as ex:
                futures = {ex.submit(self._translate_single_batch, info): info for info in chunk}
                results = []
                for fut in as_completed(futures):
                    batch_idx, batch_result = fut.result()
                    results.append((batch_idx, batch_result))
            results.sort(key=lambda x: x[0])
            for _, batch_result in results:
                translated.extend(batch_result)
            if round_start + len(chunk) < len(batch_infos):
                time.sleep(round_delay)
        return translated
