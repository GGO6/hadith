#!/usr/bin/env python3
"""
Monitor translation progress
"""
import json
import os
from pathlib import Path
from datetime import datetime

def format_size(size_bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def monitor_translation():
    """Monitor translation progress"""
    script_dir = Path(__file__).parent
    log_file = script_dir / "translation_run.log"
    checkpoints_dir = script_dir / "checkpoints"
    output_dir = script_dir / "output"
    
    print("=" * 70)
    print("Translation Progress Monitor")
    print("=" * 70)
    
    # Check log file
    if log_file.exists():
        log_size = log_file.stat().st_size
        print(f"\n📄 Log File: {log_file}")
        print(f"   Size: {format_size(log_size)}")
        
        # Read last 20 lines
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                print(f"\n📝 Last 20 lines:")
                print("-" * 70)
                for line in lines[-20:]:
                    print(line.rstrip())
    else:
        print(f"\n⚠️  Log file not found: {log_file}")
    
    # Check checkpoints
    print(f"\n💾 Checkpoints:")
    print("-" * 70)
    if checkpoints_dir.exists():
        checkpoint_files = list(checkpoints_dir.glob("*.json"))
        if checkpoint_files:
            for cp_file in sorted(checkpoint_files):
                try:
                    with open(cp_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        lang = cp_file.stem.replace('_checkpoint', '')
                        total = data.get('total_hadiths', 0)
                        translated = data.get('translated_count', 0)
                        progress = (translated / total * 100) if total > 0 else 0
                        print(f"   {lang}: {translated}/{total} ({progress:.1f}%)")
                        if 'last_updated' in data:
                            print(f"      Last updated: {data['last_updated']}")
                except Exception as e:
                    print(f"   {cp_file.name}: Error reading - {e}")
        else:
            print("   No checkpoints found yet")
    else:
        print(f"   Checkpoints directory not found: {checkpoints_dir}")
    
    # Check output files
    print(f"\n📦 Output Files:")
    print("-" * 70)
    if output_dir.exists():
        output_files = list(output_dir.rglob("*.json"))
        if output_files:
            total_size = 0
            for out_file in sorted(output_files):
                size = out_file.stat().st_size
                total_size += size
                rel_path = out_file.relative_to(output_dir)
                print(f"   {rel_path}: {format_size(size)}")
            print(f"\n   Total output size: {format_size(total_size)}")
        else:
            print("   No output files found yet")
    else:
        print(f"   Output directory not found: {output_dir}")
    
    print("\n" + "=" * 70)
    print("💡 Tips:")
    print("   - Watch live progress: tail -f translation_run.log")
    print("   - Check specific language: cat checkpoints/{language}_checkpoint.json")
    print("   - View translations: cat output/{language}/all_translations.json | jq")
    print("=" * 70)

if __name__ == "__main__":
    monitor_translation()
