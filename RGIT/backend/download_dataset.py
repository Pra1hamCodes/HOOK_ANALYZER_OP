"""Download script — fetches YouTube Trending Video dataset."""
import urllib.request
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

URLS = [
    "https://raw.githubusercontent.com/mitchelljy/Trending-YouTube-Scraper/master/output/USvideos.csv",
    "https://raw.githubusercontent.com/dushyantkumark/YouTube_Trending_VS_Analysis/main/USvideos.csv",
    "https://raw.githubusercontent.com/MohamedHamisa/YouTube-Videos-Views-Prediction/main/USvideos.csv",
    "https://raw.githubusercontent.com/AbdulRehman7590/YouTube_EDA_Project/main/USvideos.csv",
]

out_path = os.path.join(DATA_DIR, "USvideos.csv")

for url in URLS:
    repo = url.split("/")[4]
    print(f"Trying: {repo}...")
    try:
        urllib.request.urlretrieve(url, out_path)
        size = os.path.getsize(out_path)
        if size > 10000:
            print(f"SUCCESS! Downloaded {size // 1024} KB")
            with open(out_path, encoding="utf-8", errors="replace") as f:
                for i, line in enumerate(f):
                    if i < 2:
                        print(f"  Line {i}: {line[:150].strip()}")
                    else:
                        break
            sys.exit(0)
        else:
            os.remove(out_path)
            print(f"Too small ({size}B)")
    except Exception as e:
        print(f"  Failed: {e}")

print("All GitHub mirrors failed. Trying Kaggle API...")
try:
    import subprocess
    result = subprocess.run(
        ["kaggle", "datasets", "download", "-d", "datasnaek/youtube-new", "-p", DATA_DIR, "--unzip"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        print("Kaggle download succeeded!")
        for f in os.listdir(DATA_DIR):
            if f.endswith(".csv"):
                print(f"  Found: {f} ({os.path.getsize(os.path.join(DATA_DIR, f)) // 1024} KB)")
    else:
        print(f"Kaggle failed: {result.stderr[:200]}")
except Exception as e:
    print(f"Kaggle API failed: {e}")

print("\nFallback: Will try opendatasets...")
try:
    os.environ["KAGGLE_USERNAME"] = "prathmeshpandey3735"
    os.environ["KAGGLE_KEY"] = ""
    # If this doesn't work, we'll generate the dataset from a different real source
    print("No Kaggle credentials available.")
    print("Please download manually from: https://www.kaggle.com/datasets/datasnaek/youtube-new")
    print(f"Place USvideos.csv in: {DATA_DIR}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
