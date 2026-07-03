import sys
import argparse
import pandas as pd
import pathlib

def extract_page(df, page_num: int, output_dir: pathlib.Path) -> bool:
    """Extract a single page's transcription from the dataframe and save it."""
    if page_num < 1 or page_num > 90:
        print(f"Error: Page number must be between 1 and 90. (Page 90 corresponds to the letter to Gibson's wife).")
        return False
        
    if page_num == 90:
        # Row 89 represents the letter (mss52410002-1)
        match = df[df["Asset"] == "mss52410002-1"]
    else:
        # Rows 0-88 represent diary pages (mss52410001-1 to mss52410001-89)
        pattern = f"mss52410001-{page_num}$"
        match = df[(df["ItemId"] == "mss52410001") & df["Asset"].str.contains(pattern, na=False)]
        
    if match.empty:
        print(f"Error: Could not find transcription for page {page_num} in the CSV.")
        return False
        
    row = match.iloc[0]
    transcript = row["Transcription"]
    if pd.isna(transcript):
        transcript = ""
        
    # Standard format: gibson_pageNNN.txt
    out_file = output_dir / f"gibson_page{page_num:03d}.txt"
    out_file.write_text(transcript, encoding="utf-8")
    print(f"Extracted page {page_num:03d} -> {out_file} ({len(transcript)} chars)")
    return True

def main():
    parser = argparse.ArgumentParser(description="Extract individual Gibson Diary page transcriptions from the raw CSV.")
    parser.add_argument("page", type=str, nargs="?", help="Page number to extract (1-90), or 'all' to extract all pages.")
    parser.add_argument("--csv", type=str, default="data/ground_truth/gibson_transcriptions_raw.csv", help="Path to the raw CSV file.")
    parser.add_argument("--outdir", type=str, default="data/ground_truth", help="Output directory for text files.")
    
    args = parser.parse_args()
    
    csv_path = pathlib.Path(args.csv)
    if not csv_path.exists():
        print(f"Error: Raw CSV not found at {csv_path}")
        sys.exit(1)
        
    output_dir = pathlib.Path(args.outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.read_csv(csv_path)
    
    if not args.page:
        # Prompt user if no argument is provided
        val = input("Enter page number to extract (1-90) or 'all': ").strip()
        if val.lower() == "all":
            args.page = "all"
        else:
            try:
                args.page = int(val)
            except ValueError:
                print("Invalid input. Must be an integer or 'all'.")
                sys.exit(1)
                
    if str(args.page).lower() == "all":
        successes = 0
        for p in range(1, 91):
            if extract_page(df, p, output_dir):
                successes += 1
        print(f"Successfully extracted {successes} of 90 pages.")
    else:
        try:
            p_num = int(args.page)
            extract_page(df, p_num, output_dir)
        except ValueError:
            print("Error: Argument must be a page number (1-90) or 'all'.")
            sys.exit(1)

if __name__ == "__main__":
    main()
