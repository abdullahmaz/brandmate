"""
API Status Checker for Gemini API Keys
Tests all API keys to verify they're working and checks usage limits
"""

import os
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import google.generativeai as genai
    from PIL import Image
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install google-generativeai Pillow")
    exit(1)


class GeminiAPITester:
    def __init__(self):
        """Initialize API tester"""
        self.model_name = "gemini-2.0-flash-exp"
        self.test_prompt = "Say 'Hello, API is working!' in exactly 5 words."
        
    def test_single_api_key(self, api_key, key_index=1):
        """Test a single API key for functionality and basic limits"""
        
        result = {
            "key_index": key_index,
            "api_key": f"{api_key[:8]}...{api_key[-4:]}" if api_key else "None",  # Masked for security
            "status": "Unknown",
            "response_time_ms": None,
            "model_available": False,
            "generation_works": False,
            "error_message": None,
            "quota_status": "Unknown",
            "test_response": None
        }
        
        if not api_key:
            result["status"] = "INVALID"
            result["error_message"] = "Empty or None API key"
            return result
            
        try:
            start_time = time.time()
            
            # Configure API
            genai.configure(api_key=api_key)
            
            # Test 1: Check if we can create the model
            try:
                model = genai.GenerativeModel(model_name=self.model_name)
                result["model_available"] = True
            except Exception as e:
                result["status"] = "MODEL_ERROR"
                result["error_message"] = f"Model creation failed: {str(e)[:100]}"
                return result
            
            # Test 2: Try a simple generation
            try:
                response = model.generate_content(
                    self.test_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.1,
                        max_output_tokens=20
                    )
                )
                
                end_time = time.time()
                result["response_time_ms"] = round((end_time - start_time) * 1000)
                result["generation_works"] = True
                result["test_response"] = response.text.strip()
                result["status"] = "WORKING"
                result["quota_status"] = "Available"
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Parse different error types
                if "quota" in error_str or "limit" in error_str:
                    result["status"] = "QUOTA_EXCEEDED"
                    result["quota_status"] = "Exceeded"
                    result["error_message"] = "Daily quota exceeded"
                elif "api key not valid" in error_str or "invalid" in error_str:
                    result["status"] = "INVALID_KEY"
                    result["error_message"] = "API key is invalid"
                elif "permission" in error_str or "forbidden" in error_str:
                    result["status"] = "PERMISSION_ERROR"
                    result["error_message"] = "Permission denied - check API access"
                elif "not found" in error_str:
                    result["status"] = "MODEL_NOT_FOUND"
                    result["error_message"] = f"Model {self.model_name} not available"
                else:
                    result["status"] = "API_ERROR"
                    result["error_message"] = str(e)[:200]
                    
        except Exception as e:
            result["status"] = "CONNECTION_ERROR"
            result["error_message"] = f"Failed to connect: {str(e)[:100]}"
            
        return result
    
    def test_all_keys_parallel(self, api_keys, max_workers=3):
        """Test all API keys in parallel for faster results"""
        
        print("🔍 Testing API Keys in Parallel...")
        print("=" * 60)
        
        results = []
        
        # Test keys in parallel (but limit concurrent requests)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_key = {
                executor.submit(self.test_single_api_key, key, i+1): (key, i+1) 
                for i, key in enumerate(api_keys)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_key):
                key, index = future_to_key[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Print immediate feedback
                    status = result["status"]
                    key_display = result["api_key"]
                    time_ms = result.get("response_time_ms", "N/A")
                    
                    if status == "WORKING":
                        print(f"✅ Key #{index} ({key_display}): WORKING ({time_ms}ms)")
                    elif status == "QUOTA_EXCEEDED":
                        print(f"⚠️  Key #{index} ({key_display}): QUOTA EXCEEDED")
                    elif status == "INVALID_KEY":
                        print(f"❌ Key #{index} ({key_display}): INVALID")
                    else:
                        print(f"❌ Key #{index} ({key_display}): {status}")
                        
                except Exception as e:
                    print(f"❌ Key #{index}: Test failed - {e}")
        
        # Sort results by key_index for consistent output
        results.sort(key=lambda x: x["key_index"])
        return results
    
    def print_detailed_report(self, results):
        """Print detailed status report"""
        
        print("\n" + "=" * 60)
        print("📊 DETAILED API STATUS REPORT")
        print("=" * 60)
        
        working_keys = []
        quota_exceeded_keys = []
        invalid_keys = []
        other_errors = []
        
        for result in results:
            key_num = result["key_index"]
            status = result["status"]
            
            print(f"\n🔑 API Key #{key_num}: {result['api_key']}")
            print(f"   Status: {status}")
            
            if result["response_time_ms"]:
                print(f"   Response Time: {result['response_time_ms']}ms")
            
            if result["test_response"]:
                print(f"   Test Response: '{result['test_response']}'")
            
            if result["error_message"]:
                print(f"   Error: {result['error_message']}")
            
            # Categorize keys
            if status == "WORKING":
                working_keys.append(key_num)
            elif status == "QUOTA_EXCEEDED":
                quota_exceeded_keys.append(key_num)
            elif status in ["INVALID_KEY", "PERMISSION_ERROR"]:
                invalid_keys.append(key_num)
            else:
                other_errors.append(key_num)
        
        # Summary
        print("\n" + "=" * 60)
        print("📈 SUMMARY")
        print("=" * 60)
        print(f"✅ Working Keys: {len(working_keys)} - {working_keys if working_keys else 'None'}")
        print(f"⚠️  Quota Exceeded: {len(quota_exceeded_keys)} - {quota_exceeded_keys if quota_exceeded_keys else 'None'}")
        print(f"❌ Invalid Keys: {len(invalid_keys)} - {invalid_keys if invalid_keys else 'None'}")
        print(f"🔧 Other Errors: {len(other_errors)} - {other_errors if other_errors else 'None'}")
        
        total_usable = len(working_keys)
        print(f"\n🎯 USABLE KEYS FOR CAPTIONING: {total_usable}/{len(results)}")
        
        if total_usable == 0:
            print("⚠️  WARNING: No working API keys found!")
            print("   - Check key validity at: https://aistudio.google.com/app/apikey")
            print("   - Ensure Generative AI API is enabled")
            print("   - Wait for quota reset (usually 24 hours)")
        elif total_usable < len(results):
            print("ℹ️  Some keys have issues. Captioning will use working keys only.")
        else:
            print("🎉 All keys are working! Ready for captioning.")
        
        return {
            "working_keys": working_keys,
            "quota_exceeded": quota_exceeded_keys,
            "invalid_keys": invalid_keys,
            "other_errors": other_errors,
            "total_usable": total_usable
        }
    
    def save_report_to_file(self, results, filename=None):
        """Save detailed report to JSON file"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"api_status_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "model_tested": self.model_name,
            "total_keys_tested": len(results),
            "results": results
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Detailed report saved to: {filename}")
            return filename
        except Exception as e:
            print(f"\n❌ Failed to save report: {e}")
            return None


def load_api_keys_from_file(file_path="run_daily_captioning.py"):
    """Load API keys from the daily captioning script"""
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []
    
    try:
        # Read the file and extract API_KEYS list
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple extraction of API_KEYS list
        import re
        pattern = r'API_KEYS\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            keys_text = match.group(1)
            # Extract quoted strings
            key_pattern = r'"([^"]+)"'
            keys = re.findall(key_pattern, keys_text)
            print(f"✅ Loaded {len(keys)} API keys from {file_path}")
            return keys
        else:
            print(f"❌ Could not find API_KEYS in {file_path}")
            return []
            
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return []


def main():
    print("🔧 GEMINI API STATUS CHECKER")
    print("=" * 60)
    print("Checking all API keys for functionality and limits...")
    print()
    
    # Load API keys from run_daily_captioning.py
    api_keys = load_api_keys_from_file()
    
    if not api_keys:
        print("❌ No API keys found. Please check run_daily_captioning.py")
        print("   Or provide keys manually:")
        print("   python api_status_checker.py")
        return
    
    # Initialize tester
    tester = GeminiAPITester()
    
    # Test all keys
    results = tester.test_all_keys_parallel(api_keys)
    
    # Print detailed report
    summary = tester.print_detailed_report(results)
    
    # Save report to file
    tester.save_report_to_file(results)
    
    print("\n" + "=" * 60)
    print("✅ API Status Check Complete!")
    print("=" * 60)
    
    # Return summary for programmatic use
    return summary


if __name__ == '__main__':
    main()