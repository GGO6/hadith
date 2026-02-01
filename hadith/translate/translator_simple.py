"""
Simplified NLLB Translation Engine (working version)
"""
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import List, Optional
import config

class NLLBTranslator:
    def __init__(self, model_name: str = None):
        """
        Initialize NLLB translator
        
        Args:
            model_name: Model name (defaults to config.NLLB_MODEL)
        """
        self.model_name = model_name or config.NLLB_MODEL
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading NLLB model: {self.model_name} on {self.device}")
        print("This may take a few minutes on first run (downloading ~1.3GB)...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                src_lang=config.SOURCE_LANG
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name
            ).to(self.device)
            
            self.model.eval()
            print("NLLB model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
    
    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate a single text
        
        Args:
            text: English text to translate
            target_lang: Target language code (e.g., "tur_Latn")
        
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        self.tokenizer.src_lang = config.SOURCE_LANG
        inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Use tgt_lang parameter instead of forced_bos_token_id
        with torch.no_grad():
            translated_tokens = self.model.generate(
                **inputs,
                tgt_lang=target_lang,
                max_length=512,
                num_beams=5,
                early_stopping=True
            )
        
        translated_text = self.tokenizer.batch_decode(
            translated_tokens, 
            skip_special_tokens=True
        )[0]
        
        return translated_text
