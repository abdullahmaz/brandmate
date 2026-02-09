"""
Fine-tune Qwen2.5-0.5B-Instruct on Marketing Content Dataset
Uses LoRA for efficient fine-tuning with limited GPU memory
"""

import os
import json
import torch
from pathlib import Path
from datasets import Dataset, load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq,
    BitsAndBytesConfig
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)

# ============== CONFIGURATION ==============

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
DATASET_DIR = Path("training_data_v2")  # Directory with multiple JSONL files
OUTPUT_DIR = Path("models/qwen2-marketing-lora")

# Training hyperparameters
BATCH_SIZE = 2  # Smaller batch for better generalization
GRADIENT_ACCUMULATION_STEPS = 8  # Effective batch = 16
LEARNING_RATE = 5e-5  # Much lower LR to prevent overfitting
NUM_EPOCHS = 2  # Fewer epochs for small dataset
MAX_LENGTH = 512
WARMUP_RATIO = 0.1

# LoRA configuration - more conservative
LORA_R = 8  # Lower rank to prevent overfitting
LORA_ALPHA = 16
LORA_DROPOUT = 0.1  # Higher dropout for regularization

# ============== HELPER FUNCTIONS ==============

def load_jsonl_dataset(dataset_dir: Path) -> Dataset:
    """Load all JSONL files from a directory into a single dataset"""
    data = []
    jsonl_files = list(dataset_dir.glob("*.jsonl"))
    
    if not jsonl_files:
        raise FileNotFoundError(f"No JSONL files found in {dataset_dir}")
    
    print(f"Found {len(jsonl_files)} JSONL files:")
    for file_path in jsonl_files:
        file_count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
                    file_count += 1
        print(f"  - {file_path.name}: {file_count} examples")
    
    print(f"Total examples loaded: {len(data)}")
    return Dataset.from_list(data)


def format_prompt(example: dict) -> str:
    """Format example into Qwen2 chat format"""
    system_prompt = """You are a professional marketing assistant specializing in Eastern and Pakistani fashion.
Generate creative, culturally relevant marketing content for clothing brands."""
    
    instruction = example.get("instruction", "")
    input_text = example.get("input", "")
    output = example.get("output", "")
    
    if input_text:
        user_content = f"{instruction}\n\n{input_text}"
    else:
        user_content = instruction
    
    # Qwen2 chat format
    prompt = f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
{user_content}<|im_end|>
<|im_start|>assistant
{output}<|im_end|>"""
    
    return prompt


def tokenize_function(examples, tokenizer, max_length):
    """Tokenize examples"""
    prompts = [format_prompt({"instruction": inst, "input": inp, "output": out}) 
               for inst, inp, out in zip(examples["instruction"], 
                                          examples.get("input", [""] * len(examples["instruction"])),
                                          examples["output"])]
    
    tokenized = tokenizer(
        prompts,
        truncation=True,
        max_length=max_length,
        padding="max_length",
        return_tensors=None
    )
    
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized


def main():
    print("="*60)
    print("Qwen2.5-0.5B Fine-tuning for Marketing Content")
    print("="*60)
    
    # Check for dataset directory
    if not DATASET_DIR.exists():
        print(f"\n❌ Dataset directory not found: {DATASET_DIR}")
        print("Please run generate_training_data_v2.py first!")
        return
    
    jsonl_files = list(DATASET_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print(f"\n❌ No JSONL files found in {DATASET_DIR}")
        return
    
    # Check GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDevice: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Load tokenizer
    print(f"\nLoading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # Load dataset from all JSONL files
    print(f"\nLoading dataset from: {DATASET_DIR}")
    dataset = load_jsonl_dataset(DATASET_DIR)
    print(f"\nTotal dataset size: {len(dataset)} examples")
    
    # Split dataset
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    print(f"Train: {len(dataset['train'])}, Eval: {len(dataset['test'])}")
    
    # Tokenize dataset
    print("\nTokenizing dataset...")
    tokenized_train = dataset["train"].map(
        lambda x: tokenize_function(x, tokenizer, MAX_LENGTH),
        batched=True,
        remove_columns=dataset["train"].column_names
    )
    tokenized_eval = dataset["test"].map(
        lambda x: tokenize_function(x, tokenizer, MAX_LENGTH),
        batched=True,
        remove_columns=dataset["test"].column_names
    )
    
    # Configure quantization for memory efficiency
    if device == "cuda":
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )
    else:
        bnb_config = None
    
    # Load model
    print(f"\nLoading model: {MODEL_NAME}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto" if device == "cuda" else None,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        trust_remote_code=True
    )
    
    if device == "cuda":
        model = prepare_model_for_kbit_training(model)
    
    # Configure LoRA
    print("\nConfiguring LoRA...")
    lora_config = LoraConfig(
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", 
                       "gate_proj", "up_proj", "down_proj"]
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Training arguments - more conservative to prevent overfitting
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=NUM_EPOCHS,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        learning_rate=LEARNING_RATE,
        weight_decay=0.05,  # Higher weight decay for regularization
        warmup_ratio=WARMUP_RATIO,
        lr_scheduler_type="cosine",
        logging_steps=5,  # Log more frequently
        eval_strategy="steps",
        eval_steps=25,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        fp16=device == "cuda",
        optim="adamw_torch",
        gradient_checkpointing=True,
        max_grad_norm=0.3,  # Gradient clipping for stability
    )
    
    # Data collator
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True
    )
    
    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train,
        eval_dataset=tokenized_eval,
        data_collator=data_collator,
    )
    
    # Train
    print("\n" + "="*60)
    print("Starting Training...")
    print("="*60)
    
    trainer.train()
    
    # Save model
    print(f"\nSaving model to {OUTPUT_DIR}...")
    trainer.save_model()
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print("\n✓ Fine-tuning complete!")
    print(f"Model saved to: {OUTPUT_DIR}")
    
    # Test the model
    print("\n" + "="*60)
    print("Testing fine-tuned model...")
    print("="*60)
    
    # Set model to eval mode and disable gradient checkpointing for inference
    model.eval()
    model.config.use_cache = True
    if hasattr(model, 'gradient_checkpointing_disable'):
        model.gradient_checkpointing_disable()
    
    test_prompt = """<|im_start|>system
You are a professional marketing assistant specializing in Eastern and Pakistani fashion.
Generate creative, culturally relevant marketing content for clothing brands.<|im_end|>
<|im_start|>user
Write an engaging Instagram caption for a luxury embroidered khaddar shawl from our winter collection.<|im_end|>
<|im_start|>assistant
"""

    with torch.no_grad():
        inputs = tokenizer(test_prompt, return_tensors="pt").to(model.device)
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.0,
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=False)
    print("\nTest prompt: Write an Instagram caption for a luxury embroidered khaddar shawl from our winter collection")
    print("\nGenerated response:")
    print("-" * 40)
    # Extract just the assistant's response
    if "<|im_start|>assistant" in response:
        response = response.split("<|im_start|>assistant")[-1]
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0]
    print(response.strip())
    
    print("\n" + "="*60)
    print("Fine-tuning complete! Run evaluate_model.py for detailed evaluation.")
    print("="*60)
if __name__ == "__main__":
    main()
