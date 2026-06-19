---
name: qwen-binary-generation
description: Guide and scripts for direct prompt-to-binary compiler model generation, compilation pipelines under -nostdlib, and debugging machine code reconstruction mismatches.
---

# Qwen Prompt-to-Binary Generation & Execution Skill

This skill guides agent workflows for generating, compiling, executing, and validating raw ELF64 binaries synthesized directly by causal language models (such as `Qwen/Qwen2.5-Coder-1.5B`).

---

## 1. Low-Level Compilation Under `-nostdlib`

When compiling/linking C programs to keep the binary size minimal (under `1.4 KB`) and avoid external library dependencies:

### A. Inline Assembly Syscalls
All input/output must use inline assembly system call wrappers to prevent standard library linkages.
```c
void print_str(char *s) {
    int len = 0;
    while (s[len]) len++;
    asm volatile(
        "syscall\n"
        :
        : "a"(1L), "D"(1L), "S"(s), "d"((long)len)
        : "rcx", "r11"
    );
}
```
> [!CAUTION]
> **Register Clobbering**: Never manually overwrite registers like `%rdi` or `%rsi` inside the assembly block (e.g. `mov %0, %%rsi`) without registering constraints or declaring them clobbered. Doing so can collide with compiler register allocations, leading to pointers being zeroed out and triggering `SIGSEGV` (Segmentation Fault) at runtime. Always use matching constraints like `"S"(s)` and `"d"(len)`.

### B. 64-Bit Arithmetic Linkage
Under `-nostdlib`, the linker cannot automatically resolve 64-bit integer division (`__divdi3`) or modulo (`__moddi3`) helper calls.
* **Solution**: Statically link `/usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a` directly using `ld`:
  ```bash
  ld -s -N main.o /usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a -o main.bin
  ```

---

## 2. Tokenization & Model Inference

### A. Padding / EOS Token Masking Trap
If `tokenizer.pad_token = tokenizer.eos_token` is set during training, the Hugging Face collator might mask out the loss of the `<|im_end|>` token. This prevents the model from learning to emit the EOS token during generation, causing it to print continuous trailing padding zeros (`00`) past the end of the binary.

### B. Truncating Trailing Garbage via ELF Section Headers
To extract the exact binary size and truncate trailing padding zeros from the model's hex string output:
1. Parse the ELF64 header fields starting at character index `80` (offset `40` bytes).
2. Read the Section Header Table Offset (`e_shoff`, 8 bytes), size of section headers (`e_shentsize`, 2 bytes), and number of section headers (`e_shnum`, 2 bytes).
3. Compute the exact file size:
   $$\text{file\_size} = e\_shoff + (e\_shnum \times e\_shentsize)$$
4. Truncate the hex output to exactly $\text{file\_size} \times 2$ characters.

Python implementation:
```python
if hex_str.startswith("7f454c46"):
    try:
        e_shoff = int.from_bytes(bytes.fromhex(hex_str[80:96]), 'little')
        e_shentsize = int.from_bytes(bytes.fromhex(hex_str[116:120]), 'little')
        e_shnum = int.from_bytes(bytes.fromhex(hex_str[120:124]), 'little')
        if e_shoff > 0 and e_shentsize > 0 and e_shnum > 0:
            elf_size = e_shoff + e_shnum * e_shentsize
            hex_str = hex_str[:elf_size * 2]
    except Exception:
        pass
```

---

## 3. Capacity Mismatches & Debugging

If the model-generated binary compiles but crashes with `SIGSEGV` or prints garbage characters:
1. **Capacity Saturation**: Standard LoRA adapters (e.g. rank `16`) saturate when memorizing large sequences of raw machine code hex strings. Mismatches will occur in stack offsets (e.g., loading `0xb(%rsp)` instead of `0xd(%rsp)`) or string constants locations inside `.rodata`.
2. **Offset Mismatch Debugging**: Run a character-by-character hex comparison between the generated binary and the correct compiler-produced ground truth binary to trace exact offsets:
   ```python
   mismatches = [(idx, c1, c2) for idx, (c1, c2) in enumerate(zip(gen_hex, gt_hex)) if c1 != c2]
   ```
3. **Debugging Memory Addresses**: Use `gdb` or disassemble with `objdump -d <binary>` to inspect if instruction jumps or register moves point to memory maps that contain `.shstrtab` or headers instead of `.rodata`.
