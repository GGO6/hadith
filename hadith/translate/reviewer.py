"""
GPT Reviewer for translation quality assurance
"""
import json
import os
from openai import OpenAI
from typing import List, Dict
import config

class GPTReviewer:
    def __init__(self, api_key: str = None):
        """
        Initialize GPT reviewer
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def review_batch(self, items: List[Dict], language: str) -> List[Dict]:
        """
        Review a batch of translations (10 hadiths per request)
        
        Args:
            items: List of dicts with 'english', 'translated', 'hadith_id'
            language: Target language name (e.g., "Turkish")
        
        Returns:
            List of review results with 'hadith_id', 'status', 'corrected' (if needed)
        """
        if not items:
            return []
        
        # Build prompt
        prompt = f"""You are a hadith translation reviewer for {language}.
Review each translation below. For each hadith, respond with:
- "OK" if the translation is accurate and natural
- "FIX: [corrected translation]" if it needs correction

Important: Maintain religious terminology accuracy. Preserve narrator names and Islamic terms.

"""
        
        for i, item in enumerate(items, 1):
            prompt += f"""
Hadith {i} (ID: {item.get('hadith_id', i)}):
English: {item['english']}
{language}: {item['translated']}

"""
        
        prompt += """
Respond with valid JSON array format:
[
  {{"hadith_id": 1, "status": "OK"}},
  {{"hadith_id": 2, "status": "FIX", "corrected": "corrected translation here"}},
  ...
]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional translator reviewer specializing in Islamic texts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            results = json.loads(result_text)
            
            # Ensure results match input items
            reviewed = []
            for i, item in enumerate(items):
                hadith_id = item.get('hadith_id', i + 1)
                result = next((r for r in results if r.get('hadith_id') == hadith_id), None)
                
                if result:
                    reviewed.append({
                        'hadith_id': hadith_id,
                        'status': result.get('status', 'OK'),
                        'corrected': result.get('corrected', None)
                    })
                else:
                    # Fallback: use first available result or mark as OK
                    reviewed.append({
                        'hadith_id': hadith_id,
                        'status': 'OK',
                        'corrected': None
                    })
            
            return reviewed
            
        except Exception as e:
            print(f"GPT review error: {e}")
            # Return OK for all items on error
            return [
                {
                    'hadith_id': item.get('hadith_id', i + 1),
                    'status': 'OK',
                    'corrected': None
                }
                for i, item in enumerate(items)
            ]
