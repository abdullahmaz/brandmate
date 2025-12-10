"""
Interactive Test Script for Qwen2-1.5B-Instruct Text Generator
Enter your prompt to generate marketing content
"""
import asyncio
import sys

text_gen = None

def load_model():
    global text_gen
    print("=" * 60)
    print("Qwen2-1.5B-Instruct Text Generator")
    print("=" * 60)
    
    print("\n⏳ Loading model...")
    try:
        from text_generator import TextGenerator
        text_gen = TextGenerator()
        
        if text_gen.model_loaded:
            print("✓ Model loaded successfully!\n")
            return True
        else:
            print("✗ Model failed to load")
            return False
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        return False


async def generate_from_prompt(prompt: str):
    """Generate content from user prompt"""
    if not text_gen or not text_gen.model_loaded:
        print("✗ Model not loaded!")
        return None
    
    print(f"\n⏳ Generating response...")
    result = await text_gen.generate_content(
        topic=prompt,
        content_type="marketing_copy"
    )
    return result


def interactive_mode():
    """Run interactive prompt mode"""
    print("🎯 Enter your prompts below (type 'quit' to exit)\n")
    
    while True:
        print("-" * 60)
        prompt = input("Your prompt: ").strip()
        
        if not prompt:
            print("❌ Prompt cannot be empty!")
            continue
        
        if prompt.lower() == 'quit':
            print("\n👋 Goodbye!")
            break
        
        # Generate content
        result = asyncio.run(generate_from_prompt(prompt))
        
        if result:
            print("\n" + "=" * 60)
            print("✅ Generated Response:")
            print("=" * 60)
            print(result)
            print("=" * 60)
        else:
            print("❌ Failed to generate content. Try again.")


if __name__ == "__main__":
    # Load model first
    if not load_model():
        sys.exit(1)
    
    # Check for command line argument
    if len(sys.argv) >= 2:
        # Usage: python test_qwen2.py "your prompt here"
        prompt = " ".join(sys.argv[1:])
        result = asyncio.run(generate_from_prompt(prompt))
        if result:
            print("\n" + "=" * 60)
            print("✅ Generated Response:")
            print("=" * 60)
            print(result)
            print("=" * 60)
        else:
            print("❌ Failed to generate content.")
    else:
        # Interactive mode
        interactive_mode()
