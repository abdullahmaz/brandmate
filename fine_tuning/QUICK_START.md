# 🚀 Quick Start - Gemini Captioning

## Three Ways to Add API Keys

---

### **Method 1: Command Line** (Quick & Simple)

Open PowerShell/Command Prompt and run:

```bash
py -3 gemini_caption_multi_key.py --api-keys YOUR_API_KEY_HERE --category Summer_Men
```

**Example:**
```bash
py -3 gemini_caption_multi_key.py --api-keys AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo --category Summer_Men
```

**For multiple keys:**
```bash
py -3 gemini_caption_multi_key.py --api-keys KEY1 KEY2 KEY3 --category Summer_Men
```

---

### **Method 2: Batch File** (Easiest - Just Double-Click!)

1. **Open** `run_captioning.bat` in Notepad
2. **Edit line 10** - Replace with your API key:
   ```batch
   set API_KEYS=YOUR_API_KEY_HERE
   ```
3. **Edit line 13** - Choose category:
   ```batch
   set CATEGORY=Summer_Men
   ```
4. **Save** the file
5. **Double-click** `run_captioning.bat` to run!

**For multiple keys:**
```batch
set API_KEYS=KEY1 KEY2 KEY3
```

---

### **Method 3: Python Config File** (Most Organized)

1. **Open** `run_captioning_config.py` in your editor
2. **Edit** the `API_KEYS` list:
   ```python
   API_KEYS = [
       "AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo",
       "AIzaSyYourSecondKeyHere",  # Add more if you have them
   ]
   ```
3. **Save** the file
4. **Run**:
   ```bash
   py -3 gemini_caption_multi_key.py --api-keys AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo --category Summer_Men
   ```

---

## 🎯 Quick Commands

### **Test with 10 images:**
```bash
py -3 gemini_caption_multi_key.py --api-keys YOUR_KEY --category Summer_Men --test 10
```

### **Process full category:**
```bash
py -3 gemini_caption_multi_key.py --api-keys YOUR_KEY --category Summer_Men
```

### **Process all categories:**
```bash
py -3 gemini_caption_multi_key.py --api-keys YOUR_KEY --category all
```

---

## 🔑 Get API Keys

1. Go to: https://aistudio.google.com/apikey
2. Click **"Create API Key"**
3. Copy the key (starts with `AIzaSy...`)
4. Add it to your command/batch file

**For multiple free keys:**
- Create 2-3 Google accounts
- Get API key from each
- Add all keys space-separated

---

## 📊 What Happens Next?

1. Script loads your images
2. Sends each to Gemini API
3. Gets detailed fashion captions
4. Saves as `.txt` files next to images
5. Shows progress bar
6. Can resume if interrupted

**Example output:**
```
data/Summer/Men/
├── Summer_Men_0.jpg
├── Summer_Men_0.txt  ← "The model is wearing a white chikankari..."
├── Summer_Men_1.jpg
├── Summer_Men_1.txt  ← "A dark colored kurta with band collar..."
```

---

## ⏱️ Time Estimates

| Category | Images | Time (1 key, free) | Time (1 key, paid) |
|----------|--------|--------------------|--------------------|
| Summer_Men | 2500 | 50 days | 2 hours |
| All | 10000 | 200 days | 8 hours |

**With 3 free keys:** 3x faster
**With paid key:** ~$1.50 total for 10K images

---

## ✅ You're Ready!

Just choose your preferred method above and run it! 🎉

