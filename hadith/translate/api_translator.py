"""
API-based Translator using GPT-4o-mini for full translation
With parallel API calls for faster processing
"""
import os
import time
from typing import List, Dict, Tuple
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import config

class APITranslator:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """
        Initialize API translator
        
        Args:
            api_key: OpenAI API key (if None, reads from OPENAI_API_KEY env)
            model: Model to use (default: gpt-4o-mini)
        """
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter"
            )
        
        self.api_key = api_key
        self.model = model
        self.client = OpenAI(api_key=self.api_key, timeout=120.0)  # 2 minute timeout
        
        # Language names mapping
        self.lang_names = {
            "turkish": "Turkish",
            "french": "French", 
            "indonesian": "Indonesian",
            "urdu": "Urdu",
            "bengali": "Bengali",
            "german": "German",
            "spanish": "Spanish",
            "russian": "Russian"
        }
        
        print(f"API Translator initialized (model: {self.model})")
    
    def translate(self, text: str, target_language: str) -> str:
        """
        Translate a single text using GPT API
        
        Args:
            text: English text to translate
            target_language: Target language name (e.g., "turkish")
        
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        lang_name = self.lang_names.get(target_language, target_language.capitalize())
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator specializing in Islamic religious texts. "
                                 f"Translate the following English hadith text to {lang_name}. "
                                 f"Maintain the religious terminology accurately and preserve the meaning precisely. "
                                 f"Keep the narrator attribution if present."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=1000
            )
            
            translated = response.choices[0].message.content.strip()
            return translated
            
        except Exception as e:
            print(f"API translation error: {e}")
            return text
    
    def _translate_single_batch(self, batch_info: Tuple[int, List[str], str]) -> Tuple[int, List[str]]:
        """
        Translate a single batch (used for parallel processing)
        
        Args:
            batch_info: Tuple of (batch_index, texts, lang_name)
        
        Returns:
            Tuple of (batch_index, translated_texts)
        """
        batch_idx, batch_texts, lang_name = batch_info
        
        # Combine texts with separators
        combined_text = "\n\n---\n\n".join([
            f"[{idx+1}] {text}" for idx, text in enumerate(batch_texts)
        ])
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a professional translator specializing in Islamic religious texts. "
                                 f"Translate the following English hadith texts to {lang_name}. "
                                 f"Maintain religious terminology accurately and preserve meaning precisely. "
                                 f"Keep narrator attributions if present. "
                                 f"Return translations in the same format, numbered [1], [2], etc. "
                                 f"Each translation should be on a separate line."
                    },
                    {
                        "role": "user",
                        "content": combined_text
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Parse results (simple split by lines)
            lines = [line.strip() for line in result.split('\n') if line.strip()]
            
            # Extract translations (remove [N] markers)
            batch_translated = []
            for line in lines:
                if ']' in line:
                    line = line.split(']', 1)[1].strip()
                batch_translated.append(line)
            
            # Ensure we have the right number of translations
            while len(batch_translated) < len(batch_texts):
                batch_translated.append(batch_texts[len(batch_translated)])
            
            return (batch_idx, batch_translated[:len(batch_texts)])
            
        except Exception as e:
            print(f"      ⚠️ Batch {batch_idx+1} error: {e}")
            # Return original texts on error
            return (batch_idx, batch_texts)
    
    def translate_batch(self, texts: List[str], target_language: str) -> List[str]:
        """
        Translate a batch of texts using PARALLEL API calls (3x faster)
        
        Args:
            texts: List of English texts
            target_language: Target language name
        
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        lang_name = self.lang_names.get(target_language, target_language.capitalize())
        
        # Process in batches - larger batches are faster but must stay within token limits
        batch_size = 15
        max_parallel = 3  # 3 parallel calls - safe for rate limits
        
        # Split into batches
        batches = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_idx = i // batch_size
            batches.append((batch_idx, batch_texts, lang_name))
        
        total_batches = len(batches)
        print(f"      🚀 {total_batches} batches ({max_parallel} parallel)...", end='', flush=True)
        
        # Results storage (indexed by batch_idx to maintain order)
        results = [None] * total_batches
        completed = 0
        
        # Process batches in parallel groups
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._translate_single_batch, batch): batch[0]
                for batch in batches
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    idx, translated_texts = future.result()
                    results[idx] = translated_texts
                    completed += 1
                    
                    # Progress indicator
                    if completed % 5 == 0 or completed == total_batches:
                        print(f" {completed}/{total_batches}", end='', flush=True)
                        
                except Exception as e:
                    print(f" ❌{batch_idx}", end='', flush=True)
                    # Use original texts on error
                    original_batch = batches[batch_idx][1]
                    results[batch_idx] = original_batch
        
        print(f" ✓")
        
        # Flatten results maintaining order
        translated = []
        for batch_result in results:
            if batch_result:
                translated.extend(batch_result)
        
        return translated
