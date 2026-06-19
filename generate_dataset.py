import os
import subprocess
import tempfile
import json
import signal

# Tiny custom system-call header for -nostdlib compilation
c_header = """
#define NULL ((void*)0)

void print_str(char *s) {
    int len = 0;
    while (s[len]) len++;
    asm volatile(
        "mov $1, %%rax\\n"
        "mov $1, %%rdi\\n"
        "mov %0, %%rsi\\n"
        "mov %1, %%rdx\\n"
        "syscall\\n"
        :
        : "r"(s), "r"((long)len)
        : "rax", "rdi", "rsi", "rdx"
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
        "mov $60, %%rax\\n"
        "mov %0, %%rdi\\n"
        "syscall\\n"
        :
        : "r"((long)code)
        : "rax", "rdi"
    );
}
"""

def format_str(template, **kwargs):
    res = template
    for k, v in kwargs.items():
        res = res.replace("{" + k + "}", str(v))
    res = res.replace("{{", "{").replace("}}", "}")
    return res

programs = []

# --- CATEGORY 1: Simple Math Operations (10 Positive) ---
math_ops = [
    ("+", "sum of {a} and {b}", "print_int({a} + {b});"),
    ("-", "difference between {a} and {b}", "print_int({a} - {b});"),
    ("*", "product of {a} and {b}", "print_int({a} * {b});"),
    ("/", "quotient of {a} divided by {b}", "print_int({a} / {b});"),
    ("%", "remainder of {a} divided by {b}", "print_int({a} % {b});"),
    ("average", "average of three numbers: {a}, {b}, and {c}", "print_int(({a} + {b} + {c}) / 3);"),
    ("circle", "area of a circle with radius {a} (using pi=3 approximation)", "print_int(3 * {a} * {a});"),
    ("cube", "volume of a cube with side length {a}", "print_int({a} * {a} * {a});"),
    ("max", "maximum of two numbers {a} and {b}", "print_int(({a} > {b}) ? {a} : {b});"),
    ("min", "minimum of two numbers {a} and {b}", "print_int(({a} < {b}) ? {a} : {b});")
]

for idx, (op_name, desc, code_body) in enumerate(math_ops):
    a = (idx + 1) * 7
    b = (idx + 1) * 3
    c = (idx + 1) * 5
    prompt = f"Write a C program to calculate the {format_str(desc, a=a, b=b, c=c)}."
    c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, a=a, b=b, c=c)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 2: Loops (10 Positive) ---
loop_types = [
    ("print 1 to N", "print numbers from 1 to {n}", "for(int i=1; i<={n}; i++) { print_int(i); print_char(' '); }"),
    ("print N down to 1", "print numbers from {n} down to 1", "for(int i={n}; i>=1; i--) { print_int(i); print_char(' '); }"),
    ("sum 1 to N", "calculate the sum of numbers from 1 to {n}", "int sum=0; for(int i=1; i<={n}; i++) sum+=i; print_int(sum);"),
    ("print even", "print even numbers from 2 to {n}", "for(int i=2; i<={n}; i+=2) { print_int(i); print_char(' '); }"),
    ("print odd", "print odd numbers from 1 to {n}", "for(int i=1; i<={n}; i+=2) { print_int(i); print_char(' '); }"),
    ("multiples of 3", "print the first {n} multiples of 3", "for(int i=1; i<={n}; i++) { print_int(i*3); print_char(' '); }"),
    ("multiples of 5", "print the first {n} multiples of 5", "for(int i=1; i<={n}; i++) { print_int(i*5); print_char(' '); }"),
    ("sum even", "calculate the sum of even numbers from 2 to {n}", "int sum=0; for(int i=2; i<={n}; i+=2) sum+=i; print_int(sum);"),
    ("sum odd", "calculate the sum of odd numbers from 1 to {n}", "int sum=0; for(int i=1; i<={n}; i+=2) sum+=i; print_int(sum);"),
    ("squares", "print the squares of numbers from 1 to {n}", "for(int i=1; i<={n}; i++) { print_int(i*i); print_char(' '); }")
]

for idx, (name, desc, code_body) in enumerate(loop_types):
    n = (idx + 1) * 4
    prompt = f"Write a C program to {format_str(desc, n=n)}."
    c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, n=n)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 3: Factorial and Fibonacci (10 Positive) ---
algorithms = [
    ("factorial loop", "calculate the factorial of {n} using a loop", """
    int n = {n};
    long long fact = 1;
    for(int i=1; i<=n; i++) fact *= i;
    print_int(fact);
    """),
    ("factorial recursion", "calculate the factorial of {n} using recursion", """
    long long fact(int x) {
        if(x <= 1) return 1;
        return x * fact(x - 1);
    }
    void _start() {
        print_int(fact({n}));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("fibonacci loop", "calculate the {n}-th Fibonacci number using a loop", """
    int n = {n};
    long long a=0, b=1, c=0;
    if(n == 0) c = 0;
    else if(n == 1) c = 1;
    else {
        for(int i=2; i<=n; i++) {
            c = a + b;
            a = b;
            b = c;
        }
    }
    print_int(c);
    """),
    ("fibonacci recursion", "calculate the {n}-th Fibonacci number using recursion", """
    long long fib(int x) {
        if(x <= 0) return 0;
        if(x == 1) return 1;
        return fib(x-1) + fib(x-2);
    }
    void _start() {
        print_int(fib({n}));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("check prime", "check if {n} is prime (print 1 for prime, 0 otherwise)", """
    int n = {n};
    int is_prime = 1;
    if(n <= 1) is_prime = 0;
    for(int i=2; i*i<=n; i++) {
        if(n % i == 0) {
            is_prime = 0;
            break;
        }
    }
    print_int(is_prime);
    """),
    ("print primes up to N", "print prime numbers up to {n}", """
    int n = {n};
    for(int i=2; i<=n; i++) {
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
    ("gcd", "find the GCD of {a} and {b}", """
    int a = {a}, b = {b};
    while(b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    print_int(a);
    """),
    ("lcm", "find the LCM of {a} and {b}", """
    int a = {a}, b = {b};
    int temp_a = a, temp_b = b;
    while(temp_b != 0) {
        int temp = temp_b;
        temp_b = temp_a % temp_b;
        temp_a = temp;
    }
    int gcd = temp_a;
    print_int((a * b) / gcd);
    """),
    ("sum digits", "calculate the sum of the digits of {n}", """
    int n = {n};
    int sum = 0;
    while(n > 0) {
        sum += n % 10;
        n /= 10;
    }
    print_int(sum);
    """),
    ("reverse digits", "reverse the digits of the number {n}", """
    int n = {n};
    int rev = 0;
    while(n > 0) {
        rev = rev * 10 + (n % 10);
        n /= 10;
    }
    print_int(rev);
    """)
]

for idx, (name, desc, code_body) in enumerate(algorithms):
    n = (idx + 1) * 3 + 2
    a = (idx + 2) * 4
    b = (idx + 3) * 6
    prompt = f"Write a C program to {format_str(desc, n=n, a=a, b=b)}."
    
    if "void _start()" in code_body:
        c_code = f"{c_header}\n{format_str(code_body, n=n, a=a, b=b)}"
    else:
        c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, n=n, a=a, b=b)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 4: Arrays (10 Positive) ---
array_cases = [
    ("sum", "find the sum of elements in the array: {arr_str}", "int sum=0; for(int i=0; i<{size}; i++) sum+=arr[i]; print_int(sum);"),
    ("max", "find the maximum element in the array: {arr_str}", "int max=arr[0]; for(int i=1; i<{size}; i++) if(arr[i]>max) max=arr[i]; print_int(max);"),
    ("min", "find the minimum element in the array: {arr_str}", "int min=arr[0]; for(int i=1; i<{size}; i++) if(arr[i]<min) min=arr[i]; print_int(min);"),
    ("reverse", "reverse the array: {arr_str}", "for(int i={size}-1; i>=0; i--) { print_int(arr[i]); print_char(' '); }"),
    ("even count", "count the number of even elements in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]%2==0) c++; print_int(c);"),
    ("odd count", "count the number of odd elements in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]%2!=0) c++; print_int(c);"),
    ("find index", "find the index of the element {target} in the array: {arr_str}", "int idx=-1; for(int i=0; i<{size}; i++) if(arr[i]=={target}) { idx=i; break; } print_int(idx);"),
    ("bubble sort", "sort the array using bubble sort: {arr_str}", "for(int i=0; i<{size}-1; i++) for(int j=0; j<{size}-i-1; j++) if(arr[j]>arr[j+1]) { int t=arr[j]; arr[j]=arr[j+1]; arr[j+1]=t; } for(int i=0; i<{size}; i++) { print_int(arr[i]); print_char(' '); }"),
    ("occurrences", "count the occurrences of {target} in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]=={target}) c++; print_int(c);"),
    ("print all", "print all elements in the array: {arr_str}", "for(int i=0; i<{size}; i++) { print_int(arr[i]); print_char(' '); }")
]

for idx, (name, desc, code_body) in enumerate(array_cases):
    arr_values = [((idx + i) * 3) % 20 for i in range(5)]
    arr_str = ", ".join(map(str, arr_values))
    target = arr_values[2]
    size = len(arr_values)
    
    prompt = f"Write a C program to {format_str(desc, arr_str=f'{{{arr_str}}}', target=target)}."
    c_code = f"""{c_header}
void _start() {{
    int arr[] = {{{arr_str}}};
    {format_str(code_body, size=size, target=target)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 5: Strings (10 Positive) ---
strings_data = [
    ("hello", "hello"), ("world", "world"), ("programming", "programming"), 
    ("radar", "radar"), ("racecar", "racecar"), ("cprogramming", "cprogramming"),
    ("apple", "apple"), ("banana", "banana"), ("sky", "sky"), ("level", "level")
]

string_cases = [
    ("len", "calculate the length of the string \"{s}\"", "int len=0; while(str[len]!='\\0') len++; print_int(len);"),
    ("vowels", "count the number of vowels in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U') c++; } print_int(c);"),
    ("consonants", "count the number of consonants in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(((ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')) && !(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U')) c++; } print_int(c);"),
    ("palindrome", "check if the string \"{s}\" is a palindrome (print 1 for yes, 0 otherwise)", "int len=0; while(str[len]!='\\0') len++; int pal=1; for(int i=0; i<len/2; i++) if(str[i]!=str[len-1-i]) pal=0; print_int(pal);"),
    ("reverse", "reverse the string \"{s}\"", "int len=0; while(str[len]!='\\0') len++; for(int i=len-1; i>=0; i--) print_char(str[i]);"),
    ("upper", "convert the string \"{s}\" to uppercase", "for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch>='a'&&ch<='z') ch=ch-'a'+'A'; print_char(ch); }"),
    ("lower", "convert the string \"{s}\" to lowercase (with original input \"{s_upper}\")", "for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch>='A'&&ch<='Z') ch=ch-'A'+'a'; print_char(ch); }"),
    ("charcount", "print the character count of '{target_char}' in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) if(str[i]=='{target_char}') c++; print_int(c);"),
    ("copy", "copy the string \"{s}\" to another buffer and print it", "char dest[100]; int i=0; while(str[i]!='\\0') { dest[i]=str[i]; i++; } dest[i]='\\0'; print_str(dest);"),
    ("concat", "concatenate \"{s}\" and \"123\" and print the result", "char dest[100]; int i=0; while(str[i]!='\\0') { dest[i]=str[i]; i++; } dest[i++]='1'; dest[i++]='2'; dest[i++]='3'; dest[i]='\\0'; print_str(dest);")
]

for idx, (name, desc, code_body) in enumerate(string_cases):
    s = strings_data[idx][0]
    s_upper = s.upper()
    target_char = 'r' if 'r' in s else ('a' if 'a' in s else 'l')
    
    prompt = f"Write a C program to {format_str(desc, s=s, s_upper=s_upper, target_char=target_char)}."
    
    str_init = f"char str[] = \"{s_upper}\";" if name == "lower" else f"char str[] = \"{s}\";"
    c_code = f"""{c_header}
void _start() {{
    {str_init}
    {format_str(code_body, s=s, target_char=target_char)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 6: Structures (10 Positive) ---
struct_cases = [
    ("rect area", "calculate the area of a rectangle with width {w} and height {h} using a Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        struct Rectangle r = { {w}, {h} };
        print_int(r.width * r.height);
        print_char('\\n');
        exit_program(0);
    }
    """, {"w": 12, "h": 15}),
    ("rect perim", "calculate the perimeter of a rectangle with width {w} and height {h} using a Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        struct Rectangle r = { {w}, {h} };
        print_int(2 * (r.width + r.height));
        print_char('\\n');
        exit_program(0);
    }
    """, {"w": 18, "h": 24}),
    ("square area", "calculate the area of a square with side {s} using a Square structure", """
    struct Square { int side; };
    void _start() {
        struct Square sq = { {s} };
        print_int(sq.side * sq.side);
        print_char('\\n');
        exit_program(0);
    }
    """, {"s": 8}),
    ("2d point", "print a 2D Point structure with x={x} and y={y}", """
    struct Point { int x; int y; };
    void _start() {
        struct Point p = { {x}, {y} };
        print_int(p.x);
        print_char(' ');
        print_int(p.y);
        print_char('\\n');
        exit_program(0);
    }
    """, {"x": 5, "y": 10}),
    ("dist sq", "compute the distance squared between Point({x1},{y1}) and Point({x2},{y2}) using Point structures", """
    struct Point { int x; int y; };
    void _start() {
        struct Point p1 = { {x1}, {y1} };
        struct Point p2 = { {x2}, {y2} };
        int dx = p2.x - p1.x;
        int dy = p2.y - p1.y;
        print_int(dx*dx + dy*dy);
        print_char('\\n');
        exit_program(0);
    }
    """, {"x1": 2, "y1": 3, "x2": 6, "y2": 9}),
    ("student info", "print the details of a Student with id={id} and grade={grade} using a Student structure", """
    struct Student { int id; int grade; };
    void _start() {
        struct Student s = { {id}, {grade} };
        print_str("ID:");
        print_int(s.id);
        print_str(" Grade:");
        print_int(s.grade);
        print_char('\\n');
        exit_program(0);
    }
    """, {"id": 1001, "grade": 85}),
    ("complex add", "add two complex numbers ({r1} + {i1}i) and ({r2} + {i2}i) using a Complex structure and print the result", """
    struct Complex { int real; int imag; };
    void _start() {
        struct Complex c1 = { {r1}, {i1} };
        struct Complex c2 = { {r2}, {i2} };
        print_int(c1.real + c2.real);
        print_str(" + ");
        print_int(c1.imag + c2.imag);
        print_str("i\\n");
        exit_program(0);
    }
    """, {"r1": 3, "i1": 4, "r2": 5, "i2": 6}),
    ("time struct", "represent a time with hours={h}, minutes={m}, and seconds={s} using a Time structure and print it", """
    struct Time { int h; int m; int s; };
    void _start() {
        struct Time t = { {h}, {m}, {s} };
        print_int(t.h);
        print_char(':');
        print_int(t.m);
        print_char(':');
        print_int(t.s);
        print_char('\\n');
        exit_program(0);
    }
    """, {"h": 10, "m": 15, "s": 30}),
    ("box volume", "calculate the volume of a box with length {l}, width {w}, and height {h} using a Box structure", """
    struct Box { int length; int width; int height; };
    void _start() {
        struct Box b = { {l}, {w}, {h} };
        print_int(b.length * b.width * b.height);
        print_char('\\n');
        exit_program(0);
    }
    """, {"l": 5, "w": 4, "h": 3}),
    ("date compare", "compare two dates ({d1}/{m1}/{y1}) and ({d2}/{m2}/{y2}) using a Date structure and print 1 if equal, 0 if not", """
    struct Date { int d; int m; int y; };
    void _start() {
        struct Date date1 = { {d1}, {m1}, {y1} };
        struct Date date2 = { {d2}, {m2}, {y2} };
        int eq = (date1.d == date2.d && date1.m == date2.m && date1.y == date2.y);
        print_int(eq);
        print_char('\\n');
        exit_program(0);
    }
    """, {"d1": 12, "m1": 5, "y1": 2026, "d2": 12, "m2": 5, "y2": 2026})
]

for name, desc, code_body, params in struct_cases:
    prompt = f"Write a C program to {format_str(desc, **params)}."
    c_code = f"{c_header}\n{format_str(code_body, **params)}"
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 7: Bitwise Operations (10 Positive) ---
bitwise_cases = [
    ("and", "calculate the bitwise AND of {a} and {b}", "print_int({a} & {b});"),
    ("or", "calculate the bitwise OR of {a} and {b}", "print_int({a} | {b});"),
    ("xor", "calculate the bitwise XOR of {a} and {b}", "print_int({a} ^ {b});"),
    ("not", "calculate the bitwise NOT of {a}", "print_int(~{a});"),
    ("lshift", "left shift {a} by {b} bits", "print_int({a} << {b});"),
    ("rshift", "right shift {a} by {b} bits", "print_int({a} >> {b});"),
    ("count_set", "count the number of set bits in {a}", "int c=0; int n={a}; while(n>0) { c += (n & 1); n >>= 1; } print_int(c);"),
    ("check_bit", "check if the {b}-th bit (0-indexed) of {a} is set (print 1 if set, 0 otherwise)", "print_int(({a} & (1 << {b})) ? 1 : 0);"),
    ("set_bit", "set the {b}-th bit (0-indexed) of {a} and print the result", "print_int({a} | (1 << {b}));"),
    ("clear_bit", "clear the {b}-th bit (0-indexed) of {a} and print the result", "print_int({a} & ~(1 << {b}));")
]

for idx, (name, desc, code_body) in enumerate(bitwise_cases):
    a = (idx + 5) * 4 + 1
    b = 2 if idx in [4, 5, 7, 8, 9] else (idx + 1) * 2
    prompt = f"Write a C program to {format_str(desc, a=a, b=b)}."
    c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, a=a, b=b)}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 8: Pointers (10 Positive) ---
pointer_cases = [
    ("swap", "swap two variables with values {a} and {b} using pointers", """
    void swap(int *x, int *y) {
        int temp = *x;
        *x = *y;
        *y = temp;
    }
    void _start() {
        int a = {a}, b = {b};
        swap(&a, &b);
        print_int(a);
        print_char(' ');
        print_int(b);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("sum", "find the sum of two integers {a} and {b} using pointers", """
    void _start() {
        int a = {a}, b = {b};
        int *p1 = &a, *p2 = &b;
        print_int(*p1 + *p2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("max", "find the maximum of two values {a} and {b} using pointers", """
    void _start() {
        int a = {a}, b = {b};
        int *p1 = &a, *p2 = &b;
        print_int((*p1 > *p2) ? *p1 : *p2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("print val", "print the value of an integer {a} using pointer dereferencing", """
    void _start() {
        int a = {a};
        int *p = &a;
        print_int(*p);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("malloc", "allocate memory for an integer using malloc (mocked or custom), set it to {a}, print it, and free the memory", """
    // Custom mock allocator for nostdlib
    int mock_val;
    void _start() {
        int *p = &mock_val;
        *p = {a};
        print_int(*p);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("ptr arithmetic", "compute the sum of an array using pointer arithmetic: {arr_str}", """
    void _start() {
        int arr[] = {arr_init};
        int *p = arr;
        int sum = 0;
        for(int i=0; i<{size}; i++) {
            sum += *(p + i);
        }
        print_int(sum);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("reverse str ptr", "reverse a string \"{s}\" in-place using pointers and print it", """
    void _start() {
        char s[] = "{s}";
        char *start = s;
        char *end = s;
        while(*end != '\\0') end++;
        end--;
        while(start < end) {
            char t = *start;
            *start = *end;
            *end = t;
            start++;
            end--;
        }
        print_str(s);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("strlen ptr", "find the length of a string \"{s}\" using pointers", """
    void _start() {
        char s[] = "{s}";
        char *p = s;
        while(*p != '\\0') p++;
        print_int(p - s);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("strcpy ptr", "copy a string \"{s}\" to another buffer using pointers and print it", """
    void _start() {
        char s[] = "{s}";
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
    """),
    ("2d array sum ptr", "find the sum of elements of a 2D array of size 2x2 using pointers: {arr_str}", """
    void _start() {
        int arr[2][2] = {arr_init};
        int *p = &arr[0][0];
        int sum = 0;
        for(int i=0; i<4; i++) {
            sum += *(p + i);
        }
        print_int(sum);
        print_char('\\n');
        exit_program(0);
    }
    """)
]

for idx, (name, desc, code_body) in enumerate(pointer_cases):
    a = (idx + 1) * 11
    b = (idx + 2) * 9
    s = strings_data[idx][0] + "ptr"
    arr_values = [idx, idx+1, idx+2, idx+3]
    arr_str = f"{{{arr_values[0]}, {arr_values[1]}, {arr_values[2]}, {arr_values[3]}}}"
    
    if name == "ptr arithmetic":
        arr_init = f"{{{idx}, {idx+1}, {idx+2}, {idx+3}}}"
        prompt = f"Write a C program to {format_str(desc, arr_str=arr_str)}."
        c_code = f"{c_header}\n" + format_str(code_body, arr_init=arr_init, size=4)
    elif name == "2d array sum ptr":
        arr_init = f"{{ {{{idx}, {idx+1}}}, {{{idx+2}, {idx+3}}} }}"
        prompt = f"Write a C program to {format_str(desc, arr_str=arr_str)}."
        c_code = f"{c_header}\n" + format_str(code_body, arr_init=arr_init)
    else:
        prompt = f"Write a C program to {format_str(desc, a=a, b=b, s=s)}."
        c_code = f"{c_header}\n" + format_str(code_body, a=a, b=b, s=s)
        
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "positive"})

# --- CATEGORY 9: Null Pointer Dereferences (10 Negative) ---
for idx in range(10):
    val = (idx + 1) * 10
    prompt = f"Write a C program that dereferences a NULL pointer to cause a segmentation fault (attempt {idx+1})."
    
    # We vary the dereference context
    if idx % 3 == 0:
        body = f"int *ptr = NULL; *ptr = {val}; print_int(*ptr);"
    elif idx % 3 == 1:
        body = f"char *ptr = NULL; *ptr = 'A'; print_char(*ptr);"
    else:
        body = f"double *ptr = NULL; *ptr = 3.14; // segfault on write"
        
    c_code = f"""{c_header}
void _start() {{
    {body}
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "negative"})

# --- CATEGORY 10: Other Segfaults (10 Negative) ---
other_segfaults = [
    ("string literal modify 1", "modify a read-only string literal", """
    char *s = "hello";
    s[0] = 'H';
    print_str(s);
    """),
    ("string literal modify 2", "modify a read-only string literal", """
    char *s = "constant_string";
    s[5] = 'X';
    print_str(s);
    """),
    ("invalid address write 1", "dereference an invalid memory address", """
    int *ptr = (int*)0x12345678;
    *ptr = 999;
    print_int(*ptr);
    """),
    ("invalid address write 2", "dereference an invalid memory address", """
    char *ptr = (char*)0xDEADC0DE;
    *ptr = 'Z';
    print_char(*ptr);
    """),
    ("invalid address read 1", "read from an invalid memory address", """
    int *ptr = (int*)0x87654321;
    print_int(*ptr);
    """),
    ("invalid address write 3", "dereference an invalid memory address", """
    float *ptr = (float*)0xABCDEF00;
    *ptr = 1.23f;
    """),
    ("string literal modify 3", "modify a read-only string literal", """
    char *s = "read_only_mode";
    s[0] = 'W';
    print_str(s);
    """),
    ("null array deref 1", "access elements of a null array pointer", """
    int *arr = NULL;
    print_int(arr[10]);
    """),
    ("null array deref 2", "write to elements of a null array pointer", """
    int *arr = NULL;
    arr[0] = 5;
    print_int(arr[0]);
    """),
    ("null func ptr", "call a function pointer that is set to NULL", """
    void (*func)() = NULL;
    func();
    """)
]

for idx, (name, desc, code_body) in enumerate(other_segfaults):
    prompt = f"Write a C program that causes a segmentation fault by attempting to {desc} (example {idx+1})."
    
    if "void _start()" in code_body:
        c_code = f"{c_header}\n{code_body}"
    else:
        c_code = f"""{c_header}
void _start() {{
    {code_body}
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code, "expected": "negative"})

# Compile, execute and gather data
dataset = []

temp_dir = tempfile.gettempdir()

print(f"Total programs to compile & test: {len(programs)}")

for i, prog in enumerate(programs):
    prompt = prog["prompt"]
    c_code = prog["c_code"]
    expected = prog["expected"]
    
    c_file_path = os.path.join(temp_dir, f"temp_{i}.c")
    obj_file_path = os.path.join(temp_dir, f"temp_{i}.o")
    bin_file_path = os.path.join(temp_dir, f"temp_{i}.bin")
    
    # Write C code
    with open(c_file_path, "w") as f:
        f.write(c_code)
        
    # Compile C code: gcc-12 -c -fno-asynchronous-unwind-tables -fno-ident -fno-stack-protector -fno-builtin -Os <c_file> -o <obj_file>
    compile_cmd = ["/usr/bin/gcc-12", "-c", "-fno-asynchronous-unwind-tables", "-fno-ident", "-fno-stack-protector", "-fno-builtin", "-Os", c_file_path, "-o", obj_file_path]
    compile_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if compile_res.returncode != 0:
        print(f"Compilation FAILED for program {i}: {prompt}")
        print(compile_res.stderr)
        if os.path.exists(c_file_path):
            os.remove(c_file_path)
        raise RuntimeError(f"Compilation failed for sample {i}")
        
    # Link using ld: ld -s -N <obj_file> -o <bin_file>
    link_cmd = ["/usr/bin/ld", "-s", "-N", obj_file_path, "-o", bin_file_path]
    link_res = subprocess.run(link_cmd, capture_output=True, text=True)
    
    if link_res.returncode != 0:
        print(f"Linking FAILED for program {i}: {prompt}")
        print(link_res.stderr)
        if os.path.exists(c_file_path):
            os.remove(c_file_path)
        if os.path.exists(obj_file_path):
            os.remove(obj_file_path)
        raise RuntimeError(f"Linking failed for sample {i}")
        
    # Execute the compiled binary
    try:
        run_res = subprocess.run([bin_file_path], capture_output=True, timeout=2)
        exit_code = run_res.returncode
    except subprocess.TimeoutExpired:
        exit_code = -99
        print(f"Program {i} TIMEOUT")
        
    is_segfault = (exit_code == -11 or exit_code == -signal.SIGSEGV)
    is_success = (exit_code == 0)
    
    actual_status = "unknown"
    if is_success:
        actual_status = "positive"
    elif is_segfault:
        actual_status = "negative"
    else:
        actual_status = f"error_code_{exit_code}"
        
    if actual_status != expected:
        print(f"WARNING: Program {i} expected {expected}, got {actual_status} (exit_code={exit_code})")
        print("C code:")
        print(c_code)
        
    # Read binary bytes
    with open(bin_file_path, "rb") as f:
        binary_bytes = f.read()
        
    binary_hex = binary_bytes.hex()
    
    dataset.append({
        "prompt": prompt,
        "c_code": c_code,
        "binary_hex": binary_hex,
        "status": "positive" if is_success else "negative",
        "exit_code": exit_code
    })
    
    # Clean up
    if os.path.exists(c_file_path):
        os.remove(c_file_path)
    if os.path.exists(obj_file_path):
        os.remove(obj_file_path)
    if os.path.exists(bin_file_path):
        os.remove(bin_file_path)

# Save to c_program_dataset.json and c_program_dataset.jsonl in current workspace
workspace_dir = "/home/manifest/Documents/antigravity/mysterious-raman"
json_path = os.path.join(workspace_dir, "c_program_dataset.json")
jsonl_path = os.path.join(workspace_dir, "c_program_dataset.jsonl")

# JSON output
with open(json_path, "w") as f:
    json.dump(dataset, f, indent=2)
    
# JSONL output
with open(jsonl_path, "w") as f:
    for item in dataset:
        f.write(json.dumps(item) + "\n")

print(f"Dataset generated successfully!")
print(f"JSON path: {json_path}")
print(f"JSONL path: {jsonl_path}")
print(f"Total samples: {len(dataset)}")
positives = sum(1 for item in dataset if item["status"] == "positive")
negatives = sum(1 for item in dataset if item["status"] == "negative")
print(f"Positive samples: {positives}")
print(f"Negative samples: {negatives}")
