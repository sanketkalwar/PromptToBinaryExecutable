import sys

def check_env():
    print("--- Environment Check ---")
    missing_packages = []
    
    # Check torch
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA Device Name: {torch.cuda.get_device_name(0)}")
            print(f"CUDA Device Count: {torch.cuda.device_count()}")
    except ImportError:
        print("PyTorch is NOT installed.")
        missing_packages.append("torch")
        
    # Check transformers
    try:
        import transformers
        print(f"Transformers version: {transformers.__version__}")
    except ImportError:
        print("Transformers is NOT installed.")
        missing_packages.append("transformers")
        
    # Check peft
    try:
        import peft
        print(f"PEFT version: {peft.__version__}")
    except ImportError:
        print("PEFT is NOT installed.")
        missing_packages.append("peft")
        
    # Check trl
    try:
        import trl
        print(f"TRL version: {trl.__version__}")
    except ImportError:
        print("TRL is NOT installed.")
        missing_packages.append("trl")
        
    # Check accelerate
    try:
        import accelerate
        print(f"Accelerate version: {accelerate.__version__}")
    except ImportError:
        print("Accelerate is NOT installed.")
        missing_packages.append("accelerate")

    # Check datasets
    try:
        import datasets
        print(f"Datasets version: {datasets.__version__}")
    except ImportError:
        print("Datasets is NOT installed.")
        missing_packages.append("datasets")
        
    print("\n--- Summary ---")
    if missing_packages:
        print("The following packages are missing and must be installed:")
        print("pip install " + " ".join(missing_packages))
        sys.exit(1)
    else:
        print("All required packages are installed and ready!")
        sys.exit(0)

if __name__ == "__main__":
    check_env()
