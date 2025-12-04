"""
Test script to verify Qwen2-1.5B-Instruct Text Generator works with the Backend
Run this before starting the full backend server
"""
import asyncio
import sys

print("=" * 60)
print("Testing Qwen2-1.5B-Instruct Text Generator")
print("=" * 60)

# Test 1: Import and initialize Text Generator
print("\n[Test 1] Loading Text Generator with Qwen2...")
try:
    from text_generator import TextGenerator
    text_gen = TextGenerator()
    
    if text_gen.model_loaded:
        print("✓ Qwen2-1.5B-Instruct loaded successfully!")
    else:
        print("✗ Model failed to load")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error loading model: {e}")
    sys.exit(1)

# Test 2: Test caption generation
print("\n[Test 2] Testing caption generation...")
async def test_caption():
    result = await text_gen.generate_content(
        topic="Summer lawn collection with floral prints",
        content_type="caption"
    )
    if result:
        print(f"✓ Caption generated:")
        print("-" * 40)
        print(result[:500])
        print("-" * 40)
        return True
    else:
        print("✗ No response received")
        return False

# Test 3: Test marketing copy generation
print("\n[Test 3] Testing marketing copy generation...")
async def test_marketing_copy():
    result = await text_gen.generate_content(
        topic="Winter shawl collection for women",
        content_type="marketing_copy"
    )
    if result:
        print(f"✓ Marketing copy generated:")
        print("-" * 40)
        print(result[:500])
        print("-" * 40)
        return True
    else:
        print("✗ No response received")
        return False

# Test 4: Test slogan generation
print("\n[Test 4] Testing slogan generation...")
async def test_slogan():
    result = await text_gen.generate_content(
        topic="Eastern bridal wear collection",
        content_type="slogan"
    )
    if result:
        print(f"✓ Slogans generated:")
        print("-" * 40)
        print(result[:500])
        print("-" * 40)
        return True
    else:
        print("✗ No response received")
        return False

# Run all tests
async def run_all_tests():
    results = []
    results.append(await test_caption())
    results.append(await test_marketing_copy())
    results.append(await test_slogan())
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("\n✓ All tests passed! Qwen2 Text Generator is working.")
        print("You can now start the server with: python main.py")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
