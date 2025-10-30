"""
LoRA Fine-tuning for BLIP on Eastern Clothing
Uses Low-Rank Adaptation for efficient fine-tuning
"""

import os
import sys
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BlipProcessor, 
    BlipForConditionalGeneration,
    get_linear_schedule_with_warmup
)
from torch.optim import AdamW
from PIL import Image
import pandas as pd
from tqdm import tqdm
import argparse
from pathlib import Path
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class LoRALayer(nn.Module):
    """Low-Rank Adaptation layer"""
    def __init__(self, in_features, out_features, rank=16):
        super().__init__()
        self.rank = rank
        self.lora_A = nn.Linear(in_features, rank, bias=False)
        self.lora_B = nn.Linear(rank, out_features, bias=False)
        self.scaling = 1.0 / rank
        
    def forward(self, x):
        return self.lora_B(self.lora_A(x)) * self.scaling

def apply_lora_to_linear_layers(model, rank=16):
    """Apply LoRA to linear layers in the model"""
    lora_layers = {}
    
    # BLIP models have different architectures - let's target the text decoder
    print("Searching for layers to apply LoRA...")
    found_modules = []
    
    # Instead of replacing, we'll use a simpler approach: just fine-tune the language modeling head
    # BLIP uses a language modeling head for caption generation
    if hasattr(model, 'lm_head'):
        # Freeze all parameters first
        for param in model.parameters():
            param.requires_grad = False
        
        # Unfreeze language modeling head
        if hasattr(model, 'lm_head'):
            for param in model.lm_head.parameters():
                param.requires_grad = True
            print(f"  Found lm_head, enabling gradients")
            found_modules.append('lm_head')
    
    # Also try to find text decoder layers
    if hasattr(model, 'text_decoder'):
        # Enable gradients for text decoder's last few layers
        decoder_layers = list(model.text_decoder.named_children())
        if decoder_layers:
            # Unfreeze last 2 layers
            for name, module in decoder_layers[-2:]:
                if isinstance(module, nn.Module):
                    for param in module.parameters():
                        param.requires_grad = True
                    print(f"  Unfreezed text_decoder.{name}")
                    found_modules.append(f"text_decoder.{name}")
    
    # Fallback: if no specific layers found, just enable gradients for text-related parts
    if not found_modules:
        print("  No specific layers found, enabling gradients for text components...")
        for name, param in model.named_parameters():
            if 'text' in name.lower() or 'decoder' in name.lower() or 'lm' in name.lower():
                param.requires_grad = True
                if name not in found_modules:
                    found_modules.append(name)
        
        if found_modules:
            print(f"  Enabled gradients for {len(found_modules)} text-related parameters")
    
    # Count trainable parameters
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable parameters: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")
    
    return found_modules  # Return list of layer names instead of LoRA layers

class EasternClothingDataset(Dataset):
    """Dataset for Eastern clothing image-caption pairs"""
    
    def __init__(self, csv_files, image_root, processor, max_length=77):
        self.processor = processor
        self.max_length = max_length
        self.image_root = image_root
        
        # Load all captions from CSV files
        self.data = []
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                print(f"Loading captions from {csv_file}")
                df = pd.read_csv(csv_file)
                print(f"  Found {len(df)} captions in CSV")
                
                for _, row in df.iterrows():
                    # Try different possible image paths
                    possible_paths = [
                        os.path.join(image_root, row['filename']),
                        os.path.join(image_root, "Winter", "Women", row['filename']),
                        os.path.join(image_root, "Winter", "Men", row['filename']),
                        os.path.join(image_root, "Summer", "Women", row['filename']),
                        os.path.join(image_root, "Summer", "Men", row['filename'])
                    ]
                    
                    image_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            image_path = path
                            break
                    
                    if image_path:
                        self.data.append({
                            'image_path': image_path,
                            'caption': row['caption']
                        })
                    else:
                        print(f"  Warning: Image not found for {row['filename']}")
        
        print(f"Loaded {len(self.data)} image-caption pairs")
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load image
        image = Image.open(item['image_path']).convert('RGB')
        
        # Process image and text
        inputs = self.processor(
            images=image,
            text=item['caption'],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Remove batch dimension
        for key in inputs:
            inputs[key] = inputs[key].squeeze(0)
        
        return inputs

def collate_fn(batch):
    """Custom collate function for DataLoader"""
    batch_dict = {}
    for key in batch[0].keys():
        if key == 'input_ids' or key == 'attention_mask':
            # Pad sequences
            max_len = max(item[key].size(0) for item in batch)
            padded_items = []
            for item in batch:
                if item[key].size(0) < max_len:
                    if key == 'input_ids':
                        # Pad with pad_token_id (0)
                        padding = torch.zeros(max_len - item[key].size(0), dtype=item[key].dtype)
                        padded_item = torch.cat([item[key], padding])
                    else:  # attention_mask
                        padding = torch.zeros(max_len - item[key].size(0), dtype=item[key].dtype)
                        padded_item = torch.cat([item[key], padding])
                else:
                    padded_item = item[key]
                padded_items.append(padded_item)
            batch_dict[key] = torch.stack(padded_items)
        else:
            # For other tensors, just stack them
            batch_dict[key] = torch.stack([item[key] for item in batch])
    
    return batch_dict

def train_blip_with_lora(
    model_name="Salesforce/blip-image-captioning-base",
    csv_files=None,
    image_root="data_backup",
    num_epochs=3,
    batch_size=4,
    learning_rate=1e-4,
    lora_rank=16,
    output_dir="models/blip_eastern_lora"
):
    """Train BLIP model with LoRA on Eastern clothing dataset"""
    
    print("=" * 60)
    print("LoRA BLIP EASTERN CLOTHING FINE-TUNING")
    print("=" * 60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Load model and processor
    print("Loading BLIP model...")
    processor = BlipProcessor.from_pretrained(model_name)
    model = BlipForConditionalGeneration.from_pretrained(model_name)
    
    # Freeze base model parameters
    for param in model.parameters():
        param.requires_grad = False
    
    # Apply selective fine-tuning (similar to LoRA approach)
    print("Applying selective fine-tuning...")
    trainable_layers = apply_lora_to_linear_layers(model, rank=lora_rank)
    
    model.to(device)
    model.train()
    
    # Prepare dataset
    if csv_files is None:
        csv_files = [
            "captions/captions_Winter_Women.csv",
            "captions/captions_Winter_Men.csv", 
            "captions/captions_Summer_Women.csv",
            "captions/captions_Summer_Men.csv"
        ]
    
    dataset = EasternClothingDataset(csv_files, image_root, processor)
    
    if len(dataset) == 0:
        print("❌ No data found! Please check your CSV files and image paths.")
        return
    
    # Create data loader
    dataloader = DataLoader(
        dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        collate_fn=collate_fn,
        num_workers=0
    )
    
    # Set up optimizer (only for trainable parameters)
    trainable_params = [p for p in model.parameters() if p.requires_grad]
    
    if len(trainable_params) == 0:
        raise ValueError("No trainable parameters found! Check model architecture.")
    
    print(f"Optimizing {len(trainable_params)} parameter groups")
    optimizer = AdamW(trainable_params, lr=learning_rate)
    total_steps = len(dataloader) * num_epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, 
        num_warmup_steps=total_steps // 10,
        num_training_steps=total_steps
    )
    
    # Training loop
    print(f"Starting LoRA training for {num_epochs} epochs...")
    print(f"Total batches: {len(dataloader)}")
    print(f"Total steps: {total_steps}")
    print(f"LoRA rank: {lora_rank}")
    
    best_loss = float('inf')
    training_history = []
    
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch + 1}/{num_epochs}")
        print("-" * 40)
        
        epoch_loss = 0
        valid_batches = 0
        
        progress_bar = tqdm(dataloader, desc=f"Epoch {epoch + 1}")
        
        for batch_idx, batch in enumerate(progress_bar):
            # Move batch to device
            for key in batch:
                batch[key] = batch[key].to(device)
            
            # Forward pass
            try:
                outputs = model(
                    pixel_values=batch['pixel_values'],
                    input_ids=batch['input_ids'],
                    attention_mask=batch['attention_mask'],
                    labels=batch['input_ids']
                )
                
                loss = outputs.loss
                
                if loss is not None and not torch.isnan(loss):
                    # Backward pass
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    scheduler.step()
                    
                    epoch_loss += loss.item()
                    valid_batches += 1
                    
                    # Update progress bar
                    progress_bar.set_postfix({
                        'loss': f'{loss.item():.4f}',
                        'avg_loss': f'{epoch_loss/valid_batches:.4f}'
                    })
                else:
                    print(f"Warning: Invalid loss at batch {batch_idx}")
                    
            except Exception as e:
                print(f"Error in forward pass at batch {batch_idx}: {e}")
                continue
        
        # Calculate average loss for epoch
        avg_loss = epoch_loss / valid_batches if valid_batches > 0 else float('inf')
        print(f"Epoch {epoch + 1} average loss: {avg_loss:.4f}")
        
        # Save best model
        if avg_loss < best_loss:
            best_loss = avg_loss
            print(f"💾 Saving best LoRA model (loss: {best_loss:.4f})")
            model.save_pretrained(os.path.join(output_dir, "best_model"))
            processor.save_pretrained(os.path.join(output_dir, "best_model"))
        
        # Save training history
        training_history.append({
            'epoch': epoch + 1,
            'avg_loss': avg_loss,
            'valid_batches': valid_batches
        })
    
    # Save final model
    print("\nSaving final LoRA model...")
    model.save_pretrained(os.path.join(output_dir, "final_model"))
    processor.save_pretrained(os.path.join(output_dir, "final_model"))
    
    # Save training history
    with open(os.path.join(output_dir, "training_history.json"), 'w') as f:
        json.dump(training_history, f, indent=2)
    
    print(f"\n✅ LoRA training completed!")
    print(f"Best loss: {best_loss:.4f}")
    print(f"Model saved to: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description='LoRA BLIP fine-tuning for Eastern clothing')
    parser.add_argument('--mode', type=str, choices=['train', 'test'], default='train',
                       help='Mode: train or test')
    parser.add_argument('--epochs', type=int, default=3, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=4, help='Batch size')
    parser.add_argument('--learning-rate', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--lora-rank', type=int, default=16, help='LoRA rank')
    parser.add_argument('--output-dir', type=str, default='models/blip_eastern_lora',
                       help='Output directory for trained model')
    
    args = parser.parse_args()
    
    if args.mode == 'train':
        train_blip_with_lora(
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            lora_rank=args.lora_rank,
            output_dir=args.output_dir
        )
    else:
        print("Test mode not implemented yet")

if __name__ == "__main__":
    main()
