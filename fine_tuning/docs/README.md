
# Multi-Category Image Scraper

A sophisticated web scraper designed to automatically download product images from Khaadi's website, organized by clothing categories (Winter/Summer) and gender (Men/Women).

## ✨ Features

- **🗂️ Organized Storage**: Automatically sorts images into `Winter/Men`, `Winter/Women`, `Summer/Men`, `Summer/Women` folders
- **🔄 Advanced Pagination**: Handles both infinite scroll and traditional page navigation
- **🎯 Selective Scraping**: Easy enable/disable system for specific categories
- **📊 Progress Tracking**: Detailed logging and real-time progress updates
- **🛡️ Error Handling**: Robust error recovery and duplicate prevention
- **⚡ Flexible Testing**: Test individual categories before full scraping
- **🤖 Automated Setup**: Auto-downloads ChromeDriver, no manual installation needed

## 📦 Installation

### Prerequisites
- Python 3.7+
- Google Chrome browser
- Internet connection

### Setup
1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure URLs** (see Configuration section)

## 🚀 Quick Start

1. **Configure your URLs** in `config.py`:
   ```python
   "Summer_Women": {
       "url": "https://pk.khaadi.com/women/summer/",
       "enabled": True  # Set to True to enable scraping
   }
   ```

2. **Run the scraper**:
   ```bash
   python scrape_data.py
   ```

3. **Check your organized images** in the `data/` folder!

## ⚙️ Configuration

### Edit `config.py` to customize:

```python
URL_CONFIG = {
    "Winter_Men": {
        "url": "https://pk.khaadi.com/men/winter/",
        "folder": os.path.join("data", "Winter", "Men"),
        "enabled": True  # Set to False to skip this category
    },
    "Winter_Women": {
        "url": "https://pk.khaadi.com/women/winter/", 
        "folder": os.path.join("data", "Winter", "Women"),
        "enabled": False  # Disabled - won't be scraped
    },
    # Add more categories as needed...
}
```

**Key Settings**:
- `url`: The Khaadi page to scrape
- `folder`: Where to save images for this category
- `enabled`: `True` to scrape, `False` to skip

## 🎮 Usage Commands

### Basic Operations
```bash
# Run full scraper (enabled categories only)
python scrape_data.py

# Show current configuration
python scrape_data.py show_config

# Test single category without affecting config
python scrape_data.py test Winter_Men
```

### Category Management (Legacy - use config.py instead)
```bash
# Enable/disable categories
python scrape_data.py enable Winter_Men
python scrape_data.py disable Summer_Women
python scrape_data.py enable_only Winter_Men
python scrape_data.py enable_all
python scrape_data.py disable_all
```

## 📁 Folder Structure

After running, your images will be organized as:
```
data/
├── Winter/
│   ├── Men/
│   │   ├── Winter_Men_0.jpg
│   │   ├── Winter_Men_1.jpg
│   │   └── ...
│   └── Women/
│       ├── Winter_Women_0.jpg
│       └── ...
└── Summer/
    ├── Men/
    │   └── ...
    └── Women/
        └── ...
```

## 🔧 How It Works

### 1. **Multi-Page Navigation**
- Scrolls to load infinite scroll content
- Automatically detects and clicks "Next" page buttons  
- Continues until no more pages exist
- Handles up to 100 pages per category

### 2. **Smart Image Collection**
- Finds product images using CSS selectors
- Prevents duplicate downloads across pages
- Downloads high-quality source images
- Generates sequential, organized filenames

### 3. **Robust Error Handling**
- Network timeout protection
- File I/O error recovery
- Graceful handling of page structure changes
- Detailed error logging

## 📊 Example Output

```
2025-10-02 15:30:15 - INFO - Starting Khaadi multi-category scraper...
2025-10-02 15:30:15 - INFO - Found 1 enabled categories to process

==================================================
Processing category: Summer_Women
URL: https://pk.khaadi.com/women/summer/
Target folder: data\Summer\Women
==================================================

--- Processing Page 1 ---
Scroll 1: Found 64 images on current page
Scroll 2: Found 128 images on current page
...
Found next page button, navigating to page 2...

--- Processing Page 2 ---
...

Completed processing 5 pages
Total unique images found across all pages: 1,247

Starting downloads for Summer_Women...
Downloaded 10 images for Summer_Women...
Downloaded 20 images for Summer_Women...
...

Download summary for Summer_Women: 1247 successful, 0 failed
Total images downloaded: 1247
Total execution time: 0:18:32.445
```

## 🛠️ Troubleshooting

### Common Issues

**"ChromeDriver not found"**
- The script auto-downloads ChromeDriver
- Make sure you have Google Chrome installed
- Check your internet connection

**"No images found"**
- Verify the URL is correct and accessible
- Check if the website structure has changed
- Try testing with a single category first

**"Import error: config.py not found"**
- Make sure `config.py` exists in the same directory
- Copy the URL_CONFIG section if needed

**Scraper stops early**
- Check the log files for detailed error information
- Verify internet connection is stable
- Some websites may have rate limiting

### Performance Tips

- **Test first**: Use `python scrape_data.py test <category>` before full runs
- **Enable selectively**: Only enable categories you need to save time
- **Monitor logs**: Check log files for optimization opportunities
- **Respect servers**: Built-in delays prevent overloading the website

## 📝 Logs

The scraper creates detailed log files:
- **Console output**: Real-time progress
- **Log files**: `scraper_log_YYYYMMDD_HHMMSS.log`
- **Categories tracked**: Success/failure counts per category

## 🤝 Contributing

Feel free to improve this scraper:
1. Fork the repository
2. Add new features or fix bugs
3. Submit a pull request

### Possible Enhancements
- Support for other clothing websites
- Image format options (PNG, WebP)
- Size/resolution filtering  
- Metadata extraction (price, title, etc.)
- GUI interface

## ⚠️ Legal Notice

This scraper is for educational purposes. Please:
- Respect website terms of service
- Don't overload servers (built-in delays help)
- Use scraped content responsibly
- Consider the website's robots.txt

## 📋 Requirements

See `requirements.txt` for exact versions:
- `requests`: HTTP requests
- `beautifulsoup4`: HTML parsing
- `selenium`: Browser automation
- `webdriver-manager`: Automatic ChromeDriver management
- `lxml`: XML/HTML processing

## 🎯 Use Cases

Perfect for:
- **Fashion Research**: Analyzing clothing trends
- **Dataset Creation**: Building image datasets for ML
- **Inventory Analysis**: Tracking product availability  
- **Design Inspiration**: Collecting style references
- **Academic Projects**: Web scraping demonstrations

## 💡 Tips

1. **Start Small**: Test with one category first
2. **Check URLs**: Verify category URLs are correct before bulk scraping
3. **Monitor Progress**: Watch the console output for issues
4. **Organize Results**: Images are automatically sorted by category
5. **Be Patient**: Large collections take time to download

---

**Happy Scraping!** 🚀
