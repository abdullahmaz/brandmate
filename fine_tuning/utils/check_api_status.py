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
        with open("scripts/run_daily_captioning.py", 'r') as f:
            content = f.read()
        
        # Extract API_KEYS list
        pattern = r'API_KEYS\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            keys_text = match.group(1)
            keys = re.findall(r'"([^"]+)"', keys_text)
            return keys
        else:
            print("❌ Could not find API_KEYS in scripts/run_daily_captioning.py")
            return []
            
    except FileNotFoundError:
        print("❌ scripts/run_daily_captioning.py not found")
        return []


def extract_quota_info(error_message):
    """Extract detailed quota information from error message"""
    import re
    
    # Parse quota limit and used count from error message
    # Example: "quota_value: 50" means daily limit is 50
    quota_limit_match = re.search(r'quota_value:\s*(\d+)', error_message)
    
    # Look for retry delay to estimate when quota resets
    retry_delay_match = re.search(r'retry_delay.*?seconds:\s*(\d+)', error_message, re.DOTALL)
    
    # Look for quota metric type
    metric_match = re.search(r'quota_metric:\s*"([^"]+)"', error_message)
    
    quota_limit = int(quota_limit_match.group(1)) if quota_limit_match else None
    retry_seconds = int(retry_delay_match.group(1)) if retry_delay_match else None
    metric_type = metric_match.group(1) if metric_match else "Unknown"
    
    # Determine if it's daily or per-minute limit
    is_daily = "PerDay" in metric_type
    is_per_minute = "PerMinute" in metric_type
    
    return {
        "limit": quota_limit,
        "retry_seconds": retry_seconds,
        "metric_type": metric_type,
        "is_daily": is_daily,
        "is_per_minute": is_per_minute,
        "remaining": 0  # If we hit quota, remaining is 0
    }


def estimate_remaining_quota(model, key_num):
    """Estimate remaining quota by making test requests"""
    try:
        # Make a few rapid requests to test per-minute limits
        for i in range(3):
            response = model.generate_content(
                f"Test {i}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=3
                )
            )
            time.sleep(0.1)  # Small delay
        
        # If we get here, we have some quota remaining
        # For free tier: usually 50 per day, 10 per minute
        return "Available (Est. 40+ images)"
        
    except Exception as e:
        error_str = str(e)
        if "quota" in error_str.lower() or "limit" in error_str.lower():
            quota_info = extract_quota_info(error_str)
            if quota_info["is_daily"] and quota_info["limit"]:
                return f"0 of {quota_info['limit']} daily (Exhausted)"
            elif quota_info["is_per_minute"] and quota_info["limit"]:
                return f"Per-minute limit ({quota_info['limit']}/min) hit"
            else:
                return "Quota exceeded"
        else:
            return "Available (Estimation failed)"


def check_api_key(api_key, key_num):
    """Check single API key validity and detailed quota information"""
    
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
        
        # If we get here, key is working - try to estimate remaining quota
        # Make a few more requests to probe the limits
        remaining_estimate = estimate_remaining_quota(model, key_num)
        
        return {
            "valid": True,
            "status": "✅ VALID",
            "capacity": remaining_estimate,
            "daily_remaining": remaining_estimate,
            "error": None
        }
        
    except Exception as e:
        error_str = str(e)
        error_str_lower = error_str.lower()
        
        if "quota" in error_str_lower or "limit" in error_str_lower:
            quota_info = extract_quota_info(error_str)
            
            if quota_info["is_daily"] and quota_info["limit"]:
                capacity_msg = f"0 of {quota_info['limit']} daily images"
            elif quota_info["is_per_minute"]:
                capacity_msg = f"Per-minute limit hit ({quota_info['limit']}/min)"
            else:
                capacity_msg = "Quota exceeded"
            
            return {
                "valid": False,
                "status": "⚠️ QUOTA",
                "capacity": capacity_msg,
                "daily_remaining": 0,
                "quota_info": quota_info,
                "error": "Quota exceeded"
            }
        elif "api key not valid" in error_str_lower or "invalid" in error_str_lower:
            return {
                "valid": False,
                "status": "❌ INVALID",
                "capacity": "N/A",
                "daily_remaining": 0,
                "error": "Invalid API key"
            }
        else:
            return {
                "valid": False,
                "status": "❌ ERROR",
                "capacity": "Unknown",
                "daily_remaining": 0,
                "error": str(e)[:50]
            }


def main():
    print("🔍 API STATUS & DETAILED QUOTA CHECK")
    print("=" * 50)
    
    # Load keys
    api_keys = load_api_keys()
    
    if not api_keys:
        print("❌ No API keys found")
        return
    
    print(f"Testing {len(api_keys)} API keys...\n")
    
    # Check each key
    valid_count = 0
    total_estimated_remaining = 0
    quota_exhausted_count = 0
    results = []
    
    for i, key in enumerate(api_keys, 1):
        key_display = f"{key[:8]}...{key[-4:]}"
        print(f"Key #{i} ({key_display}):")
        print("  ", end="", flush=True)
        
        result = check_api_key(key, i)
        results.append(result)
        
        print(f"Status: {result['status']}")
        print(f"  Capacity: {result['capacity']}")
        
        if result["valid"]:
            valid_count += 1
            # Try to extract number from capacity string for better estimation
            if "40+" in result['capacity']:
                total_estimated_remaining += 40
            else:
                total_estimated_remaining += 50  # Conservative estimate
        elif "quota" in result.get("error", "").lower():
            quota_exhausted_count += 1
            
        print()  # Empty line between keys
    
    # Enhanced Summary
    print("=" * 50)
    print("📊 DETAILED SUMMARY")
    print("=" * 50)
    print(f"Valid Keys: {valid_count}/{len(api_keys)}")
    print(f"Quota Exhausted: {quota_exhausted_count}/{len(api_keys)}")
    print(f"Estimated Remaining: ~{total_estimated_remaining} images total")
    
    if total_estimated_remaining > 0:
        per_category = total_estimated_remaining // 4
        print(f"Per Category: ~{per_category} images each")
        print(f"  • Summer_Men: ~{per_category} images")
        print(f"  • Summer_Women: ~{per_category} images") 
        print(f"  • Winter_Men: ~{per_category} images")
        print(f"  • Winter_Women: ~{per_category} images")
    else:
        print("Per Category: 0 images (all quotas exhausted)")
    
    # Status message
    if valid_count == 0:
        print("\n⚠️ No working keys - check API keys!")
    elif quota_exhausted_count == len(api_keys):
        print("\n⚠️ All quotas exhausted - try again tomorrow!")
    elif quota_exhausted_count > 0:
        print(f"\n⚠️ {quota_exhausted_count} keys exhausted, {valid_count} still working")
        print("💡 Run captioning to use remaining quota")
    else:
        print("\n✅ All keys working - ready for full captioning!")
        
    # Show quota reset info if any keys are exhausted
    exhausted_keys = [r for r in results if not r["valid"] and "quota" in r.get("error", "").lower()]
    if exhausted_keys and any("quota_info" in r for r in exhausted_keys):
        print("\n🕒 Quota Reset Information:")
        for i, r in enumerate(exhausted_keys, 1):
            if "quota_info" in r and r["quota_info"]["retry_seconds"]:
                hours = r["quota_info"]["retry_seconds"] // 3600
                minutes = (r["quota_info"]["retry_seconds"] % 3600) // 60
                if hours > 0:
                    print(f"  Key #{i}: Resets in {hours}h {minutes}m")
                else:
                    print(f"  Key #{i}: Resets in {minutes}m")


if __name__ == '__main__':
    main()