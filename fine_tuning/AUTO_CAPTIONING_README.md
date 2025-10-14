# 🏷️ Auto-Captioning for Fashion Dataset

## 📖 Overview

I've created an **automatic captioning system** that uses AI to generate text descriptions for all your 10,000 fashion images. This is required for training Stable Diffusion models.

---

## 🎯 What It Does

### **Input:** Your images
```
data/Winter/Men/Winter_Men_0001.jpg
```

### **Output:** AI-generated captions
```
data/Winter/Men/Winter_Men_0001.txt
"pakistani winter men's formal wear, waistcoat, a man wearing a black waistcoat with gold buttons and traditional embroidery"
```

---

## 🛠️ How It Works

### **Technology:**
- **BLIP** (Bootstrapping Language-Image Pre-training) by Salesforce
- State-of-the-art vision-language model
- Pre-trained on millions of images

### **Process:**
1. 📸 Loads your image
2. 🧠 AI analyzes the visual content
3. 📝 Generates natural language description
4. 🏷️ Adds Pakistani fashion context
5. 💾 Saves caption as `.txt` file

---

## 🚀 Quick Start Guide

### **Step 1: Install Dependencies**

```bash
pip install transformers torch accelerate
```

**Or install everything:**
```bash
pip install -r requirements.txt
```

**Estimated download:** ~500MB for the model (one-time)

---

### **Step 2: Test on Single Image**

Verify the system works:

```bash
python test_caption_single.py
```

**What you'll see:**
```
Looking for sample image...
[OK] Found sample: data/Winter/Men/Winter_Men_0001.jpg
[OK] Category: Winter_Men

Loading BLIP model...
Using device: cuda
[OK] Model loaded successfully!

Base caption: a man wearing a black waistcoat with gold buttons
Enhanced caption: pakistani winter men's formal wear, waistcoat, a man wearing a black waistcoat with gold buttons

[SUCCESS] Caption generation test complete!
```

---

### **Step 3: Test on Small Batch**

Process 10 images per category (40 total):

```bash
python caption_generator.py --test 10
```

**Time:** ~1-2 minutes with GPU, ~5-10 minutes with CPU

---

### **Step 4: Process Full Dataset**

Caption all 10,000 images:

```bash
python caption_generator.py
```

**Time Estimates:**
| Hardware | Time |
|----------|------|
| GPU (RTX 3060+) | 20-30 minutes |
| GPU (Google Colab T4) | 15-20 minutes |
| CPU | 2-4 hours |

---

## 📊 Expected Results

### **Statistics:**

After running on full dataset, you'll have:

- ✅ **10,000 images** → **10,000 captions**
- ✅ Each image gets a unique, AI-generated description
- ✅ Captions include Pakistani fashion context
- ✅ Ready for model training

### **Caption Quality Examples:**

#### Winter Men:
```
"pakistani winter men's formal wear, waistcoat, a man wearing a navy blue waistcoat with silver buttons and traditional embroidery"
```

#### Winter Women:
```
"pakistani winter women's clothing, khaddar fabric, unstitched three piece suit with printed stripes and embroidered dupatta"
```

#### Summer Men:
```
"pakistani summer men's eastern wear, kurta, white cotton kurta with minimal embroidery on collar"
```

#### Summer Women:
```
"pakistani summer women's lawn fabric, unstitched, three piece lawn suit with floral print in pastel colors"
```

---

## 🎛️ Command Options

### All Available Flags:

```bash
python caption_generator.py [OPTIONS]
```

| Option | Description | Example |
|--------|-------------|---------|
| `--test N` | Process only N images per category | `--test 10` |
| `--overwrite` | Regenerate existing captions | `--overwrite` |
| `--data-root PATH` | Custom data directory | `--data-root ./my_data` |
| `--model NAME` | Use different model size | `--model Salesforce/blip-image-captioning-large` |

### **Examples:**

```bash
# Test mode
python caption_generator.py --test 5

# Full dataset with large model
python caption_generator.py --model Salesforce/blip-image-captioning-large

# Overwrite existing captions
python caption_generator.py --overwrite

# Custom directory
python caption_generator.py --data-root /path/to/images
```

---

## 💻 System Requirements

### **Minimum:**
- Python 3.8+
- 4GB RAM
- 2GB disk space (for model)
- CPU (slow but works)

### **Recommended:**
- Python 3.10+
- 8GB RAM
- NVIDIA GPU with 4GB+ VRAM
- CUDA installed

### **Optimal:**
- Google Colab (Free GPU)
- Or RTX 3060/4060 or better

---

## ☁️ Google Colab Option (Recommended!)

If you don't have a GPU, use Google Colab for FREE:

### **1. Upload to Google Drive:**
- Upload `data/` folder
- Upload `caption_generator.py`

### **2. Create Colab Notebook:**

```python
# Mount Drive
from google.colab import drive
drive.mount('/content/drive')

# Navigate
%cd /content/drive/MyDrive/FYP

# Install
!pip install transformers accelerate -q

# Run
!python caption_generator.py
```

### **3. Download Results:**
- Your `data/` folder now has all `.txt` files
- Download to your local machine

**Time:** ~15-20 minutes for 10,000 images with Colab GPU!

---

## 🐛 Troubleshooting

### **"transformers not installed"**
```bash
pip install transformers torch accelerate
```

### **"CUDA out of memory"**
- Use base model (default)
- Process in batches: `--test 100`
- Close other applications

### **Very slow**
- You're on CPU - this is normal
- Use Google Colab with GPU
- Or use `--test` mode for batches

### **Model download fails**
- Check internet connection
- Model is 500MB, downloads once
- Cached in `~/.cache/huggingface/`

### **Captions are poor quality**
- Try large model: `--model Salesforce/blip-image-captioning-large`
- Or manually edit important captions
- Or use CLIP Interrogator instead

---

## 📁 File Structure After Captioning

```
E:\Projects\FYP\
├── data/
│   ├── Winter/
│   │   ├── Men/
│   │   │   ├── Winter_Men_0001.jpg
│   │   │   ├── Winter_Men_0001.txt  ← NEW!
│   │   │   ├── Winter_Men_0002.jpg
│   │   │   ├── Winter_Men_0002.txt  ← NEW!
│   │   │   └── ... (2500 images + 2500 captions)
│   │   └── Women/
│   │       └── ... (2500 images + 2500 captions)
│   └── Summer/
│       ├── Men/
│       │   └── ... (2500 images + 2500 captions)
│       └── Women/
│           └── ... (2500 images + 2500 captions)
│
├── caption_generator.py  ← Main script
├── test_caption_single.py  ← Test single image
├── CAPTIONING_GUIDE.md  ← Detailed guide
└── AUTO_CAPTIONING_README.md  ← This file
```

**Total:** 10,000 images + 10,000 captions = 20,000 files

---

## ✅ Verification

After captioning, verify results:

### **Check caption exists:**
```bash
# Windows
dir data\Winter\Men\*.txt

# Linux/Mac
ls data/Winter/Men/*.txt
```

### **Read a caption:**
```bash
# Windows
type data\Winter\Men\Winter_Men_0001.txt

# Linux/Mac
cat data/Winter/Men/Winter_Men_0001.txt
```

### **Count captions:**
```python
import os
from pathlib import Path

data_root = "data"
categories = ["Winter/Men", "Winter/Women", "Summer/Men", "Summer/Women"]

for cat in categories:
    path = os.path.join(data_root, cat)
    txt_files = list(Path(path).glob("*.txt"))
    print(f"{cat}: {len(txt_files)} captions")
```

**Expected output:**
```
Winter/Men: 2500 captions
Winter/Women: 2500 captions
Summer/Men: 2500 captions
Summer/Women: 2500 captions
```

---

## 🎯 What's Next?

After captioning is complete:

### **Immediate:**
1. ✅ Verify caption quality
2. ✅ Check a few samples manually
3. ✅ Fix any obvious errors (optional)

### **Next Steps:**
1. 📁 Organize dataset for training
2. 🛠️ Set up Kohya_ss or training tool
3. ⚙️ Configure training parameters
4. 🚀 Start fine-tuning!

---

## 💡 Tips

### **Improve Caption Quality:**

1. **Manual editing** for key images
   - Edit important/representative images
   - Add specific details (colors, patterns, styles)

2. **Use large model** for better descriptions
   ```bash
   python caption_generator.py --model Salesforce/blip-image-captioning-large
   ```

3. **Add trigger words** manually
   - Add "pakistani fashion" consistently
   - Add specific terms like "khaddar", "lawn", "waistcoat"

### **Speed Up Processing:**

1. Use GPU (Google Colab is free!)
2. Process in batches if memory limited
3. Base model is faster than large

### **Save Money:**

- Google Colab has free GPU tier
- Colab Pro is $10/month (more GPU time)
- Vastly faster than CPU processing

---

## 📚 Learn More

### **About BLIP:**
- Paper: https://arxiv.org/abs/2201.12086
- Model: https://huggingface.co/Salesforce/blip-image-captioning-base

### **Alternative Models:**
- BLIP-2 (more accurate)
- CLIP Interrogator (artistic)
- CogVLM (very detailed, needs 24GB VRAM)

### **Training Resources:**
- Kohya_ss GUI: https://github.com/bmaltais/kohya_ss
- EveryDream2: https://github.com/victorchall/EveryDream2trainer
- Stable Diffusion Training: https://huggingface.co/docs/diffusers/training/overview

---

## 🆘 Get Help

If you encounter issues:

1. Check CAPTIONING_GUIDE.md for detailed troubleshooting
2. Run test script first: `python test_caption_single.py`
3. Use `--test 10` mode to verify before full run
4. Check PyTorch installation: `python -c "import torch; print(torch.cuda.is_available())"`

---

**Created:** October 2025  
**Status:** Ready to use  
**Next:** Run `python test_caption_single.py` to get started!

