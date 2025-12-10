"""
Interactive test script for the fine-tuned Qwen2 model
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# System prompt for marketing content generation (same as text_generator.py)
SYSTEM_PROMPT = """You are a professional marketing content writer specializing in Pakistani and Eastern fashion brands. Your expertise includes:

BRAND FOCUS:
- Pakistani fashion brands selling lawn suits, khaddar, cotton, silk, and embroidered clothing
- Seasonal collections: Summer (lawn, cotton) and Winter (khaddar, velvet, wool, shawls)
- Target audience: Modern Pakistani women and men who appreciate traditional wear with contemporary styling

CONTENT STYLE:
- Use elegant, sophisticated language that resonates with Pakistani culture
- Include relevant emojis (✨💫🌸👗) for social media content
- Add trending hashtags like #PakistaniFashion #LawnCollection #EasternWear #DesiFashion
- Reference cultural elements: Eid, weddings, festive seasons, mehndi, formal gatherings

TONE:
- Warm, inviting, and aspirational
- Blend of traditional values with modern aesthetics
- Emphasize quality, craftsmanship, and heritage
- Create urgency for limited collections and sales

OUTPUT REQUIREMENTS:
- Keep responses focused and concise
- Include call-to-actions where appropriate
- Use Pakistani English spellings and expressions
- Reference PKR for prices when mentioned"""


def load_model():
    """Load the fine-tuned model with merged LoRA weights"""
    import os
    
    print("=" * 60)
    print("Loading Fine-tuned Qwen2 Model")
    print("=" * 60)
    
    base_model_name = "Qwen/Qwen2-1.5B-Instruct"
    # Get the absolute path to the LoRA checkpoint
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lora_path = os.path.join(script_dir, "..", "TextGeneration", "models", "qwen2-marketing-lora")
    lora_path = os.path.normpath(lora_path)
    
    print(f"\nLoading base model: {base_model_name}")
    print(f"LoRA checkpoint: {lora_path}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # Load and merge LoRA weights
    from peft import PeftModel
    print("\nLoading and merging LoRA weights...")
    model = PeftModel.from_pretrained(model, lora_path)
    model = model.merge_and_unload()
    
    print(f"\n✓ Model loaded on: {next(model.parameters()).device}")
    return model, tokenizer


def generate_response(model, tokenizer, user_prompt: str, max_tokens: int = 256, temperature: float = 0.7):
    """Generate a response using the fine-tuned model"""
    
    # Create chat messages with system prompt
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    # Generate with better parameters to reduce hallucination
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            top_k=50,  # Added: limits vocabulary to top 50 tokens
            repetition_penalty=1.1,  # Added: penalize repetition
            min_new_tokens=20,  # Added: ensure minimum output length
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode only the new tokens
    generated_tokens = outputs[0][inputs['input_ids'].shape[1]:]
    response = tokenizer.decode(generated_tokens, skip_special_tokens=True)
    
    return response.strip()


def interactive_mode(model, tokenizer):
    """Run interactive prompt mode"""
    print("\n" + "=" * 60)
    print("Interactive Mode - Type your prompts")
    print("=" * 60)
    print("Commands:")
    print("  'quit' or 'exit' - Exit the program")
    print("  'temp <value>'   - Set temperature (e.g., 'temp 0.8')")
    print("  'tokens <value>' - Set max tokens (e.g., 'tokens 150')")
    print("=" * 60)
    
    max_tokens = 256
    temperature = 0.7
    
    while True:
        print(f"\n[Settings: max_tokens={max_tokens}, temperature={temperature}]")
        user_input = input("\n📝 Enter your prompt: ").strip()
        
        if not user_input:
            continue
        
        # Check for commands
        if user_input.lower() in ['quit', 'exit']:
            print("\n👋 Goodbye!")
            break
        
        if user_input.lower().startswith('temp '):
            try:
                temperature = float(user_input.split()[1])
                print(f"✓ Temperature set to {temperature}")
                continue
            except (ValueError, IndexError):
                print("❌ Invalid temperature value")
                continue
        
        if user_input.lower().startswith('tokens '):
            try:
                max_tokens = int(user_input.split()[1])
                print(f"✓ Max tokens set to {max_tokens}")
                continue
            except (ValueError, IndexError):
                print("❌ Invalid tokens value")
                continue
        
        # Generate response
        print("\n⏳ Generating...")
        print("-" * 40)
        
        response = generate_response(
            model, tokenizer, 
            user_input, 
            max_tokens=max_tokens, 
            temperature=temperature
        )
        
        print(response)
        print("-" * 40)


def main():
    # Load the model
    model, tokenizer = load_model()
    
    # Run interactive mode
    interactive_mode(model, tokenizer)


if __name__ == "__main__":
    main()
