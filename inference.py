import os
import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 inference.py \"<user prompt>\" [output_binary_name]")
        print("Example: python3 inference.py \"Write a C program to calculate the sum of 7 and 3.\" sum_program")
        sys.exit(1)
        
    prompt = sys.argv[1]
    output_bin = sys.argv[2] if len(sys.argv) > 2 else "generated_binary"
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    adapter_dir = os.path.join(workspace_dir, "qwen_binary_generator_lora_generic")
    base_model_id = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    
    print(f"Loading tokenizer: {base_model_id}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    
    print(f"Loading base model: {base_model_id}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    print(f"Loading LoRA adapter from: {adapter_dir}")
    if not os.path.exists(adapter_dir):
        print(f"WARNING: Adapter directory {adapter_dir} not found. Running inference with base model only.")
        model = base_model
    else:
        model = PeftModel.from_pretrained(base_model, adapter_dir)
        
    # Format input prompt using ChatML format
    system_prompt = "You are a C compiler. For any programming prompt, output the compiled C executable directly as a hex string."
    chat_prompt = (
        f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
        f"<|im_start|>user\n{prompt}<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )
    
    print(f"\nPrompt: {prompt}")
    print("Generating binary hex string...")
    
    inputs = tokenizer(chat_prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=4096,  # Allow up to 4096 tokens for binary hex
            eos_token_id=tokenizer.encode("<|im_end|>")[0],
            pad_token_id=tokenizer.eos_token_id,
            do_sample=False  # Deterministic decoding for best compilation correctness
        )
        
    # Decode only the generated assistant tokens
    generated_tokens = outputs[0][len(inputs.input_ids[0]):]
    generated_text = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
    
    # Clean up output (remove any potential whitespace or markdown wrapper)
    hex_str = "".join(generated_text.split())
    
    # Truncate trailing garbage using ELF64 header size metadata
    if hex_str.startswith("7f454c46"):
        try:
            e_shoff_bytes = bytes.fromhex(hex_str[80:96])
            e_shoff = int.from_bytes(e_shoff_bytes, 'little')
            e_shentsize_bytes = bytes.fromhex(hex_str[116:120])
            e_shentsize = int.from_bytes(e_shentsize_bytes, 'little')
            e_shnum_bytes = bytes.fromhex(hex_str[120:124])
            e_shnum = int.from_bytes(e_shnum_bytes, 'little')
            if e_shoff > 0 and e_shentsize > 0 and e_shnum > 0:
                elf_size = e_shoff + e_shnum * e_shentsize
                hex_str = hex_str[:elf_size * 2]
        except Exception:
            pass
            
    print(f"Generated hex length: {len(hex_str)} characters (~{len(hex_str)//2} bytes)")
    
    # 5. Decode hex to binary bytes
    try:
        binary_bytes = bytes.fromhex(hex_str)
    except ValueError as e:
        print("ERROR: Generated output is not a valid hex string!")
        print("Raw generated output preview:")
        print(generated_text[:200] + "...")
        sys.exit(1)
        
    # 6. Save binary and make executable
    bin_path = os.path.join(workspace_dir, output_bin)
    with open(bin_path, "wb") as f:
        f.write(binary_bytes)
        
    os.chmod(bin_path, 0o755)
    print(f"Binary saved successfully to: {bin_path}")
    print(f"Permissions set to executable (chmod +x).")
    
    # 7. Attempt to run it
    print("\nExecuting generated binary...")
    import subprocess
    try:
        run_res = subprocess.run([bin_path], capture_output=True, text=True, timeout=3)
        print(f"Execution Output (Stdout):\n{run_res.stdout}")
        if run_res.stderr:
            print(f"Execution Errors (Stderr):\n{run_res.stderr}")
        print(f"Exit Code: {run_res.returncode}")
    except subprocess.TimeoutExpired:
        print("ERROR: Execution timed out (possible infinite loop or hang).")
    except Exception as e:
        print(f"ERROR: Execution failed: {e}")

if __name__ == "__main__":
    main()
