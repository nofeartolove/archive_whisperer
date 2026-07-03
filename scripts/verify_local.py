import pathlib
import jiwer
import json

project_root = pathlib.Path(__file__).parent.parent.resolve()

def compare_files(gt_path: pathlib.Path, trans_path: pathlib.Path):
    if not gt_path.exists():
        return f"Ground truth file missing: {gt_path.name}"
    if not trans_path.exists():
        return f"Transcription file missing: {trans_path.name}"
        
    gt_text = gt_path.read_text(encoding="utf-8").strip()
    trans_text = trans_path.read_text(encoding="utf-8").strip()
    
    # Strip '|' separators to perform fair comparison
    hyp_clean = trans_text.replace("|", " ").strip()
    ref_clean = gt_text.strip()
    
    wer_val = jiwer.wer(ref_clean, hyp_clean)
    cer_val = jiwer.cer(ref_clean, hyp_clean)
    
    return {
        "wer": wer_val,
        "cer": cer_val,
        "gt_len": len(ref_clean),
        "trans_len": len(hyp_clean)
    }

def main():
    pages = ["011", "037", "049"]
    item_id = "mss5241.mss5241_01_001_089"
    
    print("\nLocal Verification against Ground Truth files:")
    print("==================================================")
    
    for page in pages:
        gt_path = project_root / "data" / "ground_truth" / f"gibson_page{page}.txt"
        trans_path = project_root / "output" / f"{item_id}_{page}.txt"
        
        res = compare_files(gt_path, trans_path)
        if isinstance(res, dict):
            print(f"Gibson Page {page}:")
            print(f" - Word Error Rate (WER): {res['wer'] * 100:.2f}%")
            print(f" - Character Error Rate (CER): {res['cer'] * 100:.2f}%")
            print(f" - Ground Truth Length: {res['gt_len']} chars")
            print(f" - Transcription Length: {res['trans_len']} chars")
        else:
            print(f"Gibson Page {page}: {res}")
        print("--------------------------------------------------")

if __name__ == "__main__":
    main()
