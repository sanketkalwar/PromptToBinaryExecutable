import os
import json
import tempfile
import subprocess
import signal

def main():
    workspace_dir = "/home/manifest/Documents/antigravity/mysterious-raman"
    json_path = os.path.join(workspace_dir, "c_program_dataset.json")
    jsonl_path = os.path.join(workspace_dir, "c_program_dataset.jsonl")
    
    print("--- Verification Script Start ---")
    
    # 1. Check file existence
    if not os.path.exists(json_path):
        print(f"ERROR: JSON file not found at {json_path}")
        return
    if not os.path.exists(jsonl_path):
        print(f"ERROR: JSONL file not found at {jsonl_path}")
        return
        
    # 2. Load and validate counts
    with open(json_path, "r") as f:
        dataset = json.load(f)
        
    total_samples = len(dataset)
    print(f"Total samples found: {total_samples}")
    if total_samples != 100:
        print(f"ERROR: Expected 100 samples, got {total_samples}")
        return
        
    positives = [item for item in dataset if item["status"] == "positive"]
    negatives = [item for item in dataset if item["status"] == "negative"]
    
    print(f"Positive samples: {len(positives)}")
    print(f"Negative samples: {len(negatives)}")
    
    if len(positives) != 83:
        print(f"ERROR: Expected 83 positive samples, got {len(positives)}")
    if len(negatives) != 17:
        print(f"ERROR: Expected 17 negative samples, got {len(negatives)}")
        
    temp_dir = tempfile.gettempdir()
    
    # 3. Test a positive binary
    print("\nVerifying a positive sample execution...")
    pos_sample = positives[0]
    print(f"Prompt: {pos_sample['prompt']}")
    
    pos_bin_path = os.path.join(temp_dir, "verify_pos.bin")
    # Decode and save
    binary_bytes = bytes.fromhex(pos_sample["binary_hex"])
    with open(pos_bin_path, "wb") as f:
        f.write(binary_bytes)
    os.chmod(pos_bin_path, 0o755)
    
    try:
        run_res = subprocess.run([pos_bin_path], capture_output=True, timeout=2)
        print(f"Exit code: {run_res.returncode}")
        print(f"Stdout: {run_res.stdout.decode().strip()}")
        print(f"Stderr: {run_res.stderr.decode().strip()}")
        if run_res.returncode == 0:
            print("Positive binary verification: SUCCESS")
        else:
            print("Positive binary verification: FAILED (non-zero exit code)")
    except Exception as e:
        print(f"Positive binary execution failed: {e}")
    finally:
        if os.path.exists(pos_bin_path):
            os.remove(pos_bin_path)
            
    # 4. Test a negative binary
    print("\nVerifying a negative sample execution...")
    neg_sample = negatives[0]
    print(f"Prompt: {neg_sample['prompt']}")
    
    neg_bin_path = os.path.join(temp_dir, "verify_neg.bin")
    # Decode and save
    binary_bytes = bytes.fromhex(neg_sample["binary_hex"])
    with open(neg_bin_path, "wb") as f:
        f.write(binary_bytes)
    os.chmod(neg_bin_path, 0o755)
    
    try:
        run_res = subprocess.run([neg_bin_path], capture_output=True, timeout=2)
        exit_code = run_res.returncode
        print(f"Exit code: {exit_code}")
        is_segfault = (exit_code == -11 or exit_code == -signal.SIGSEGV)
        if is_segfault:
            print("Negative binary verification: SUCCESS (correctly caught segfault)")
        else:
            print(f"Negative binary verification: FAILED (did not segfault, returned {exit_code})")
    except Exception as e:
        print(f"Negative binary execution error: {e}")
    finally:
        if os.path.exists(neg_bin_path):
            os.remove(neg_bin_path)
            
    print("\n--- Verification Script End ---")

if __name__ == "__main__":
    main()
