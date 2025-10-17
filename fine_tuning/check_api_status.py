"""
Simple API Status & Daily Capacity Checker
Just shows if each API key is valid and daily capacity remaining
"""

import os
import re
import time

try:
    import google.generativeai as genai
except ImportError:
    print("❌ Missing google-generativeai. Install with: pip install google-generativeai")
    exit(1)


def load_api_keys():
    """Load API keys from run_daily_captioning.py"""
    try:
        with open("run_daily_captioning.py", 'r') as f:
            content = f.read()
        
        # Extract API_KEYS list
        pattern = r'API_KEYS\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            keys_text = match.group(1)
            keys = re.findall(r'"([^"]+)"', keys_text)
            return keys
        else:
            print("❌ Could not find API_KEYS in run_daily_captioning.py")
            return []
            
    except FileNotFoundError:
        print("❌ run_daily_captioning.py not found")
        return []


def check_api_key(api_key, key_num):
    """Check single API key validity and estimate remaining capacity"""
    
    try:
        # Configure API
        genai.configure(api_key=api_key)
        
        # Try a minimal test
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        response = model.generate_content(
            "Hi",
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=5
            )
        )
        
        # If we get here, key is working
        # Note: We can't easily check exact quota remaining without making many requests
        # So we'll just indicate it's available
        return {
            "valid": True,
            "status": "✅ VALID",
            "capacity": "Available",
            "error": None
        }
        
    except Exception as e:
        error_str = str(e).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return {
                "valid": False,
                "status": "⚠️ QUOTA",
                "capacity": "0 (Exceeded)",
                "error": "Daily quota exceeded"
            }
        elif "api key not valid" in error_str or "invalid" in error_str:
            return {
                "valid": False,
                "status": "❌ INVALID",
                "capacity": "N/A",
                "error": "Invalid API key"
            }
        else:
            return {
                "valid": False,
                "status": "❌ ERROR",
                "capacity": "Unknown",
                "error": str(e)[:50]
            }


def main():
    print("🔍 API STATUS & CAPACITY CHECK")
    print("=" * 40)
    
    # Load keys
    api_keys = load_api_keys()
    
    if not api_keys:
        print("❌ No API keys found")
        return
    
    print(f"Testing {len(api_keys)} API keys...\n")
    
    # Check each key
    valid_count = 0
    total_capacity = 0
    
    for i, key in enumerate(api_keys, 1):
        key_display = f"{key[:8]}...{key[-4:]}"
        print(f"Key #{i} ({key_display}): ", end="", flush=True)
        
        result = check_api_key(key, i)
        
        print(f"{result['status']} - Capacity: {result['capacity']}")
        
        if result["valid"]:
            valid_count += 1
            # Estimate 125 images per working key (daily limit)
            total_capacity += 125
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 SUMMARY")
    print("=" * 40)
    print(f"Valid Keys: {valid_count}/{len(api_keys)}")
    print(f"Daily Capacity: {total_capacity} images")
    print(f"Per Category: {total_capacity // 4} images" if total_capacity > 0 else "Per Category: 0 images")
    
    if valid_count == 0:
        print("\n⚠️ No working keys - check API keys!")
    elif valid_count < len(api_keys):
        print(f"\n⚠️ {len(api_keys) - valid_count} keys have issues")
    else:
        print("\n✅ All keys working - ready to caption!")


if __name__ == '__main__':
    main()