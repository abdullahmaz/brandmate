# 🔑 Multi-Key Gemini Captioning Guide

## ✨ Features

This improved captioning system has:

✅ **Multiple API Key Support** - Rotates through keys when quota is exceeded
✅ **Automatic Retry** - Retries failed images with exponential backoff  
✅ **Resume Capability** - Can resume from interruption
✅ **Progress Tracking** - Saves progress every 10 images
✅ **No Images Skipped** - Ensures all images are captioned
✅ **Rate Limiting** - Configurable wait time between requests

---

## 🚀 Quick Start

### **1. Get Multiple API Keys** (Optional but Recommended)

If you want to use multiple free-tier keys:

1. Go to: https://aistudio.google.com/apikey
2. Create 2-3 Google accounts
3. Get API key from each account
4. **Note:** This is within Google's terms for personal use

**OR** just enable billing on one key (recommended).

---

### **2. Basic Usage**

#### **Single API Key:**
```bash
py -3 gemini_caption_multi_key.py ^
  --api-keys AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo ^
  --category Summer_Men
```

#### **Multiple API Keys (Recommended):**
```bash
py -3 gemini_caption_multi_key.py ^
  --api-keys KEY1 KEY2 KEY3 ^
  --category Summer_Men
```

The script will automatically rotate to the next key when one hits quota limits!

---

## 📋 Command Options

### **Required:**
- `--api-keys` - One or more API keys (space-separated)
- `--category` - Which category to process

### **Optional:**
- `--test N` - Process only N images (for testing)
- `--wait-time 0.5` - Wait time between requests (default: 0.5s)
- `--overwrite` - Regenerate existing captions
- `--no-resume` - Start from scratch (don't resume)
- `--data-root` - Custom data directory

---

## 💡 Examples

### **Test with 10 images:**
```bash
py -3 gemini_caption_multi_key.py ^
  --api-keys YOUR_KEY ^
  --category Summer_Men ^
  --test 10
```

### **Process full category with 3 API keys:**
```bash
py -3 gemini_caption_multi_key.py ^
  --api-keys KEY1 KEY2 KEY3 ^
  --category Summer_Men ^
  --wait-time 0.3
```

### **Resume after interruption:**
```bash
# Just run the same command again - it will resume automatically!
py -3 gemini_caption_multi_key.py ^
  --api-keys YOUR_KEY ^
  --category Summer_Men
```

### **Process all categories:**
```bash
py -3 gemini_caption_multi_key.py ^
  --api-keys KEY1 KEY2 KEY3 ^
  --category all
```

---

## 🔄 How Key Rotation Works

### **With Free Tier (50 requests/day per key):**

| # Keys | Daily Capacity | Time for 2500 images |
|--------|----------------|----------------------|
| 1 key  | 50 images/day  | 50 days |
| 2 keys | 100 images/day | 25 days |
| 3 keys | 150 images/day | 17 days |
| 5 keys | 250 images/day | 10 days |

### **With Paid Tier (1500 requests/day per key):**

| # Keys | Daily Capacity | Time for 10K images |
|--------|----------------|---------------------|
| 1 key  | 1500/day      | 7 days |
| 2 keys | 3000/day      | 3.5 days |

**Best:** Enable billing on 1 key = 10K images in ~8 hours for ~$1.50

---

## 📊 Progress Tracking

The script saves progress files in each category folder:
```
data/Summer/Men/.caption_progress_Summer_Men.json
```

This allows you to:
- ✅ Resume after interruption
- ✅ See how many images completed
- ✅ Run multiple times without re-processing

---

## ⚙️ Advanced Configuration

### **Adjust Wait Time:**

Faster (more aggressive, may hit rate limits):
```bash
--wait-time 0.2
```

Slower (safer, less likely to hit limits):
```bash
--wait-time 1.0
```

### **Disable Resume (Start Fresh):**
```bash
--no-resume
```

### **Overwrite Existing Captions:**
```bash
--overwrite
```

---

## 🐛 Error Handling

### **Quota Exceeded (429 Error):**
- Script automatically rotates to next API key
- If single key: waits and retries with exponential backoff
- Retries up to 5 times per image

### **Network Error:**
- Automatically retries with 1s delay
- Saves progress so you can resume

### **Interrupted (Ctrl+C):**
- Progress is saved every 10 images
- Just run the same command again to resume

---

## 📈 Recommended Strategy

### **Option 1: Pay for Billing (Fastest)**
```bash
# Enable billing on 1 key
# Cost: ~$1.50 for 10K images
# Time: ~8 hours

py -3 gemini_caption_multi_key.py ^
  --api-keys YOUR_PAID_KEY ^
  --category all ^
  --wait-time 0.3
```

### **Option 2: Multiple Free Keys (Free but Slower)**
```bash
# Get 3 free API keys
# Capacity: 150 images/day
# Time: ~67 days for 10K images

py -3 gemini_caption_multi_key.py ^
  --api-keys KEY1 KEY2 KEY3 ^
  --category all ^
  --wait-time 0.5
```

### **Option 3: Daily Batches (Free, Manageable)**
```bash
# Process 50 images per day with 1 free key
# Run this daily:

py -3 gemini_caption_multi_key.py ^
  --api-keys YOUR_KEY ^
  --category Summer_Men ^
  --test 50
```

---

## 🎯 Best Practices

1. **Start with test mode** to verify quality:
   ```bash
   --test 10
   ```

2. **Use multiple keys** if on free tier

3. **Enable billing** if you need it done quickly (~$1.50 total)

4. **Let it run overnight** for large batches

5. **Don't interrupt** - but if you do, it will resume automatically

6. **Check progress** by looking at `.txt` files in your data folders

---

## ✅ Verification

Check how many captions were created:
```bash
# Windows PowerShell
(Get-ChildItem "data\Summer\Men\*.txt").Count

# Or check the summary at the end of the script
```

---

## 🆘 Troubleshooting

### **"All retries failed"**
- All your API keys hit quota limits
- Wait 24 hours or enable billing

### **"Caption file not found"**
- Script is still running
- Check the progress bar

### **Progress seems slow**
- Increase `--wait-time` to reduce rate limit errors
- Or add more API keys

---

## 📞 Support

If you encounter issues:
1. Check the error message
2. Verify API keys are valid
3. Ensure internet connection
4. Try with `--test 1` to debug

---

**Created:** October 2025  
**Last Updated:** October 2025

