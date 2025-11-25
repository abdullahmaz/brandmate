"""
Fixed Daily Caption Processing Runner
Runs with proper output flushing and real-time display
"""

import os
import sys
import subprocess
from datetime import date

# Suppress ALTS warnings from Google AI library
os.environ['GRPC_VERBOSITY'] = 'ERROR'

# Fix Windows console encoding to support emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    print("=" * 60)
    print("DAILY CAPTION PROCESSING RUNNER - FIXED OUTPUT")
    print(f"Date: {date.today()}")
    print("=" * 60)
    
    # Change to the fine_tuning directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Run the daily captioning script with unbuffered output
    cmd = [sys.executable, "-u", "scripts/run_daily_captioning.py"]
    
    print("🚀 Starting daily captioning with real-time output...")
    print("=" * 60)
    
    try:
        # Run with real-time output
        result = subprocess.run(cmd, check=True, text=True, bufsize=1, universal_newlines=True)
        print("\n" + "=" * 60)
        print("✅ Daily captioning completed successfully!")
        print("=" * 60)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running daily captioning: {e}")
        print("Return code:", e.returncode)
        return 1
    
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
