"""
Evaluate Fine-tuned Qwen2 Marketing Model
Tests the model across different:
- Content types (captions, ads, campaigns, etc.)
- Creativity levels (temperature settings)
- Seasonal contexts (summer/winter)
- Accuracy of prompt following
"""

import os
import json
import torch
from pathlib import Path
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# ============== CONFIGURATION ==============

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LORA_MODEL_PATH = Path("models/qwen2-marketing-lora")
RESULTS_DIR = Path("evaluation_results")

SYSTEM_PROMPT = """You are a professional marketing assistant specializing in Eastern and Pakistani fashion.
Generate creative, culturally relevant marketing content for clothing brands."""

# ============== TEST CASES ==============

# Different content types to evaluate
CONTENT_TYPE_TESTS = {
    "instagram_caption": {
        "prompt": "Write an engaging Instagram caption for a premium lawn suit from our summer collection, perfect for office wear.",
        "expected_elements": ["hashtags", "emoji", "call-to-action", "summer", "lawn", "office"],
        "max_tokens": 150,
    },
    "facebook_post": {
        "prompt": "Create a Facebook post announcing our new winter khaddar collection launch with a special discount offer.",
        "expected_elements": ["discount", "winter", "khaddar", "launch", "collection"],
        "max_tokens": 200,
    },
    "product_description": {
        "prompt": "Write a detailed product description for an embroidered cotton kurta from our summer men's collection.",
        "expected_elements": ["fabric", "embroidery", "cotton", "summer", "kurta", "men"],
        "max_tokens": 250,
    },
    "ad_copy": {
        "prompt": "Write compelling ad copy for a luxury pashmina shawl for our winter women's collection.",
        "expected_elements": ["luxury", "pashmina", "winter", "women", "warmth"],
        "max_tokens": 150,
    },
    "billboard_headline": {
        "prompt": "Create a short, impactful billboard headline for our summer lawn collection.",
        "expected_elements": ["summer", "lawn"],
        "max_tokens": 50,
    },
    "reel_idea": {
        "prompt": "Generate a creative Instagram Reel idea showcasing our winter shawl collection.",
        "expected_elements": ["reel", "video", "winter", "shawl", "visual"],
        "max_tokens": 200,
    },
    "campaign_idea": {
        "prompt": "Propose a marketing campaign concept for launching our new summer collection targeting young professionals.",
        "expected_elements": ["campaign", "summer", "professional", "strategy", "target"],
        "max_tokens": 300,
    },
    "email_subject": {
        "prompt": "Write 3 compelling email subject lines for our winter sale announcement.",
        "expected_elements": ["winter", "sale"],
        "max_tokens": 100,
    },
    "whatsapp_broadcast": {
        "prompt": "Write a WhatsApp broadcast message promoting our new arrivals in the winter collection.",
        "expected_elements": ["new arrivals", "winter", "emoji"],
        "max_tokens": 150,
    },
    "slogan": {
        "prompt": "Create 3 brand slogans for an Eastern fashion brand focusing on modern traditional wear.",
        "expected_elements": ["traditional", "modern", "fashion"],
        "max_tokens": 100,
    },
}

# Creativity tests with different temperatures
CREATIVITY_TESTS = {
    "low_creativity": {
        "temperature": 0.3,
        "top_p": 0.8,
        "description": "Conservative, predictable output"
    },
    "medium_creativity": {
        "temperature": 0.7,
        "top_p": 0.9,
        "description": "Balanced creativity and coherence"
    },
    "high_creativity": {
        "temperature": 1.0,
        "top_p": 0.95,
        "description": "More creative, diverse output"
    },
}

# Seasonal accuracy tests
SEASONAL_TESTS = {
    "summer_men": {
        "prompt": "Write an Instagram caption for a cotton shalwar kameez from our summer men's collection for daily wear.",
        "must_contain": ["summer", "cotton"],
        "must_not_contain": ["winter", "wool", "khaddar", "shawl"],
    },
    "summer_women": {
        "prompt": "Create a product description for a floral lawn suit from our summer women's collection.",
        "must_contain": ["summer", "lawn", "floral"],
        "must_not_contain": ["winter", "wool", "khaddar", "shawl"],
    },
    "winter_men": {
        "prompt": "Write ad copy for a wool waistcoat from our winter men's collection.",
        "must_contain": ["winter", "wool", "waistcoat"],
        "must_not_contain": ["summer", "lawn", "cotton kurta"],
    },
    "winter_women": {
        "prompt": "Create a social media post for an embroidered khaddar suit from our winter women's collection.",
        "must_contain": ["winter", "khaddar"],
        "must_not_contain": ["summer", "lawn"],
    },
}

# ============== MODEL LOADING ==============

def load_model():
    """Load the fine-tuned model with LoRA weights"""
    print("="*60)
    print("Loading Fine-tuned Model")
    print("="*60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    
    # Load tokenizer
    print(f"\nLoading tokenizer: {BASE_MODEL}")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    print(f"Loading base model: {BASE_MODEL}")
    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )
    
    # Load LoRA weights
    if LORA_MODEL_PATH.exists():
        print(f"Loading LoRA weights from: {LORA_MODEL_PATH}")
        model = PeftModel.from_pretrained(base_model, str(LORA_MODEL_PATH))
        print("✓ LoRA weights loaded successfully!")
    else:
        print(f"⚠️  LoRA weights not found at {LORA_MODEL_PATH}")
        print("Using base model without fine-tuning for comparison...")
        model = base_model
    
    model.eval()
    return model, tokenizer, device

# ============== GENERATION ==============

def generate_response(model, tokenizer, prompt: str, temperature: float = 0.7, 
                     top_p: float = 0.9, max_tokens: int = 150) -> str:
    """Generate response from the model"""
    
    full_prompt = f"""<|im_start|>system
{SYSTEM_PROMPT}<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
    
    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=top_p,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.0,
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=False)
    
    # Extract assistant's response
    if "<|im_start|>assistant" in response:
        response = response.split("<|im_start|>assistant")[-1]
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0]
    
    return response.strip()

# ============== EVALUATION FUNCTIONS ==============

def evaluate_content_types(model, tokenizer, results: dict):
    """Evaluate model on different content types"""
    print("\n" + "="*60)
    print("EVALUATION 1: Content Type Performance")
    print("="*60)
    
    results["content_types"] = {}
    
    for content_type, test in CONTENT_TYPE_TESTS.items():
        print(f"\n📝 Testing: {content_type}")
        print(f"   Prompt: {test['prompt'][:80]}...")
        
        response = generate_response(
            model, tokenizer, 
            test["prompt"],
            max_tokens=test["max_tokens"]
        )
        
        # Check for expected elements
        response_lower = response.lower()
        found_elements = [elem for elem in test["expected_elements"] 
                        if elem.lower() in response_lower]
        element_score = len(found_elements) / len(test["expected_elements"]) * 100
        
        results["content_types"][content_type] = {
            "prompt": test["prompt"],
            "response": response,
            "expected_elements": test["expected_elements"],
            "found_elements": found_elements,
            "element_score": element_score,
            "response_length": len(response.split()),
        }
        
        print(f"   ✓ Generated ({len(response.split())} words)")
        print(f"   Element Score: {element_score:.1f}% ({len(found_elements)}/{len(test['expected_elements'])})")
        print(f"   Response preview: {response[:100]}...")


def evaluate_creativity(model, tokenizer, results: dict):
    """Evaluate model at different creativity levels"""
    print("\n" + "="*60)
    print("EVALUATION 2: Creativity Levels")
    print("="*60)
    
    test_prompt = "Write a creative Instagram caption for a luxury embroidered shawl from our winter collection."
    
    results["creativity"] = {}
    
    for level, config in CREATIVITY_TESTS.items():
        print(f"\n🎨 Testing: {level} (temp={config['temperature']}, top_p={config['top_p']})")
        print(f"   {config['description']}")
        
        # Generate 3 samples to check diversity
        samples = []
        for i in range(3):
            response = generate_response(
                model, tokenizer,
                test_prompt,
                temperature=config["temperature"],
                top_p=config["top_p"],
                max_tokens=150
            )
            samples.append(response)
        
        # Calculate diversity (unique words ratio across samples)
        all_words = " ".join(samples).lower().split()
        unique_words = set(all_words)
        diversity_score = len(unique_words) / len(all_words) * 100 if all_words else 0
        
        results["creativity"][level] = {
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "samples": samples,
            "diversity_score": diversity_score,
        }
        
        print(f"   Diversity Score: {diversity_score:.1f}%")
        print(f"   Sample 1: {samples[0][:100]}...")


def evaluate_seasonal_accuracy(model, tokenizer, results: dict):
    """Evaluate model's accuracy in following seasonal context"""
    print("\n" + "="*60)
    print("EVALUATION 3: Seasonal Accuracy")
    print("="*60)
    
    results["seasonal_accuracy"] = {}
    total_score = 0
    total_tests = 0
    
    for test_name, test in SEASONAL_TESTS.items():
        print(f"\n🌡️  Testing: {test_name}")
        
        response = generate_response(model, tokenizer, test["prompt"], max_tokens=200)
        response_lower = response.lower()
        
        # Check must_contain
        contains_required = [elem for elem in test["must_contain"] 
                           if elem.lower() in response_lower]
        contains_score = len(contains_required) / len(test["must_contain"]) * 100
        
        # Check must_not_contain (penalty)
        contains_forbidden = [elem for elem in test["must_not_contain"] 
                            if elem.lower() in response_lower]
        penalty = len(contains_forbidden) * 20  # 20% penalty per forbidden element
        
        final_score = max(0, contains_score - penalty)
        total_score += final_score
        total_tests += 1
        
        results["seasonal_accuracy"][test_name] = {
            "prompt": test["prompt"],
            "response": response,
            "must_contain": test["must_contain"],
            "found_required": contains_required,
            "must_not_contain": test["must_not_contain"],
            "found_forbidden": contains_forbidden,
            "accuracy_score": final_score,
        }
        
        status = "✅" if final_score >= 70 else "⚠️" if final_score >= 40 else "❌"
        print(f"   {status} Score: {final_score:.1f}%")
        print(f"   Required found: {contains_required}")
        if contains_forbidden:
            print(f"   ⚠️  Forbidden found: {contains_forbidden}")
        print(f"   Response: {response[:150]}...")
    
    avg_seasonal_score = total_score / total_tests if total_tests > 0 else 0
    results["seasonal_accuracy"]["average_score"] = avg_seasonal_score
    print(f"\n📊 Average Seasonal Accuracy: {avg_seasonal_score:.1f}%")


def evaluate_prompt_accuracy(model, tokenizer, results: dict):
    """Evaluate how accurately model follows specific instructions"""
    print("\n" + "="*60)
    print("EVALUATION 4: Prompt Following Accuracy")
    print("="*60)
    
    accuracy_tests = [
        {
            "name": "Word count instruction",
            "prompt": "Write a very short (under 20 words) Instagram caption for a lawn suit.",
            "check": lambda r: len(r.split()) <= 30,  # Allow some flexibility
            "description": "Should be concise, under ~30 words",
        },
        {
            "name": "Format instruction (list)",
            "prompt": "List exactly 5 unique selling points for our winter khaddar collection.",
            "check": lambda r: any(char in r for char in ["1.", "•", "-", "1)"]) or r.count("\n") >= 3,
            "description": "Should contain list formatting",
        },
        {
            "name": "Emoji requirement",
            "prompt": "Write a fun Instagram caption with emojis for a summer cotton kurta.",
            "check": lambda r: any(ord(char) > 127 for char in r),  # Check for non-ASCII (emojis)
            "description": "Should contain emojis",
        },
        {
            "name": "Hashtag requirement",
            "prompt": "Write an Instagram caption with relevant hashtags for a premium lawn suit.",
            "check": lambda r: "#" in r,
            "description": "Should contain hashtags",
        },
        {
            "name": "Question format",
            "prompt": "Write an engagement post asking followers about their favorite winter outfit styles.",
            "check": lambda r: "?" in r,
            "description": "Should contain a question",
        },
        {
            "name": "Call-to-action",
            "prompt": "Write ad copy for our winter collection with a clear call-to-action to shop now.",
            "check": lambda r: any(cta in r.lower() for cta in ["shop", "buy", "order", "click", "visit", "discover", "explore", "get yours"]),
            "description": "Should contain call-to-action",
        },
    ]
    
    results["prompt_accuracy"] = {}
    passed = 0
    
    for test in accuracy_tests:
        print(f"\n🎯 Testing: {test['name']}")
        
        response = generate_response(model, tokenizer, test["prompt"], max_tokens=150)
        test_passed = test["check"](response)
        
        results["prompt_accuracy"][test["name"]] = {
            "prompt": test["prompt"],
            "response": response,
            "passed": test_passed,
            "description": test["description"],
        }
        
        if test_passed:
            passed += 1
            print(f"   ✅ PASSED - {test['description']}")
        else:
            print(f"   ❌ FAILED - {test['description']}")
        print(f"   Response: {response[:120]}...")
    
    accuracy_rate = passed / len(accuracy_tests) * 100
    results["prompt_accuracy"]["overall_rate"] = accuracy_rate
    print(f"\n📊 Prompt Following Accuracy: {accuracy_rate:.1f}% ({passed}/{len(accuracy_tests)})")


def generate_summary(results: dict):
    """Generate evaluation summary"""
    print("\n" + "="*60)
    print("📊 EVALUATION SUMMARY")
    print("="*60)
    
    # Content type average
    if results.get("content_types"):
        ct_scores = [v["element_score"] for v in results["content_types"].values() 
                    if isinstance(v, dict) and "element_score" in v]
        ct_avg = sum(ct_scores) / len(ct_scores) if ct_scores else 0
        print(f"\n1. Content Type Coverage: {ct_avg:.1f}%")
    
    # Creativity diversity
    if results.get("creativity"):
        for level, data in results["creativity"].items():
            if isinstance(data, dict):
                print(f"   - {level}: {data.get('diversity_score', 0):.1f}% diversity")
    
    # Seasonal accuracy
    if results.get("seasonal_accuracy"):
        seasonal_avg = results["seasonal_accuracy"].get("average_score", 0)
        print(f"\n2. Seasonal Accuracy: {seasonal_avg:.1f}%")
    
    # Prompt accuracy
    if results.get("prompt_accuracy"):
        prompt_rate = results["prompt_accuracy"].get("overall_rate", 0)
        print(f"\n3. Prompt Following: {prompt_rate:.1f}%")
    
    # Overall assessment
    overall_scores = []
    if results.get("content_types"):
        overall_scores.append(ct_avg)
    if results.get("seasonal_accuracy"):
        overall_scores.append(seasonal_avg)
    if results.get("prompt_accuracy"):
        overall_scores.append(prompt_rate)
    
    if overall_scores:
        overall = sum(overall_scores) / len(overall_scores)
        print(f"\n{'='*40}")
        print(f"OVERALL SCORE: {overall:.1f}%")
        if overall >= 80:
            print("✅ Excellent - Model is ready for production!")
        elif overall >= 60:
            print("✓ Good - Model performs well, minor improvements possible")
        elif overall >= 40:
            print("⚠️ Fair - Model needs more training or data")
        else:
            print("❌ Poor - Consider retraining with better data")
    
    return results


def save_results(results: dict):
    """Save evaluation results to file"""
    RESULTS_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"evaluation_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {output_file}")
    return output_file


def main():
    print("="*60)
    print("Qwen2 Marketing Model Evaluation")
    print("="*60)
    
    # Check if model exists
    if not LORA_MODEL_PATH.exists():
        print(f"\n⚠️  Fine-tuned model not found at: {LORA_MODEL_PATH}")
        print("Please run finetune_qwen2.py first!")
        print("\nWould you like to evaluate the base model instead? (y/n)")
        response = input().strip().lower()
        if response != 'y':
            return
    
    # Load model
    model, tokenizer, device = load_model()
    
    # Results dictionary
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": str(LORA_MODEL_PATH) if LORA_MODEL_PATH.exists() else BASE_MODEL,
        "device": device,
    }
    
    # Run evaluations
    try:
        evaluate_content_types(model, tokenizer, results)
        evaluate_creativity(model, tokenizer, results)
        evaluate_seasonal_accuracy(model, tokenizer, results)
        evaluate_prompt_accuracy(model, tokenizer, results)
        
        # Generate summary
        results = generate_summary(results)
        
        # Save results
        save_results(results)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation interrupted!")
        save_results(results)
    
    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    main()
