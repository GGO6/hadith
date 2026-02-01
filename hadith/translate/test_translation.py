#!/usr/bin/env python3
"""
Quick test script to verify translation works
"""
import sys
import config
from translator import NLLBTranslator

def main():
    print("=" * 60)
    print("Testing NLLB Translation")
    print("=" * 60)
    
    # Test text
    test_text = "I heard the Messenger of Allah (peace be upon him) say: \"Actions are judged by intentions.\""
    
    print(f"\nOriginal English:")
    print(test_text)
    
    # Initialize translator
    print("\nInitializing translator (this may take a few minutes on first run)...")
    translator = NLLBTranslator()
    
    # Test translation to Turkish
    print("\nTranslating to Turkish...")
    turkish = translator.translate(test_text, config.LANGUAGES["turkish"]["nllb"])
    print(f"Turkish: {turkish}")
    
    # Test translation to French
    print("\nTranslating to French...")
    french = translator.translate(test_text, config.LANGUAGES["french"]["nllb"])
    print(f"French: {french}")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
