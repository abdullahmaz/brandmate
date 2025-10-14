"""
Configuration file for Gemini API keys
Edit this file to add your API keys, then run with:
py -3 gemini_caption_multi_key.py --config run_captioning_config.py --category Summer_Men
"""

# Add your Gemini API keys here (one or more)
API_KEYS = [
    "AIzaSyCTQ9q5DtEM_T5T1K5pmOCCpRk8rPHYrKo",
    "AIzaSyC6-0I2okCeGUBXFViCuatfW5O_nS49Z9I",
    "AIzaSyBs_6NaCSSNlZN2jgbOzFGMwaXJ4pbXrks",
    "AIzaSyAYSJy_X8VzgVkWVXKPJEd9uyW2CT96H6c",
    "AIzaSyAdOR1WxOugMgh5mdMwL91aF3ytpDq5x58"
    # Add more keys below if you have them:
    # "AIzaSyYourSecondKeyHere",
    # "AIzaSyYourThirdKeyHere",
]

# Other settings
WAIT_TIME = 0.5  # Wait time between requests (seconds)
DATA_ROOT = "data"  # Root directory of your dataset

