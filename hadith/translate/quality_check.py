"""
Quality checking for translations using back-translation and semantic similarity
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict
import config
from translator import NLLBTranslator

class QualityChecker:
    def __init__(self):
        """Initialize quality checker with similarity model and translator"""
        print("Loading similarity model...")
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.nllb = NLLBTranslator()
        print("Quality checker initialized")
    
    def check(self, original_en: str, translated: str, target_lang: str) -> Dict:
        """
        Check translation quality using multiple metrics
        
        Args:
            original_en: Original English text
            translated: Translated text
            target_lang: Target language code
        
        Returns:
            Dictionary with quality metrics and confidence level
        """
        if not original_en or not translated:
            return {
                "similarity": 0.0,
                "length_ratio": 0.0,
                "confidence": "LOW",
                "needs_review": True
            }
        
        # 1. Back-translation
        try:
            back_translated = self.nllb.translate(translated, config.SOURCE_LANG)
        except Exception as e:
            print(f"Back-translation error: {e}")
            back_translated = ""
        
        # 2. Semantic similarity
        try:
            emb1 = self.similarity_model.encode([original_en])
            emb2 = self.similarity_model.encode([back_translated])
            similarity = float(cosine_similarity(emb1, emb2)[0][0])
        except Exception as e:
            print(f"Similarity calculation error: {e}")
            similarity = 0.0
        
        # 3. Length ratio
        length_ratio = len(translated) / len(original_en) if len(original_en) > 0 else 0.0
        
        # 4. Determine confidence level
        if similarity >= config.SIMILARITY_HIGH and \
           config.LENGTH_RATIO_MIN <= length_ratio <= config.LENGTH_RATIO_MAX:
            confidence = "HIGH"
        elif similarity >= config.SIMILARITY_MEDIUM and \
             config.LENGTH_RATIO_MIN <= length_ratio <= config.LENGTH_RATIO_MAX:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return {
            "similarity": round(similarity, 4),
            "length_ratio": round(length_ratio, 4),
            "confidence": confidence,
            "needs_review": confidence != "HIGH",
            "back_translated": back_translated
        }
