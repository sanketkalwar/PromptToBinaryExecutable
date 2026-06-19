import os
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer
)
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(workspace_dir, "c_program_dataset_5k.json")
    output_dir = os.path.join(workspace_dir, "qwen_binary_generator_lora_large")
    
    print(f"Loading dataset from: {dataset_path}")
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}. Please run generate_large_dataset.py first.")
        
    with open(dataset_path, "r") as f:
        raw_data = json.load(f)
        
    # All samples in this dataset are positive/working
    train_data = [item for item in raw_data if item["status"] == "positive"]
    print(f"Filtered {len(train_data)} positive samples for training (from {len(raw_data)} total).")
    
    # 2. Convert to Hugging Face Dataset
    dataset = Dataset.from_list(train_data)
    
    # 3. Model and Tokenizer setup
    model_id = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    print(f"Loading tokenizer for: {model_id}")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    
    # 4. Format prompt function using ChatML
    system_prompt = "You are a C compiler. For any programming prompt, output the compiled C executable directly as a hex string."
    
    def format_dataset(example):
        return {
            "prompt": (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{example['prompt']}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            ),
            "completion": f"{example['binary_hex']}<|im_end|>"
        }
        
    print("Formatting dataset for prompt-completion task...")
    dataset = dataset.map(format_dataset)
    
    print(f"Loading model in bfloat16: {model_id}")
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # 5. PEFT (LoRA) Configuration
    print("Setting up LoRA configuration...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    # 6. SFTConfig (Hugging Face / TRL 1.6.0)
    print("Setting up SFTConfig...")
    training_args = SFTConfig(
        output_dir=output_dir,
        per_device_train_batch_size=1,  # Keep batch size 1
        gradient_accumulation_steps=1,  # 1 update per sample
        learning_rate=3e-4,
        logging_steps=50,
        num_train_epochs=10,            # 10 epochs for long-duration training
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        save_strategy="epoch",          # Save checkpoints after each epoch
        save_total_limit=2,             # Keep only the last 2 checkpoints to save disk space
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        gradient_checkpointing=False,   # Keep disabled for max speed
        report_to="none",
        max_length=2048,
        dataset_text_field=None
    )
    
    # 7. Trainer Initialization
    print("Initializing trainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        processing_class=tokenizer,
        args=training_args
    )
    
    # 8. Start Training
    print("Starting training...")
    trainer.train()
    
    # 9. Save final adapter model
    print(f"Saving final fine-tuned adapter to: {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("Fine-tuning complete!")

if __name__ == "__main__":
    main()
