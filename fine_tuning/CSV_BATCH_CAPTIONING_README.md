# CSV Batch Captioning System

## Overview

This system processes fashion images using Google Gemini API with the following key features:

- **CSV Output**: All captions are saved to CSV files (filename, caption) instead of individual txt files
- **Batch Processing**: Processes exactly 100 images per API key to respect daily limits
- **Multiple API Keys**: Supports up to 5 API keys for 500 images per day total
- **Daily Workflow**: Designed for daily execution with automatic progress tracking
- **Resume Capability**: Continues from where it left off if interrupted

## Files

- `gemini_caption_csv_batch.py` - Main batch captioning script
- `run_daily_captioning.py` - Daily runner script for all categories
- `run_daily_captioning.bat` - Windows batch file for easy execution

## Setup

### 1. Install Dependencies

```bash
pip install google-generativeai Pillow tqdm
```

### 2. Get API Keys

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create up to 5 API keys
3. Edit `run_daily_captioning.py` and replace the placeholder API keys:

```python
API_KEYS = [
    "your_actual_api_key_1",
    "your_actual_api_key_2", 
    "your_actual_api_key_3",
    "your_actual_api_key_4",
    "your_actual_api_key_5"
]
```

## Usage

### Easy Daily Run (Recommended)

**Windows:**
```bash
# Just double-click the batch file:
run_daily_captioning.bat
```

**Command Line:**
```bash
python run_daily_captioning.py
```

This will process all 4 categories (Summer_Men, Summer_Women, Winter_Men, Winter_Women) with your configured API keys.

### Manual Single Category

```bash
python gemini_caption_csv_batch.py \
    --category Summer_Men \
    --api-keys "key1" "key2" "key3" "key4" "key5" \
    --data-root data_backup \
    --batch-size 100
```

## How It Works

### Daily Processing Workflow

1. **Day 1**: Run the script → processes 500 images (100 per API key)
2. **Day 2**: Run again → continues from image 501, processes next 500
3. **Day N**: Continue until all images are captioned

### API Key Rotation

- Processes 100 images with Key 1
- Automatically switches to Key 2 for next 100 images  
- Continues through all 5 keys
- Stops when daily limit reached (500 images total)

### Output Files

**CSV Files:**
- `captions_Summer_Men_20251014.csv`
- `captions_Summer_Women_20251014.csv` 
- `captions_Winter_Men_20251014.csv`
- `captions_Winter_Women_20251014.csv`

**CSV Format:**
```csv
filename,caption
sm_1.jpg,"A man wearing a light blue cotton kurta with white shalwar in Pakistani summer eastern wear. The kurta features a simple round neckline and relaxed fit typical of lawn fabric clothing. He stands against a neutral background in a casual pose."
sm_2.jpg,"Pakistani men's summer shalwar kameez in beige cotton fabric with traditional cut and styling..."
```

**Progress Files (Auto-generated):**
- `.caption_progress_Summer_Men.json` - Tracks daily progress
- `.caption_progress_Summer_Women.json`
- `.caption_progress_Winter_Men.json` 
- `.caption_progress_Winter_Women.json`

### Resume Capability

If the script is interrupted:
- Progress is saved after each image
- Restart the script and it continues from where it stopped
- No images are processed twice
- Safe to stop and restart anytime

## Configuration Options

### Batch Size
Default is 100 images per API key (Gemini's daily limit). Don't change unless you know the current limits.

### Wait Time
Default is 0.5 seconds between requests to avoid rate limiting. Increase if you get rate limit errors.

### Daily Limit
Automatically calculated as: `batch_size × number_of_api_keys`
- 1 key = 100 images/day
- 5 keys = 500 images/day

## Troubleshooting

### "Import errors" when running
```bash
pip install google-generativeai Pillow tqdm
```

### "Invalid API key" errors
- Check your API keys are correct
- Ensure they're not expired
- Verify you have Gemini API access

### "Rate limit exceeded"
- Increase `--wait-time` (e.g., `--wait-time 1.0`)
- The script will automatically rotate to next API key

### Progress not saving
- Ensure you have write permissions in the directory
- Check disk space for progress files

## File Structure

```
fine_tuning/
├── data_backup/           # Your renamed image folders  
│   ├── Summer/
│   │   ├── Men/          # sm_1.jpg, sm_2.jpg, etc.
│   │   └── Women/        # sw_1.jpg, sw_2.jpg, etc.
│   └── Winter/
│       ├── Men/          # wm_1.jpg, wm_2.jpg, etc.
│       └── Women/        # ww_1.jpg, ww_2.jpg, etc.
├── gemini_caption_csv_batch.py    # Main script
├── run_daily_captioning.py        # Daily runner
├── run_daily_captioning.bat       # Windows batch file
└── captions_*.csv                 # Generated CSV files
```

## Tips

1. **Run daily** at the same time to establish a routine
2. **Monitor CSV files** to track progress across days  
3. **Keep API keys secure** - don't commit them to git
4. **Backup CSV files** regularly as they contain your work
5. **Check progress files** if you need to see detailed status

## Expected Performance

- **Processing Speed**: ~2-3 images per minute (with 0.5s wait time)
- **Daily Capacity**: 500 images (with 5 API keys)
- **Total Time**: ~3-4 hours for 500 images
- **For 6662 images**: ~13-14 days of daily processing