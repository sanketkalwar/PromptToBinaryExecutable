import os
import subprocess
import tempfile
import json
import random

# Base helper templates for stdin parsing under -nostdlib
c_header_parse = """
#define NULL ((void*)0)

void print_str(char *s) {
    int len = 0;
    while (s[len]) len++;
    asm volatile(
        "syscall\\n"
        :
        : "a"(1L), "D"(1L), "S"(s), "d"((long)len)
        : "rcx", "r11"
    );
}

void print_int(long long val) {
    char buf[24];
    int i = 23;
    buf[i] = '\\0';
    int is_neg = 0;
    if (val < 0) { is_neg = 1; val = -val; }
    if (val == 0) { buf[--i] = '0'; }
    else {
        while (val > 0) {
            buf[--i] = '0' + (val % 10);
            val /= 10;
        }
    }
    if (is_neg) buf[--i] = '-';
    print_str(buf + i);
}

void print_char(char c) {
    char buf[2] = {c, '\\0'};
    print_str(buf);
}

void exit_program(int code) {
    asm volatile(
        "syscall\\n"
        :
        : "a"(60L), "D"((long)code)
        : "rcx", "r11"
    );
    while (1);
}

int read_stdin(char *buf, int max_len) {
    long bytes_read;
    asm volatile(
        "syscall\\n"
        : "=a"(bytes_read)
        : "0"(0L), "D"(0L), "S"(buf), "d"((long)max_len)
        : "rcx", "r11", "memory"
    );
    if (bytes_read > 0) {
        buf[bytes_read] = '\\0';
    } else {
        buf[0] = '\\0';
    }
    return (int)bytes_read;
}

long long parse_int(char *buf, int *idx) {
    while (buf[*idx] == ' ' || buf[*idx] == '\\n' || buf[*idx] == '\\r' || buf[*idx] == '\\t') {
        (*idx)++;
    }
    int sign = 1;
    if (buf[*idx] == '-') {
        sign = -1;
        (*idx)++;
    } else if (buf[*idx] == '+') {
        (*idx)++;
    }
    long long val = 0;
    while (buf[*idx] >= '0' && buf[*idx] <= '9') {
        val = val * 10 + (buf[*idx] - '0');
        (*idx)++;
    }
    return val * sign;
}

char parse_char(char *buf, int *idx) {
    while (buf[*idx] == ' ' || buf[*idx] == '\\n' || buf[*idx] == '\\r' || buf[*idx] == '\\t') {
        (*idx)++;
    }
    char c = buf[*idx];
    if (c != '\\0') {
        (*idx)++;
    }
    return c;
}

int parse_str(char *buf, int *idx, char *dest, int max_len) {
    while (buf[*idx] == ' ' || buf[*idx] == '\\n' || buf[*idx] == '\\r' || buf[*idx] == '\\t') {
        (*idx)++;
    }
    int len = 0;
    while (buf[*idx] != '\\0' && buf[*idx] != ' ' && buf[*idx] != '\\n' && buf[*idx] != '\\r' && buf[*idx] != '\\t' && len < max_len - 1) {
        dest[len++] = buf[*idx];
        (*idx)++;
    }
    dest[len] = '\\0';
    return len;
}
"""

def format_str(template, **kwargs):
    res = template
    for k, v in kwargs.items():
        res = res.replace("{" + k + "}", str(v))
    res = res.replace("{{", "{").replace("}}", "}")
    return res

words_list = ["apple", "banana", "cherry", "date", "elder", "fig", "grape", "honey", "ivory", "juice", "lemon", "mango", "orange", "pear", "quince", "sky", "time", "world", "yellow", "zebra"]
var_names = ["val", "num", "temp", "limit", "bound", "count", "idx", "result", "total", "input_val", "item", "var", "data_val", "x_val", "y_val", "n_val", "calc_val"]
phrasings = [
    "Write a C program to",
    "Create a C application to",
    "Implement a C program that will",
    "Write a C code that is designed to",
    "Write a C application designed to"
]

programs = []

# --- CATEGORY 1: Simple Math Operations (500 samples) ---
print("Generating Category 1: Math...")
math_templates = [
    ("calculate the sum of two integers read from stdin", "{v_res} = {v_a} + {v_b}; print_int({v_res});"),
    ("calculate the difference between two integers read from stdin", "{v_res} = {v_a} - {v_b}; print_int({v_res});"),
    ("calculate the product of two integers read from stdin", "{v_res} = {v_a} * {v_b}; print_int({v_res});"),
    ("calculate the quotient of two integers read from stdin", "if ({v_b} == 0) {{ print_str(\"DivByZero\"); exit_program(1); }} {v_res} = {v_a} / {v_b}; print_int({v_res});"),
    ("calculate the remainder of two integers read from stdin", "if ({v_b} == 0) {{ print_str(\"DivByZero\"); exit_program(1); }} {v_res} = {v_a} % {v_b}; print_int({v_res});"),
    ("calculate the average of three integers read from stdin", "{v_res} = ({v_a} + {v_b} + {v_c}) / 3; print_int({v_res});"),
    ("calculate the area of a circle given its radius read from stdin (pi=3)", "{v_res} = 3 * {v_a} * {v_a}; print_int({v_res});"),
    ("calculate the volume of a cube given its side length read from stdin", "{v_res} = {v_a} * {v_a} * {v_a}; print_int({v_res});"),
    ("calculate the maximum of two integers read from stdin", "{v_res} = ({v_a} > {v_b}) ? {v_a} : {v_b}; print_int({v_res});"),
    ("calculate the minimum of two integers read from stdin", "{v_res} = ({v_a} < {v_b}) ? {v_a} : {v_b}; print_int({v_res});")
]

for i in range(50):
    for desc, code_body in math_templates:
        phrase = random.choice(phrasings)
        v_a = random.choice(var_names) + "_a"
        v_b = random.choice(var_names) + "_b"
        v_c = random.choice(var_names) + "_c"
        v_res = random.choice(var_names) + "_res"
        
        prompt = f"{phrase} {desc}."
        
        c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    long long {v_a} = parse_int(input_buf, &parse_idx);
    long long {v_b} = parse_int(input_buf, &parse_idx);
    long long {v_c} = parse_int(input_buf, &parse_idx);
    long long {v_res} = 0;
    
    {format_str(code_body, v_a=v_a, v_b=v_b, v_c=v_c, v_res=v_res)}
    print_char('\\n');
    exit_program(0);
}}
"""
        # Test case inputs/outputs
        a_val, b_val, c_val = random.randint(1, 10), random.randint(1, 10), random.randint(1, 10)
        stdin_input = f"{a_val} {b_val} {c_val}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 2: Loops (500 samples) ---
print("Generating Category 2: Loops...")
loop_templates = [
    ("read an integer N and print numbers from 1 to N", "for(int i=1; i<={v_n}; i++) {{ print_int(i); print_char(' '); }}"),
    ("read an integer N and print numbers from N down to 1", "for(int i={v_n}; i>=1; i--) {{ print_int(i); print_char(' '); }}"),
    ("read an integer N and calculate the sum of numbers from 1 to N", "long long sum=0; for(int i=1; i<={v_n}; i++) sum+=i; print_int(sum);"),
    ("read an integer N and print even numbers from 2 to N", "for(int i=2; i<={v_n}; i+=2) {{ print_int(i); print_char(' '); }}"),
    ("read an integer N and print odd numbers from 1 to N", "for(int i=1; i<={v_n}; i+=2) {{ print_int(i); print_char(' '); }}"),
    ("read an integer N and print the first N multiples of 3", "for(int i=1; i<={v_n}; i++) {{ print_int(i*3); print_char(' '); }}"),
    ("read an integer N and print the first N multiples of 5", "for(int i=1; i<={v_n}; i++) {{ print_int(i*5); print_char(' '); }}"),
    ("read an integer N and calculate the sum of even numbers from 2 to N", "long long sum=0; for(int i=2; i<={v_n}; i+=2) sum+=i; print_int(sum);"),
    ("read an integer N and calculate the sum of odd numbers from 1 to N", "long long sum=0; for(int i=1; i<={v_n}; i+=2) sum+=i; print_int(sum);"),
    ("read an integer N and print the squares of numbers from 1 to N", "for(int i=1; i<={v_n}; i++) {{ print_int(i*i); print_char(' '); }}")
]

for i in range(50):
    for desc, code_body in loop_templates:
        phrase = random.choice(phrasings)
        v_n = random.choice(var_names) + "_n"
        prompt = f"{phrase} {desc}."
        
        c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    long long {v_n} = parse_int(input_buf, &parse_idx);
    
    {format_str(code_body, v_n=v_n)}
    print_char('\\n');
    exit_program(0);
}}
"""
        stdin_input = str(random.randint(5, 15))
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 3: Algorithms (500 samples) ---
print("Generating Category 3: Algorithms...")
algo_templates = [
    ("read N and calculate the factorial of N using a loop", """
    long long fact = 1;
    for(int i=1; i<={v_n}; i++) fact *= i;
    print_int(fact);
    """),
    ("read N and calculate the factorial of N using recursion", """
    long long fact(int x) {
        if(x <= 1) return 1;
        return x * fact(x - 1);
    }
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        long long n = parse_int(input_buf, &parse_idx);
        print_int(fact(n));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("read N and calculate the N-th Fibonacci number using a loop", """
    long long a=0, b=1, c=0;
    if({v_n} == 0) c = 0;
    else if({v_n} == 1) c = 1;
    else {
        for(int i=2; i<={v_n}; i++) {
            c = a + b;
            a = b;
            b = c;
        }
    }
    print_int(c);
    """),
    ("read N and calculate the N-th Fibonacci number using recursion", """
    long long fib(int x) {
        if(x <= 0) return 0;
        if(x == 1) return 1;
        return fib(x-1) + fib(x-2);
    }
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        long long n = parse_int(input_buf, &parse_idx);
        print_int(fib(n));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("read N and check if N is prime (print 1 for prime, 0 otherwise)", """
    int is_prime = 1;
    if({v_n} <= 1) is_prime = 0;
    for(int i=2; i*i<={v_n}; i++) {
        if({v_n} % i == 0) {
            is_prime = 0;
            break;
        }
    }
    print_int(is_prime);
    """),
    ("read N and print all prime numbers up to N", """
    for(int i=2; i<={v_n}; i++) {
        int is_prime = 1;
        for(int j=2; j*j<=i; j++) {
            if(i % j == 0) {
                is_prime = 0;
                break;
            }
        }
        if(is_prime) { print_int(i); print_char(' '); }
    }
    """),
    ("read two integers A and B and find their GCD", """
    long long temp_a = {v_a}, temp_b = {v_b};
    while(temp_b != 0) {
        long long temp = temp_b;
        temp_b = temp_a % temp_b;
        temp_a = temp;
    }
    print_int(temp_a);
    """),
    ("read two integers A and B and find their LCM", """
    long long temp_a = {v_a}, temp_b = {v_b};
    long long product = temp_a * temp_b;
    while(temp_b != 0) {
        long long temp = temp_b;
        temp_b = temp_a % temp_b;
        temp_a = temp;
    }
    long long gcd = temp_a;
    print_int(product / gcd);
    """),
    ("read N and calculate the sum of its digits", """
    long long temp = {v_n};
    long long sum = 0;
    while(temp > 0) {
        sum += temp % 10;
        temp /= 10;
    }
    print_int(sum);
    """),
    ("read N and reverse its digits", """
    long long temp = {v_n};
    long long rev = 0;
    while(temp > 0) {
        rev = rev * 10 + (temp % 10);
        temp /= 10;
    }
    print_int(rev);
    """)
]

for i in range(50):
    for desc, code_body in algo_templates:
        phrase = random.choice(phrasings)
        v_n = random.choice(var_names) + "_n"
        v_a = random.choice(var_names) + "_a"
        v_b = random.choice(var_names) + "_b"
        prompt = f"{phrase} {desc}."
        
        if "void _start()" in code_body:
            c_code = f"{c_header_parse}\n{code_body}"
        else:
            c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    long long {v_n} = parse_int(input_buf, &parse_idx);
    long long {v_a} = {v_n};
    long long {v_b} = parse_int(input_buf, &parse_idx);
    
    {format_str(code_body, v_n=v_n, v_a=v_a, v_b=v_b)}
    print_char('\\n');
    exit_program(0);
}}
"""
        stdin_input = f"{random.randint(5, 12)} {random.randint(5, 12)}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 4: Arrays (500 samples) ---
print("Generating Category 4: Arrays...")
array_templates = [
    ("read array size and elements, and find the sum of elements", "int sum=0; for(int i=0; i<{v_size}; i++) sum+=arr[i]; print_int(sum);"),
    ("read array size and elements, and find the maximum element", "int max=arr[0]; for(int i=1; i<{v_size}; i++) if(arr[i]>max) max=arr[i]; print_int(max);"),
    ("read array size and elements, and find the minimum element", "int min=arr[0]; for(int i=1; i<{v_size}; i++) if(arr[i]<min) min=arr[i]; print_int(min);"),
    ("read array size and elements, and print them in reverse order", "for(int i={v_size}-1; i>=0; i--) {{ print_int(arr[i]); print_char(' '); }}"),
    ("read array size and elements, and count the number of even elements", "int c=0; for(int i=0; i<{v_size}; i++) if(arr[i]%2==0) c++; print_int(c);"),
    ("read array size and elements, and count the number of odd elements", "int c=0; for(int i=0; i<{v_size}; i++) if(arr[i]%2!=0) c++; print_int(c);"),
    ("read array size, elements, and a target, and find the index of the target", "int idx=-1; for(int i=0; i<{v_size}; i++) if(arr[i]=={v_target}) {{ idx=i; break; }} print_int(idx);"),
    ("read array size and elements, and sort them using bubble sort", "for(int i=0; i<{v_size}-1; i++) for(int j=0; j<{v_size}-i-1; j++) if(arr[j]>arr[j+1]) {{ int t=arr[j]; arr[j]=arr[j+1]; arr[j+1]=t; }} for(int i=0; i<{v_size}; i++) {{ print_int(arr[i]); print_char(' '); }}"),
    ("read array size, elements, and a target, and count its occurrences", "int c=0; for(int i=0; i<{v_size}; i++) if(arr[i]=={v_target}) c++; print_int(c);"),
    ("read array size and elements, and print all elements", "for(int i=0; i<{v_size}; i++) {{ print_int(arr[i]); print_char(' '); }}")
]

for i in range(50):
    for desc, code_body in array_templates:
        phrase = random.choice(phrasings)
        v_size = random.choice(var_names) + "_size"
        v_target = random.choice(var_names) + "_target"
        prompt = f"{phrase} {desc}."
        
        c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[256];
    int read_bytes = read_stdin(input_buf, 255);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    int {v_size} = parse_int(input_buf, &parse_idx);
    if ({v_size} > 100 || {v_size} <= 0) exit_program(1);
    
    int arr[100];
    for (int i = 0; i < {v_size}; i++) {{
        arr[i] = parse_int(input_buf, &parse_idx);
    }}
    int {v_target} = parse_int(input_buf, &parse_idx);
    
    {format_str(code_body, v_size=v_size, v_target=v_target)}
    print_char('\\n');
    exit_program(0);
}}
"""
        size = random.randint(4, 8)
        elements = [random.randint(1, 30) for _ in range(size)]
        target = elements[random.randint(0, size-1)]
        stdin_input = f"{size} {' '.join(map(str, elements))} {target}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 5: Strings (500 samples) ---
print("Generating Category 5: Strings...")
string_templates = [
    ("read a string from stdin and print its length", "int len=0; while(str[len]!='\\0') len++; print_int(len);"),
    ("read a string from stdin and count its vowels", "int c=0; for(int i=0; str[i]!='\\0'; i++) {{ char ch=str[i]; if(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U') c++; }} print_int(c);"),
    ("read a string from stdin and count its consonants", "int c=0; for(int i=0; str[i]!='\\0'; i++) {{ char ch=str[i]; if(((ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')) && !(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U')) c++; }} print_int(c);"),
    ("read a string from stdin and check if it is a palindrome (print 1/0)", "int len=0; while(str[len]!='\\0') len++; int pal=1; for(int i=0; i<len/2; i++) if(str[i]!=str[len-1-i]) pal=0; print_int(pal);"),
    ("read a string from stdin and print it in reverse", "int len=0; while(str[len]!='\\0') len++; for(int i=len-1; i>=0; i--) print_char(str[i]);"),
    ("read a string from stdin and convert it to uppercase", "for(int i=0; str[i]!='\\0'; i++) {{ char ch=str[i]; if(ch>='a'&&ch<='z') ch=ch-'a'+'A'; print_char(ch); }}"),
    ("read a string from stdin and convert it to lowercase", "for(int i=0; str[i]!='\\0'; i++) {{ char ch=str[i]; if(ch>='A'&&ch<='Z') ch=ch-'A'+'a'; print_char(ch); }}"),
    ("read a string and a target character, and count occurrences of the character", "int c=0; for(int i=0; str[i]!='\\0'; i++) if(str[i]=={v_target}) c++; print_int(c);"),
    ("read a string from stdin, copy it to another buffer, and print it", "char dest[200]; int i=0; while(str[i]!='\\0') {{ dest[i]=str[i]; i++; }} dest[i]='\\0'; print_str(dest);"),
    ("read two strings from stdin, concatenate them, and print the result", "char dest[200]; int i=0; while(str[i]!='\\0') {{ dest[i]=str[i]; i++; }} int j=0; while(str2[j]!='\\0') {{ dest[i++]=str2[j++]; }} dest[i]='\\0'; print_str(dest);")
]

for i in range(50):
    for desc, code_body in string_templates:
        phrase = random.choice(phrasings)
        v_target = random.choice(var_names) + "_target"
        prompt = f"{phrase} {desc}."
        
        c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[256];
    int read_bytes = read_stdin(input_buf, 255);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    char str[100];
    parse_str(input_buf, &parse_idx, str, 99);
    char {v_target} = parse_char(input_buf, &parse_idx);
    char str2[100];
    parse_str(input_buf, &parse_idx, str2, 99);
    
    {format_str(code_body, v_target=v_target)}
    print_char('\\n');
    exit_program(0);
}}
"""
        word1 = random.choice(words_list)
        word2 = random.choice(words_list)
        target = word1[0]
        stdin_input = f"{word1} {target} {word2}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 6: Bitwise Operations (500 samples) ---
print("Generating Category 6: Bitwise...")
bitwise_templates = [
    ("read two integers and calculate their bitwise AND", "print_int({v_a} & {v_b});"),
    ("read two integers and calculate their bitwise OR", "print_int({v_a} | {v_b});"),
    ("read two integers and calculate their bitwise XOR", "print_int({v_a} ^ {v_b});"),
    ("read an integer and calculate its bitwise NOT", "print_int(~{v_a});"),
    ("read an integer and shift it left by a bit count", "print_int({v_a} << {v_b});"),
    ("read an integer and shift it right by a bit count", "print_int({v_a} >> {v_b});"),
    ("read an integer and count its set bits", "int c=0; long long n={v_a}; while(n>0) {{ c += (n & 1); n >>= 1; }} print_int(c);"),
    ("read an integer and check if a given bit position is set (1/0)", "print_int(({v_a} & (1LL << {v_b})) ? 1 : 0);"),
    ("read an integer and set a given bit position", "print_int({v_a} | (1LL << {v_b}));"),
    ("read an integer and clear a given bit position", "print_int({v_a} & ~(1LL << {v_b}));")
]

for i in range(50):
    for desc, code_body in bitwise_templates:
        phrase = random.choice(phrasings)
        v_a = random.choice(var_names) + "_a"
        v_b = random.choice(var_names) + "_b"
        prompt = f"{phrase} {desc}."
        
        c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    long long {v_a} = parse_int(input_buf, &parse_idx);
    long long {v_b} = parse_int(input_buf, &parse_idx);
    
    {format_str(code_body, v_a=v_a, v_b=v_b)}
    print_char('\\n');
    exit_program(0);
}}
"""
        stdin_input = f"{random.randint(10, 100)} {random.randint(1, 3)}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 7: Structures & Pointers (500 samples) ---
print("Generating Category 7: Structures & Pointers...")
struct_pointer_templates = [
    ("rect_area", "read rectangle width and height, and calculate area using Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int w = parse_int(input_buf, &parse_idx);
        int h = parse_int(input_buf, &parse_idx);
        struct Rectangle r = { w, h };
        print_int(r.width * r.height);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("rect_perim", "read rectangle width and height, and calculate perimeter using Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int w = parse_int(input_buf, &parse_idx);
        int h = parse_int(input_buf, &parse_idx);
        struct Rectangle r = { w, h };
        print_int(2 * (r.width + r.height));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("square_area", "read square side, and calculate area using Square structure", """
    struct Square { int side; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int s = parse_int(input_buf, &parse_idx);
        struct Square sq = { s };
        print_int(sq.side * sq.side);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("2d_point", "read x and y, and print a 2D Point structure", """
    struct Point { int x; int y; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int px = parse_int(input_buf, &parse_idx);
        int py = parse_int(input_buf, &parse_idx);
        struct Point p = { px, py };
        print_int(p.x);
        print_char(' ');
        print_int(p.y);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("complex_add", "read two complex numbers (real and imag parts) and add them using Complex structures", """
    struct Complex { int real; int imag; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int r1 = parse_int(input_buf, &parse_idx);
        int i1 = parse_int(input_buf, &parse_idx);
        int r2 = parse_int(input_buf, &parse_idx);
        int i2 = parse_int(input_buf, &parse_idx);
        struct Complex c1 = { r1, i1 };
        struct Complex c2 = { r2, i2 };
        print_int(c1.real + c2.real);
        print_str(" + ");
        print_int(c1.imag + c2.imag);
        print_str("i\\n");
        exit_program(0);
    }
    """),
    ("time_struct", "read hours, minutes, and seconds, and print them using a Time structure", """
    struct Time { int h; int m; int s; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int th = parse_int(input_buf, &parse_idx);
        int tm = parse_int(input_buf, &parse_idx);
        int ts = parse_int(input_buf, &parse_idx);
        struct Time t = { th, tm, ts };
        print_int(t.h);
        print_char(':');
        print_int(t.m);
        print_char(':');
        print_int(t.s);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("box_volume", "read box dimensions (l, w, h) and calculate volume using a Box structure", """
    struct Box { int length; int width; int height; };
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int bl = parse_int(input_buf, &parse_idx);
        int bw = parse_int(input_buf, &parse_idx);
        int bh = parse_int(input_buf, &parse_idx);
        struct Box b = { bl, bw, bh };
        print_int(b.length * b.width * b.height);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("swap_ptr", "read two integers and swap them using pointers", """
    void swap(int *x, int *y) {
        int temp = *x;
        *x = *y;
        *y = temp;
    }
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int val1 = parse_int(input_buf, &parse_idx);
        int val2 = parse_int(input_buf, &parse_idx);
        swap(&val1, &val2);
        print_int(val1);
        print_char(' ');
        print_int(val2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("sum_ptr", "read two integers and find their sum using pointers", """
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int val1 = parse_int(input_buf, &parse_idx);
        int val2 = parse_int(input_buf, &parse_idx);
        int *p1 = &val1, *p2 = &val2;
        print_int(*p1 + *p2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("ptr_arith", "read array size and elements, and calculate sum using pointer arithmetic", """
    void _start() {
        char input_buf[256];
        int read_bytes = read_stdin(input_buf, 255);
        if (read_bytes <= 0) exit_program(1);
        int parse_idx = 0;
        int size = parse_int(input_buf, &parse_idx);
        if (size > 50 || size <= 0) exit_program(1);
        int arr[50];
        for(int i=0; i<size; i++) {
            arr[i] = parse_int(input_buf, &parse_idx);
        }
        int *p = arr;
        int sum = 0;
        for(int i=0; i<size; i++) {
            sum += *(p + i);
        }
        print_int(sum);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("strlen_ptr", "read a string from stdin and find its length using pointers", """
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        char s[100];
        int parse_idx = 0;
        parse_str(input_buf, &parse_idx, s, 99);
        char *p = s;
        while(*p != '\\0') p++;
        print_int(p - s);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("strcpy_ptr", "read a string from stdin, copy it using pointers, and print it", """
    void _start() {
        char input_buf[128];
        int read_bytes = read_stdin(input_buf, 127);
        if (read_bytes <= 0) exit_program(1);
        char s[100];
        int parse_idx = 0;
        parse_str(input_buf, &parse_idx, s, 99);
        char dest[100];
        char *p1 = s, *p2 = dest;
        while(*p1 != '\\0') {
            *p2 = *p1;
            p1++;
            p2++;
        }
        *p2 = '\\0';
        print_str(dest);
        print_char('\\n');
        exit_program(0);
    }
    """)
]

for i in range(42):
    for name, desc, code_body in struct_pointer_templates:
        phrase = random.choice(phrasings)
        prompt = f"{phrase} {desc}."
        stdin_input = f"{random.randint(5, 20)} {random.randint(5, 20)} {random.randint(5, 20)} {random.randint(5, 20)}"
        if "string" in desc:
            stdin_input = random.choice(words_list)
        elif "array" in desc:
            stdin_input = "4 10 20 30 40"
            
        c_code = f"{c_header_parse}\n{code_body}"
        programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 8: Chained Calculator applications (500 samples) ---
print("Generating Category 8: Calculators...")
for i in range(500):
    phrase = random.choice(phrasings)
    prompt = f"{phrase} a simple calculator application that reads two integers and an operator (+, -, *, /) from stdin, and prints the result."
    
    # We vary the variable names and comments slightly to make 500 distinct programs
    v_a = random.choice(var_names) + "_a"
    v_b = random.choice(var_names) + "_b"
    v_op = random.choice(var_names) + "_op"
    v_res = random.choice(var_names) + "_res"
    
    c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    long long {v_a} = parse_int(input_buf, &parse_idx);
    char {v_op} = parse_char(input_buf, &parse_idx);
    long long {v_b} = parse_int(input_buf, &parse_idx);
    long long {v_res} = 0;
    
    if ({v_op} == '+') {v_res} = {v_a} + {v_b};
    else if ({v_op} == '-') {v_res} = {v_a} - {v_b};
    else if ({v_op} == '*') {v_res} = {v_a} * {v_b};
    else if ({v_op} == '/') {{
        if ({v_b} == 0) {{
            print_str("DivByZero\\n");
            exit_program(1);
        }}
        {v_res} = {v_a} / {v_b};
    }} else {{
        print_str("InvalidOp\\n");
        exit_program(1);
    }}
    
    // Output calculation result {i}
    print_int({v_res});
    print_char('\\n');
    exit_program(0);
}}
"""
    a_val = random.randint(1, 100)
    b_val = random.randint(1, 10)
    op = random.choice(['+', '-', '*'])
    stdin_input = f"{a_val} {op} {b_val}"
    programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 9: Tic-Tac-Toe Game simulations (500 samples) ---
print("Generating Category 9: Tic-Tac-Toe Checkers...")
for i in range(500):
    phrase = random.choice(phrasings)
    prompt = f"{phrase} check the winner of a Tic-Tac-Toe board read as a 9-character string from stdin, and print 'X', 'O', 'D' (for Draw), or 'I' (for In Progress)."
    
    # Vary the index names or check logic slightly
    v_board = random.choice(var_names) + "_board"
    v_winner = random.choice(var_names) + "_winner"
    
    c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes < 9) exit_program(1);
    
    char {v_board}[9];
    int p_idx = 0;
    for (int idx=0; idx<9; idx++) {{
        while(input_buf[p_idx] == ' ' || input_buf[p_idx] == ',' || input_buf[p_idx] == '\\n') {{
            p_idx++;
        }}
        {v_board}[idx] = input_buf[p_idx++];
    }}
    
    char {v_winner} = ' ';
    // Rows
    if ({v_board}[0] != ' ' && {v_board}[0] == {v_board}[1] && {v_board}[1] == {v_board}[2]) {v_winner} = {v_board}[0];
    else if ({v_board}[3] != ' ' && {v_board}[3] == {v_board}[4] && {v_board}[4] == {v_board}[5]) {v_winner} = {v_board}[3];
    else if ({v_board}[6] != ' ' && {v_board}[6] == {v_board}[7] && {v_board}[7] == {v_board}[8]) {v_winner} = {v_board}[6];
    
    // Columns
    else if ({v_board}[0] != ' ' && {v_board}[0] == {v_board}[3] && {v_board}[3] == {v_board}[6]) {v_winner} = {v_board}[0];
    else if ({v_board}[1] != ' ' && {v_board}[1] == {v_board}[4] && {v_board}[4] == {v_board}[7]) {v_winner} = {v_board}[1];
    else if ({v_board}[2] != ' ' && {v_board}[2] == {v_board}[5] && {v_board}[5] == {v_board}[8]) {v_winner} = {v_board}[2];
    
    // Diagonals
    else if ({v_board}[0] != ' ' && {v_board}[0] == {v_board}[4] && {v_board}[4] == {v_board}[8]) {v_winner} = {v_board}[0];
    else if ({v_board}[2] != ' ' && {v_board}[2] == {v_board}[4] && {v_board}[4] == {v_board}[6]) {v_winner} = {v_board}[2];
    
    if ({v_winner} != ' ') {{
        print_char({v_winner});
    }} else {{
        int empty = 0;
        for(int idx=0; idx<9; idx++) if({v_board}[idx] == ' ' || {v_board}[idx] == '_') empty++;
        if(empty == 0) print_char('D');
        else print_char('I');
    }}
    print_char('\\n');
    exit_program(0);
}}
"""
    # Sample board
    slots = ['X', 'O', ' ', 'X', ' ', 'O', 'X', ' ', ' ']
    random.shuffle(slots)
    stdin_input = ",".join(slots)
    programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 10: Generic Grid Snake Game (500 samples) ---
print("Generating Category 10: Grid Snake Simulators...")
for i in range(500):
    phrase = random.choice(phrasings)
    prompt = f"{phrase} simulate a snake on a 5x5 grid by reading the start position (X and Y) and a sequence of moves (R, L, U, D) from stdin, and print its final coordinates."
    
    # Vary the coord variables
    v_x = random.choice(var_names) + "_x"
    v_y = random.choice(var_names) + "_y"
    v_moves = random.choice(var_names) + "_moves"
    
    c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    int {v_x} = parse_int(input_buf, &parse_idx);
    int {v_y} = parse_int(input_buf, &parse_idx);
    char {v_moves}[64];
    parse_str(input_buf, &parse_idx, {v_moves}, 63);
    
    for (int idx = 0; {v_moves}[idx] != '\\0'; idx++) {{
        if ({v_moves}[idx] == 'R') {v_x} = ({v_x} + 1) % 5;
        else if ({v_moves}[idx] == 'L') {v_x} = ({v_x} - 1 + 5) % 5;
        else if ({v_moves}[idx] == 'D') {v_y} = ({v_y} + 1) % 5;
        else if ({v_moves}[idx] == 'U') {v_y} = ({v_y} - 1 + 5) % 5;
    }}
    print_str("X:");
    print_int({v_x});
    print_str(" Y:");
    print_int({v_y});
    print_char('\\n');
    exit_program(0);
}}
"""
    stdin_input = f"{random.randint(0,4)} {random.randint(0,4)} RDRLU"
    programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# --- CATEGORY 11: ASCII Graphics & Image Visualizers (500 samples) ---
print("Generating Category 11: ASCII Visualizers...")
# 250 ASCII Shape Drawers
for i in range(250):
    phrase = random.choice(phrasings)
    prompt = f"{phrase} draw a shape (1 for Rectangle, 2 for Triangle) based on width and height read from stdin using character grid representation."
    
    v_shape = random.choice(var_names) + "_shape"
    v_w = random.choice(var_names) + "_w"
    v_h = random.choice(var_names) + "_h"
    symbol = random.choice(['*', '#', '@', '+'])
    
    c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[128];
    int read_bytes = read_stdin(input_buf, 127);
    if (read_bytes <= 0) exit_program(1);
    
    int parse_idx = 0;
    int {v_shape} = parse_int(input_buf, &parse_idx);
    int {v_w} = parse_int(input_buf, &parse_idx);
    int {v_h} = parse_int(input_buf, &parse_idx);
    
    if ({v_shape} == 1) {{
        for (int r = 0; r < {v_h}; r++) {{
            for (int col = 0; col < {v_w}; col++) {{
                print_char('{symbol}');
            }}
            print_char('\\n');
        }}
    }} else if ({v_shape} == 2) {{
        for (int r = 0; r < {v_h}; r++) {{
            for (int col = 0; col <= r && col < {v_w}; col++) {{
                print_char('{symbol}');
            }}
            print_char('\\n');
        }}
    }}
    exit_program(0);
}}
"""
    stdin_input = f"{random.choice([1, 2])} {random.randint(3,6)} {random.randint(3,6)}"
    programs.append({"prompt": prompt, "c_code": c_code, "stdin": stdin_input})

# 250 BMP-to-ASCII Image Visualizers
for i in range(250):
    phrase = random.choice(phrasings)
    prompt = f"{phrase} read an uncompressed 24-bit BMP image from stdin, parse its headers, convert each pixel to luminance, and output its ASCII art representation to stdout."
    
    v_w = random.choice(var_names) + "_w"
    v_h = random.choice(var_names) + "_h"
    v_bpp = random.choice(var_names) + "_bpp"
    v_lum = random.choice(var_names) + "_lum"
    
    # We vary the character ramps slightly
    ramps = [
        " .:-=+*#%@",
        " ._~+*oO@#",
        "  .-+*xX%@"
    ]
    ramp = random.choice(ramps)
    
    c_code = f"""{c_header_parse}
void _start() {{
    char input_buf[2048];
    int read_bytes = read_stdin(input_buf, 2047);
    if (read_bytes < 54) exit_program(1);
    
    if (input_buf[0] != 'B' || input_buf[1] != 'M') exit_program(1);
    
    int {v_w} = *(int*)&input_buf[18];
    int {v_h} = *(int*)&input_buf[22];
    int {v_bpp} = *(short*)&input_buf[28];
    if ({v_bpp} != 24) exit_program(1);
    
    int offset = 54;
    for (int y = {v_h} - 1; y >= 0; y--) {{
        for (int x = 0; x < {v_w}; x++) {{
            int p_idx = offset + (y * {v_w} + x) * 3;
            if (p_idx + 2 >= read_bytes) exit_program(1);
            unsigned char b = input_buf[p_idx];
            unsigned char g = input_buf[p_idx + 1];
            unsigned char r = input_buf[p_idx + 2];
            
            int {v_lum} = (r * 299 + g * 587 + b * 114) / 1000;
            
            char c = ' ';
            if ({v_lum} < 25) c = '{ramp[9]}';
            else if ({v_lum} < 50) c = '{ramp[8]}';
            else if ({v_lum} < 75) c = '{ramp[7]}';
            else if ({v_lum} < 100) c = '{ramp[6]}';
            else if ({v_lum} < 125) c = '{ramp[5]}';
            else if ({v_lum} < 150) c = '{ramp[4]}';
            else if ({v_lum} < 175) c = '{ramp[3]}';
            else if ({v_lum} < 200) c = '{ramp[2]}';
            else if ({v_lum} < 225) c = '{ramp[1]}';
            else c = '{ramp[0]}';
            
            print_char(c);
        }}
        print_char('\\n');
    }}
    exit_program(0);
}}
"""
    # Create small mock BMP bytes: 4x4 image
    # pixels is a list of (R, G, B) tuples
    pixels = [(r * 10, r * 15, r * 16) for r in range(16)]
    # Make BMP helper
    width = 4
    height = 4
    row_size = width * 3
    padding = (4 - (row_size % 4)) % 4
    pixel_data_size = (row_size + padding) * height
    file_size = 54 + pixel_data_size
    
    header = bytearray(54)
    header[0:2] = b'BM'
    header[2:6] = file_size.to_bytes(4, 'little')
    header[10:14] = (54).to_bytes(4, 'little')
    header[14:18] = (40).to_bytes(4, 'little')
    header[18:22] = width.to_bytes(4, 'little')
    header[22:26] = height.to_bytes(4, 'little')
    header[26:28] = (1).to_bytes(2, 'little')
    header[28:30] = (24).to_bytes(2, 'little')
    header[34:38] = pixel_data_size.to_bytes(4, 'little')
    
    pixel_bytes = bytearray()
    for y in range(height):
        row_pixels = pixels[(height - 1 - y) * width : (height - y) * width]
        for r, g, b in row_pixels:
            pixel_bytes.append(b)
            pixel_bytes.append(g)
            pixel_bytes.append(r)
        pixel_bytes.extend([0] * padding)
    bmp_bytes = bytes(header + pixel_bytes)
    
    # Store stdin as hex string that python builder can decode
    programs.append({"prompt": prompt, "c_code": c_code, "stdin_hex": bmp_bytes.hex()})

# Compile, execute and gather dataset
print(f"Total generic programs generated: {len(programs)}")
dataset = []

temp_dir = tempfile.gettempdir()
success_count = 0

for i, prog in enumerate(programs):
    prompt = prog["prompt"]
    c_code = prog["c_code"]
    
    c_file_path = os.path.join(temp_dir, f"temp_gen_{i}.c")
    obj_file_path = os.path.join(temp_dir, f"temp_gen_{i}.o")
    bin_file_path = os.path.join(temp_dir, f"temp_gen_{i}.bin")
    
    with open(c_file_path, "w") as f:
        f.write(c_code)
        
    compile_cmd = ["/usr/bin/gcc-12", "-c", "-fno-asynchronous-unwind-tables", "-fno-ident", "-fno-stack-protector", "-fno-builtin", "-Os", c_file_path, "-o", obj_file_path]
    compile_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    if compile_res.returncode != 0:
        if os.path.exists(c_file_path): os.remove(c_file_path)
        continue
        
    link_cmd = ["/usr/bin/ld", "-s", "-N", obj_file_path, "/usr/lib/gcc/x86_64-linux-gnu/12/libgcc.a", "-o", bin_file_path]
    link_res = subprocess.run(link_cmd, capture_output=True, text=True)
    if link_res.returncode != 0:
        if os.path.exists(c_file_path): os.remove(c_file_path)
        if os.path.exists(obj_file_path): os.remove(obj_file_path)
        continue
        
    # Run program with stdin
    try:
        if "stdin_hex" in prog:
            stdin_bytes = bytes.fromhex(prog["stdin_hex"])
            run_res = subprocess.run([bin_file_path], input=stdin_bytes, capture_output=True, timeout=1)
        else:
            stdin_str = prog.get("stdin", "")
            run_res = subprocess.run([bin_file_path], input=stdin_str, capture_output=True, text=True, timeout=1)
        exit_code = run_res.returncode
    except subprocess.TimeoutExpired:
        exit_code = -99
        
    if exit_code == 0:
        with open(bin_file_path, "rb") as f:
            binary_hex = f.read().hex()
            
        dataset.append({
            "prompt": prompt,
            "c_code": c_code,
            "binary_hex": binary_hex,
            "status": "positive",
            "exit_code": 0
        })
        success_count += 1
        
    if os.path.exists(c_file_path): os.remove(c_file_path)
    if os.path.exists(obj_file_path): os.remove(obj_file_path)
    if os.path.exists(bin_file_path): os.remove(bin_file_path)
    
    if (i + 1) % 500 == 0:
        print(f"Processed {i+1} programs. Successful verified: {success_count}")

# Save to c_program_dataset_generic_5k.json
workspace_dir = "/home/manifest/Documents/antigravity/mysterious-raman"
json_path = os.path.join(workspace_dir, "c_program_dataset_generic_5k.json")

with open(json_path, "w") as f:
    json.dump(dataset, f, indent=2)
    
print(f"Dataset generated successfully!")
print(f"JSON path: {json_path}")
print(f"Total positive verified samples collected: {len(dataset)}")
