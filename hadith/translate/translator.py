"""
NLLB Translation Engine
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
            
            # Build language code to token ID mapping
            self.lang_to_id = {}
            # Try to get from tokenizer's special tokens
            for lang_code in [config.SOURCE_LANG] + [lang["nllb"] for lang in config.LANGUAGES.values()]:
                try:
                    # Encode the language code as a special token
                    tokens = self.tokenizer.encode(lang_code, add_special_tokens=False)
                    if tokens:
                        self.lang_to_id[lang_code] = tokens[0]
                except:
                    pass
            
            print("NLLB model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("\nTroubleshooting:")
            print("1. Check internet connection")
            print("2. Try: pip install --upgrade transformers")
            print("3. The model will be downloaded automatically (~1.3GB)")
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
        
        # Get target language token ID
        target_lang_id = self.lang_to_id.get(target_lang)
        if not target_lang_id:
            # Fallback: try to encode the language code
            try:
                lang_tokens = self.tokenizer.encode(target_lang, add_special_tokens=False)
                target_lang_id = lang_tokens[0] if lang_tokens else None
            except:
                target_lang_id = None
        
        with torch.no_grad():
            generate_kwargs = {
                **inputs,
                "max_length": 512,
                "num_beams": 5,
                "early_stopping": True
            }
            
            # Add forced_bos_token_id if we have a valid language token ID
            if target_lang_id:
                generate_kwargs["forced_bos_token_id"] = target_lang_id
            
            translated_tokens = self.model.generate(**generate_kwargs)
        
        translated_text = self.tokenizer.batch_decode(
            translated_tokens, 
            skip_special_tokens=True
        )[0]
        
        return translated_text
    
    def translate_batch(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate a batch of texts (more efficient)
        
        Args:
            texts: List of English texts
            target_lang: Target language code
        
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        # Filter empty texts
        non_empty_texts = [t if t and t.strip() else "" for t in texts]
        
        self.tokenizer.src_lang = config.SOURCE_LANG
        inputs = self.tokenizer(
            non_empty_texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Get target language token ID
        if hasattr(self.tokenizer, 'lang_code_to_id'):
            target_lang_id = self.tokenizer.lang_code_to_id[target_lang]
        else:
            target_lang_id = self.tokenizer.convert_tokens_to_ids(target_lang)
            if target_lang_id == self.tokenizer.unk_token_id:
                target_lang_id = None
        
        with torch.no_grad():
            generate_kwargs = {
                **inputs,
                "max_length": 512,
                "num_beams": 5,
                "early_stopping": True
            }
            if target_lang_id is not None:
                generate_kwargs["forced_bos_token_id"] = target_lang_id
            
            translated_tokens = self.model.generate(**generate_kwargs)
        
        translated_texts = self.tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True
        )
        
        return translated_texts
