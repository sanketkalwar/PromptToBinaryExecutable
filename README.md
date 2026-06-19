# Qwen ELF Binary Generator: Direct Prompt-to-Binary Compilation

An experimental project to fine-tune `Qwen/Qwen2.5-Coder-1.5B-Instruct` to act as an end-to-end compiler. Given a natural language programming prompt, the model directly outputs the compiled machine code of a stripped, executable ELF64 binary as a raw hexadecimal string.

---

## 1. Project Overview & Constraints

The objective is to train a language model to perform **direct associative mapping and synthesis** from prompts to executable binaries, bypassing standard intermediate compilers.

### Low-Level Constraints
* **`-nostdlib` Execution**: All programs must compile without the C standard library to ensure small binary sizes (under `1.4 KB`). 
* **Inline Assembly Syscalls**: Basic I/O, string operations, integer parsing, and exit routines are implemented via custom inline x86_64 assembly helpers (`sys_read`, `sys_write`, `sys_exit`).
* **Static linking of `libgcc.a`**: Under `-nostdlib`, the linker normally cannot resolve 64-bit integer division and modulo (`__divdi3`, `__moddi3`). This was solved by directly linking `/usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a` during the verification compilation pipeline:
  ```bash
  ld -s -N <obj_file> /usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a -o <bin_file>
  ```
  This keeps ELF sizes minimal (averaging `1.1 KB`) while resolving 64-bit arithmetic.

---

## 2. Dataset Composition (`c_program_dataset_generic_5k.json`)

The dataset contains **5,486 positive, verified compiled binaries** across 11 programming categories. Every binary in the dataset dynamically reads inputs from `stdin`, executes, and outputs formatting to `stdout`:

1. **Simple Math**: Addition, subtraction, multiplication, division, modulo, and averages.
2. **Loops**: Ascending/descending ranges, multiples of numbers, sums.
3. **Algorithms**: Prime checking, GCD, LCM, digit sums, and digit reversing.
4. **Arrays**: Reversing, sorting (bubble sort), finding max/min/average, index search.
5. **Strings**: Vowel/consonant count, palindromes, capitalization conversion, reverse, concatenation.
6. **Bitwise Operations**: Bit shifts, bitwise AND/OR/XOR, set/clear/check bit.
7. **Structures & Pointers**: Coordinates, area calculations, Complex number arithmetic, pointer swap.
8. **Calculator**: Interactive operator-guided calculator (reads operands and operator, e.g. `45 * 5`).
9. **Tic-Tac-Toe Checkers**: Parses a 9-character board state from `stdin` and outputs winner status (`X`, `O`, `D`, `I`).
10. **Grid Snake Simulators**: Simulates wrapping snake movement on a 5x5 grid based on coordinates and move instructions (`R`, `L`, `U`, `D`).
11. **ASCII Visualizers & BMP Decoders**:
    * **ASCII Shape Drawers**: Draws customized shapes based on read dimensions.
    * **BMP-to-ASCII Decoders**: Parses uncompressed 24-bit BMP file headers from `stdin` and outputs ASCII art luminance maps.

---

## 3. Training & Convergence

We fine-tuned the model using **LoRA (Low-Rank Adaptation)** in `bfloat16` precision:
* **Base Model**: `Qwen/Qwen2.5-Coder-1.5B-Instruct`
* **LoRA Rank**: `r=16`, `alpha=32`, targeting all linear projection modules.
* **Epochs**: `10` epochs (~54,860 steps total, resumed using Hugging Face checkpointing after server interruption).
* **Final Loss**: `1.092e-05`
* **Training Batch Token Accuracy**: reached `100.00%` on final batches.

---

## 4. Key Findings & Insights

### A. LoRA Capacity Squeeze (The Memorization Squeeze)
While the training loss converged to `1.092e-05`, category-specific evaluation shows that token accuracies plateaued between **91% and 98%**:
* Because a binary hex sequence contains thousands of dense, non-redundant instruction bytes, a LoRA rank of `r=16` is simply saturated by the memory requirements of 55 unique binaries (~165,000 total characters).
* While the **Calculator** application compiles and runs successfully (exit code 0, outputs `225` for input `45 * 5`), longer binaries (Tic-Tac-Toe, Snake, BMP visualizer) suffer from minor byte-level offset shifts (e.g. stack offset mismatch or `.rodata` offset shift), leading to runtime `SIGSEGV` or incorrect printouts.
* **Recommendation**: Perfect exact-match memorization of raw binaries requires scaling up LoRA rank to `r>=256` or performing **Full Parameter Fine-Tuning**.

### B. Concept Association on Out-of-Distribution (OOD) Math Prompts
When tested on unseen math prompts, the model successfully outputs syntactically valid ELF headers and executable code structures (exit code `0`). However, it performs associative fallback mapping to the closest memorized binary category:
* *Prompt: "calculate the square of N"* $\rightarrow$ Maps to Loop category: *"print the squares of numbers from 1 to N"* (`1 4 9 16 25 ...`).
* *Prompt: "calculate the sum of three integers"* $\rightarrow$ Maps to Math category: *"sum of two integers"* (ignoring the third input).

---

## 5. Usage & Execution Instructions

### A. Running Inference
To generate a binary directly from a prompt:
```bash
python3 inference.py "Write a C program to a simple calculator application that reads two integers and an operator (+, -, *, /) from stdin, and prints the result." my_calculator
```
This loads the adapter, generates the hex string, strips trailing garbage using ELF section metadata size computation, and outputs the executable `./my_calculator`.

### B. Running Verification
To verify the fine-tuned adapter against in-domain tests:
```bash
python3 scratch/verify_adapters.py
```
This tests the model on Calculator, Tic-Tac-Toe, Snake, and BMP visualizer prompts.

### C. Running Evaluations
To view exact token accuracy across the categories:
```bash
python3 scratch/eval_categories.py
```
