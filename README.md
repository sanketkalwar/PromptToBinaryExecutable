# 🧠 Neural Compiler: Direct Prompt-to-Binary Synthesis

An experimental project to fine-tune `Qwen/Qwen2.5-Coder-1.5B-Instruct` to act as an end-to-end compiler. Given a natural language programming prompt, the model directly outputs the compiled machine code of a stripped, executable ELF64 binary as a raw hexadecimal string—bypassing high-level language generation, assembly, and standard linker toolchains.

---

## ⚡ How is this different from "Prompt-to-Code"?

Traditional AI code generators act as code writing assistants. This project establishes the model as a **Neural Compiler** that directly targets execution environments.

| Feature | 📝 Traditional "Prompt-to-Code" | 0️⃣1️⃣ Neural "Prompt-to-Binary" (This Work) |
| :--- | :--- | :--- |
| **Output Type** | High-level language source code (C, C++, Python, etc.) | Raw hexadecimal string representing stripped ELF64 machine code |
| **Dependencies** | Requires local preprocessors, compilers (GCC/Clang), assemblers, linkers, and standard libraries | Zero compiler toolchain dependency. Runs directly on the target OS/Architecture |
| **System Libs** | Relies on dynamic runtime libraries (e.g. `glibc`) | Runs under strict `-nostdlib` constraints using direct assembly system calls |
| **Binary Size** | Typically heavy (16 KB - 1 MB+) due to runtime boilerplate | Ultra-lightweight stripped binaries averaging **1.1 KB** |
| **Execution** | Code must be saved, built, linked, and then run | Model output is converted to bytes and runs instantly |

---

## 🚀 Futuristic Applications

Direct machine-level neural compilation unlocks novel paradigms across space flight, latency-critical finance, and environmental sustainability:

### 1. Space Exploration & Self-Healing Code (Space Robots)
* **Problem**: Space probes, satellites, or Martian rovers are bombarded with heavy cosmic radiation that can fry hardware registers, disable processor cores, or damage specific memory cells. Standard firmware compiles statically on Earth and cannot adapt to damaged silicon layout dynamically.
* **Neural Solution**: An onboard neural compiler model can self-sense the remaining functional hardware architecture, registers, and available sensors. Using this real-time telemetry as prompt context, it dynamically synthesizes tailor-made, stripped binary drivers that bypass the damaged hardware areas, restoring critical systems on-the-fly without requiring Earth communication or heavy compiler tools.

### 2. High-Frequency Trading (HFT)
* **Problem**: HFT algorithms operate in the sub-microsecond domain. Standard compilers optimize code using generic heuristics that might align instruction caches suboptimally for specialized network cards and memory structures.
* **Neural Solution**: A neural compiler can generate hand-optimized instruction-level binaries specifically laid out for target hardware instruction caches, branching predictors, and CPU cache lines. It generates low-latency execution loops directly, bypassing standard compiler overheads and producing hyper-optimized code streams.

### 3. Reducing Electronic E-Waste
* **Problem**: Millions of fully functional legacy microcontrollers, sensors, and processors are discarded annually because their original compilers, SDKs, and toolchains are deprecated, unsupported, or incompatible with modern operating systems.
* **Neural Solution**: A neural compiler trained on the raw instruction sets (e.g. legacy PIC, 8051, or custom DSP architectures) can target legacy systems directly. Developers can program legacy hardware using natural language prompts, bypassing the deprecated toolchain and extending the lifespan of hardware indefinitely.

### 4. Edge Robotics & Micro-IoT Firmware
* **Problem**: Micro-robots and IoT nodes have extremely constrained memory budgets (measured in bytes) where traditional standard library bloat is unacceptable.
* **Neural Solution**: The neural compiler synthesizes direct `-nostdlib` binaries containing only the bare-minimum machine code needed for the task, fitting inside tiny registers and saving flash memory.

---

## 🛠️ Project Constraints & System Architecture

### 1. `-nostdlib` Execution & Syscalls
To bypass runtime bloat, all binaries are built without the standard C library (`-nostdlib`). Input and output are managed using custom inline assembly wrappers calling direct x86_64 system calls:
* **`read_stdin`**: Wraps the `sys_read` (syscall `0`) using registers `rax`, `rdi`, `rsi`, and `rdx`.
* **`print_str`**: Wraps the `sys_write` (syscall `1`) to output strings to stdout.
* **`exit_process`**: Wraps the `sys_exit` (syscall `60`) to cleanly shut down execution.

### 2. Resolving Division & Modulo (Static Linker Hack)
Under `-nostdlib` mode, the compiler normally outputs unresolved symbols like `__divdi3` and `__moddi3` for 64-bit division/modulo. We resolved this by linking `/usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a` statically during verification:
```bash
ld -s -N <obj_file> /usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a -o <bin_file>
```
This preserves the ultra-compact size (~1.1 KB) while supporting full arithmetic operations.

---

## 📊 Dataset Composition & Fine-Tuning

### Dataset (`c_program_dataset_generic_5k.json`)
Contains **5,486 positive, verified compiled binaries** across 11 programming categories (500 samples per category):
1. **Simple Math**: Operand operations from `stdin`.
2. **Loops**: Multiples, descending/ascending sum ranges.
3. **Algorithms**: Prime checking, GCD, LCM, digit sums.
4. **Arrays**: Bubble sorting, reversing, min/max target search.
5. **Strings**: Vowel count, palindromes, capitalization conversion.
6. **Bitwise**: Bit shifts, logical AND/OR/XOR, set/clear bit.
7. **Structures & Pointers**: Coordinates, area formatting, pointer swaps.
8. **Interactive Calculator**: Reads operands and operator (`+`, `-`, `*`, `/`) from `stdin`.
9. **Tic-Tac-Toe Checker**: Evaluates a 9-char board representation.
10. **Grid Snake Simulator**: Simulates wrapping snake on a 5x5 grid from move inputs.
11. **ASCII Visualizers**: Draw custom shapes and decode uncompressed 24-bit BMP headers to ASCII luminance grids.

### Training Configurations
* **Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
* **LoRA Rank**: `r=16`, `alpha=32`
* **Epochs**: `10`
* **Final Loss**: `1.092e-05`
* **Training Batch Token Accuracy**: reached `100.00%` on final batches.

---

## 🔍 Key Findings: The LoRA Capacity Squeeze

During post-training verification, category-specific evaluation revealed a representation barrier:
* **Token Accuracy**: Stable between **91% and 98%**.
* **Capacity Saturation**: Hexadecimal instruction streams are dense and contain zero redundancy. A LoRA rank of `r=16` is simply saturated by the memory requirements of 55 distinct binary designs (~165,000 dense hex characters).
* **Binary Sensitivity**: A 2.6% error in token generation can shift stack layouts or zero out a string offset, causing immediate runtime `SIGSEGV`.
* **Recommendation**: True exact-match memorization of multiple raw binaries requires scaling LoRA rank to `r>=256` or executing a **Full Parameter Fine-Tuning**.

---

## 💻 Usage & Execution

### Running Inference
To compile a natural language prompt directly into an executable binary:
```bash
python3 inference.py "Write a simple calculator that reads two integers and an operator (+, -, *, /) from stdin, and prints the result." my_calc
```
This loads the adapters, generates the raw hex, strips trailing tokens using ELF header section sizing, and saves the executable `./my_calc`.

### Running Verification
To run tests against Calculator, Snake, Tic-Tac-Toe, and BMP visualizer:
```bash
python3 scratch/verify_adapters.py
```
