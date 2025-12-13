
from pathlib import Path
from main import initialize_output_files
from config import FILTERS_CSV_PATH, OUTPUT_DIR
import logging

logging.basicConfig(level=logging.INFO)

def test_cleanup():
    # 1. Create dummy files
    FILTERS_CSV_PATH.write_text("dummy csv")
    md_path = OUTPUT_DIR / "filters_results.md"
    md_path.write_text("dummy markdown")
    
    print(f"Created dummy files:\n{FILTERS_CSV_PATH}\n{md_path}")
    
    # 2. Run cleanup
    print("Running cleanup...")
    initialize_output_files()
    
    # 3. Verify deletion
    if not FILTERS_CSV_PATH.exists() and not md_path.exists():
        print("SUCCESS: Files removed.")
    else:
        print(f"FAILURE: CSV exists? {FILTERS_CSV_PATH.exists()} MD exists? {md_path.exists()}")

if __name__ == "__main__":
    test_cleanup()
