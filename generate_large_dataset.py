import os
import subprocess
import tempfile
import json
import random

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

# --- CATEGORY 1: Simple Math Operations (500 samples) ---
print("Generating Category 1: Math Operations...")
math_templates = [
    ("sum of {a} and {b}", "print_int({a} + {b});"),
    ("difference between {a} and {b}", "print_int({a} - {b});"),
    ("product of {a} and {b}", "print_int({a} * {b});"),
    ("quotient of {a} divided by {b}", "print_int({a} / {b});"),
    ("remainder of {a} divided by {b}", "print_int({a} % {b});"),
    ("average of three numbers: {a}, {b}, and {c}", "print_int(({a} + {b} + {c}) / 3);"),
    ("area of a circle with radius {a} (using pi=3 approximation)", "print_int(3 * {a} * {a});"),
    ("volume of a cube with side length {a}", "print_int({a} * {a} * {a});"),
    ("maximum of two numbers {a} and {b}", "print_int(({a} > {b}) ? {a} : {b});"),
    ("minimum of two numbers {a} and {b}", "print_int(({a} < {b}) ? {a} : {b});")
]

for i in range(50):
    for desc, code_body in math_templates:
        a = (i + 1) * 3 + random.randint(1, 10)
        b = (i + 1) * 2 + random.randint(1, 5)
        if b == 0: b = 1
        c = (i + 1) * 4 + random.randint(1, 15)
        prompt = f"Write a C program to calculate the {format_str(desc, a=a, b=b, c=c)}."
        c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, a=a, b=b, c=c)}
    print_char('\\n');
    exit_program(0);
}}
"""
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 2: Loops (500 samples) ---
print("Generating Category 2: Loops...")
loop_templates = [
    ("print numbers from 1 to {n}", "for(int i=1; i<={n}; i++) { print_int(i); print_char(' '); }"),
    ("print numbers from {n} down to 1", "for(int i={n}; i>=1; i--) { print_int(i); print_char(' '); }"),
    ("calculate the sum of numbers from 1 to {n}", "int sum=0; for(int i=1; i<={n}; i++) sum+=i; print_int(sum);"),
    ("print even numbers from 2 to {n}", "for(int i=2; i<={n}; i+=2) { print_int(i); print_char(' '); }"),
    ("print odd numbers from 1 to {n}", "for(int i=1; i<={n}; i+=2) { print_int(i); print_char(' '); }"),
    ("print the first {n} multiples of 3", "for(int i=1; i<={n}; i++) { print_int(i*3); print_char(' '); }"),
    ("print the first {n} multiples of 5", "for(int i=1; i<={n}; i++) { print_int(i*5); print_char(' '); }"),
    ("calculate the sum of even numbers from 2 to {n}", "int sum=0; for(int i=2; i<={n}; i+=2) sum+=i; print_int(sum);"),
    ("calculate the sum of odd numbers from 1 to {n}", "int sum=0; for(int i=1; i<={n}; i+=2) sum+=i; print_int(sum);"),
    ("print the squares of numbers from 1 to {n}", "for(int i=1; i<={n}; i++) { print_int(i*i); print_char(' '); }")
]

for i in range(50):
    for desc, code_body in loop_templates:
        n = (i + 1) * 2 + random.randint(2, 6)
        prompt = f"Write a C program to {format_str(desc, n=n)}."
        c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, n=n)}
    print_char('\\n');
    exit_program(0);
}}
"""
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 3: Algorithms (500 samples) ---
print("Generating Category 3: Algorithms...")
algo_templates = [
    ("calculate the factorial of {n} using a loop", """
    int n = {n};
    long long fact = 1;
    for(int i=1; i<=n; i++) fact *= i;
    print_int(fact);
    """),
    ("calculate the factorial of {n} using recursion", """
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
    ("calculate the {n}-th Fibonacci number using a loop", """
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
    ("calculate the {n}-th Fibonacci number using recursion", """
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
    ("check if {n} is prime (print 1 for prime, 0 otherwise)", """
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
    ("print prime numbers up to {n}", """
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
    ("find the GCD of {a} and {b}", """
    int a = {a}, b = {b};
    while(b != 0) {
        int temp = b;
        b = a % b;
        a = temp;
    }
    print_int(a);
    """),
    ("find the LCM of {a} and {b}", """
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
    ("calculate the sum of the digits of {n}", """
    int n = {n};
    int sum = 0;
    while(n > 0) {
        sum += n % 10;
        n /= 10;
    }
    print_int(sum);
    """),
    ("reverse the digits of the number {n}", """
    int n = {n};
    int rev = 0;
    while(n > 0) {
        rev = rev * 10 + (n % 10);
        n /= 10;
    }
    print_int(rev);
    """)
]

for i in range(50):
    for desc, code_body in algo_templates:
        n = random.randint(3, 15)
        a = (i + 1) * 3 + random.randint(2, 10)
        b = (i + 1) * 4 + random.randint(2, 12)
        
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
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 4: Arrays (500 samples) ---
print("Generating Category 4: Arrays...")
array_templates = [
    ("find the sum of elements in the array: {arr_str}", "int sum=0; for(int i=0; i<{size}; i++) sum+=arr[i]; print_int(sum);"),
    ("find the maximum element in the array: {arr_str}", "int max=arr[0]; for(int i=1; i<{size}; i++) if(arr[i]>max) max=arr[i]; print_int(max);"),
    ("find the minimum element in the array: {arr_str}", "int min=arr[0]; for(int i=1; i<{size}; i++) if(arr[i]<min) min=arr[i]; print_int(min);"),
    ("reverse the array: {arr_str}", "for(int i={size}-1; i>=0; i--) { print_int(arr[i]); print_char(' '); }"),
    ("count the number of even elements in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]%2==0) c++; print_int(c);"),
    ("count the number of odd elements in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]%2!=0) c++; print_int(c);"),
    ("find the index of the element {target} in the array: {arr_str}", "int idx=-1; for(int i=0; i<{size}; i++) if(arr[i]=={target}) { idx=i; break; } print_int(idx);"),
    ("sort the array using bubble sort: {arr_str}", "for(int i=0; i<{size}-1; i++) for(int j=0; j<{size}-i-1; j++) if(arr[j]>arr[j+1]) { int t=arr[j]; arr[j]=arr[j+1]; arr[j+1]=t; } for(int i=0; i<{size}; i++) { print_int(arr[i]); print_char(' '); }"),
    ("count the occurrences of {target} in the array: {arr_str}", "int c=0; for(int i=0; i<{size}; i++) if(arr[i]=={target}) c++; print_int(c);"),
    ("print all elements in the array: {arr_str}", "for(int i=0; i<{size}; i++) { print_int(arr[i]); print_char(' '); }")
]

for i in range(50):
    for desc, code_body in array_templates:
        size = random.randint(4, 7)
        arr_values = [random.randint(1, 50) for _ in range(size)]
        arr_str = ", ".join(map(str, arr_values))
        target = arr_values[random.randint(0, size-1)]
        
        prompt = f"Write a C program to {format_str(desc, arr_str=f'{{{arr_str}}}', target=target)}."
        c_code = f"""{c_header}
void _start() {{
    int arr[] = {{{arr_str}}};
    {format_str(code_body, size=size, target=target)}
    print_char('\\n');
    exit_program(0);
}}
"""
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 5: Strings (500 samples) ---
print("Generating Category 5: Strings...")
words_list = [
    "apple", "banana", "cherry", "date", "elder", "fig", "grape", "honey", "ivory", "juice",
    "kiwi", "lemon", "mango", "nut", "orange", "pear", "quince", "radar", "sky", "time",
    "unicorn", "valve", "world", "xenon", "yellow", "zebra", "level", "racecar", "madam"
]

string_templates = [
    ("calculate the length of the string \"{s}\"", "int len=0; while(str[len]!='\\0') len++; print_int(len);"),
    ("count the number of vowels in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U') c++; } print_int(c);"),
    ("count the number of consonants in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(((ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')) && !(ch=='a'||ch=='e'||ch=='i'||ch=='o'||ch=='u'||ch=='A'||ch=='E'||ch=='I'||ch=='O'||ch=='U')) c++; } print_int(c);"),
    ("check if the string \"{s}\" is a palindrome (print 1 for yes, 0 otherwise)", "int len=0; while(str[len]!='\\0') len++; int pal=1; for(int i=0; i<len/2; i++) if(str[i]!=str[len-1-i]) pal=0; print_int(pal);"),
    ("reverse the string \"{s}\"", "int len=0; while(str[len]!='\\0') len++; for(int i=len-1; i>=0; i--) print_char(str[i]);"),
    ("convert the string \"{s}\" to uppercase", "for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch>='a'&&ch<='z') ch=ch-'a'+'A'; print_char(ch); }"),
    ("convert the string \"{s_upper}\" to lowercase", "for(int i=0; str[i]!='\\0'; i++) { char ch=str[i]; if(ch>='A'&&ch<='Z') ch=ch-'A'+'a'; print_char(ch); }"),
    ("print the character count of '{target_char}' in the string \"{s}\"", "int c=0; for(int i=0; str[i]!='\\0'; i++) if(str[i]=='{target_char}') c++; print_int(c);"),
    ("copy the string \"{s}\" to another buffer and print it", "char dest[100]; int i=0; while(str[i]!='\\0') { dest[i]=str[i]; i++; } dest[i]='\\0'; print_str(dest);"),
    ("concatenate \"{s}\" and \"123\" and print the result", "char dest[100]; int i=0; while(str[i]!='\\0') { dest[i]=str[i]; i++; } dest[i++]='1'; dest[i++]='2'; dest[i++]='3'; dest[i]='\\0'; print_str(dest);")
]

for i in range(50):
    for desc, code_body in string_templates:
        s = random.choice(words_list)
        if len(s) > 10: s = s[:10]
        s_upper = s.upper()
        target_char = s[random.randint(0, len(s)-1)]
        
        prompt = f"Write a C program to {format_str(desc, s=s, s_upper=s_upper, target_char=target_char)}."
        
        str_init = f"char str[] = \"{s_upper}\";" if "s_upper" in desc else f"char str[] = \"{s}\";"
        c_code = f"""{c_header}
void _start() {{
    {str_init}
    {format_str(code_body, s=s, target_char=target_char)}
    print_char('\\n');
    exit_program(0);
}}
"""
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 6: Bitwise Operations (500 samples) ---
print("Generating Category 6: Bitwise Operations...")
bitwise_templates = [
    ("calculate the bitwise AND of {a} and {b}", "print_int({a} & {b});"),
    ("calculate the bitwise OR of {a} and {b}", "print_int({a} | {b});"),
    ("calculate the bitwise XOR of {a} and {b}", "print_int({a} ^ {b});"),
    ("calculate the bitwise NOT of {a}", "print_int(~{a});"),
    ("left shift {a} by {b} bits", "print_int({a} << {b});"),
    ("right shift {a} by {b} bits", "print_int({a} >> {b});"),
    ("count the number of set bits in {a}", "int c=0; int n={a}; while(n>0) { c += (n & 1); n >>= 1; } print_int(c);"),
    ("check if the {b}-th bit (0-indexed) of {a} is set (print 1 if set, 0 otherwise)", "print_int(({a} & (1 << {b})) ? 1 : 0);"),
    ("set the {b}-th bit (0-indexed) of {a} and print the result", "print_int({a} | (1 << {b}));"),
    ("clear the {b}-th bit (0-indexed) of {a} and print the result", "print_int({a} & ~(1 << {b}));")
]

for i in range(50):
    for desc, code_body in bitwise_templates:
        a = random.randint(1, 100)
        b = random.randint(1, 4)
        prompt = f"Write a C program to {format_str(desc, a=a, b=b)}."
        c_code = f"""{c_header}
void _start() {{
    {format_str(code_body, a=a, b=b)}
    print_char('\\n');
    exit_program(0);
}}
"""
        programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 7: Structures & Pointers (500 samples) ---
print("Generating Category 7: Structures & Pointers...")
struct_pointer_templates = [
    ("rect_area", "calculate the area of a rectangle with width {w} and height {h} using a Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        struct Rectangle r = { {w}, {h} };
        print_int(r.width * r.height);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("rect_perim", "calculate the perimeter of a rectangle with width {w} and height {h} using a Rectangle structure", """
    struct Rectangle { int width; int height; };
    void _start() {
        struct Rectangle r = { {w}, {h} };
        print_int(2 * (r.width + r.height));
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("square_area", "calculate the area of a square with side {side_val} using a Square structure", """
    struct Square { int side; };
    void _start() {
        struct Square sq = { {side_val} };
        print_int(sq.side * sq.side);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("2d_point", "print a 2D Point structure with x={x} and y={y}", """
    struct Point { int x; int y; };
    void _start() {
        struct Point p = { {x}, {y} };
        print_int(p.x);
        print_char(' ');
        print_int(p.y);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("dist_sq", "compute the distance squared between Point({x1},{y1}) and Point({x2},{y2}) using Point structures", """
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
    """),
    ("complex_add", "add two complex numbers ({r1} + {i1}i) and ({r2} + {i2}i) using a Complex structure and print the result", """
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
    """),
    ("time_struct", "represent a time with hours={h}, minutes={m}, and seconds={s} using a Time structure and print it", """
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
    """),
    ("box_volume", "calculate the volume of a box with length {l}, width {w}, and height {h} using a Box structure", """
    struct Box { int length; int width; int height; };
    void _start() {
        struct Box b = { {l}, {w}, {h} };
        print_int(b.length * b.width * b.height);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("swap_ptr", "swap two variables with values {a} and {b} using pointers", """
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
    ("sum_ptr", "find the sum of two integers {a} and {b} using pointers", """
    void _start() {
        int a = {a}, b = {b};
        int *p1 = &a, *p2 = &b;
        print_int(*p1 + *p2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("max_ptr", "find the maximum of two values {a} and {b} using pointers", """
    void _start() {
        int a = {a}, b = {b};
        int *p1 = &a, *p2 = &b;
        print_int((*p1 > *p2) ? *p1 : *p2);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("malloc_sim", "allocate memory for an integer using malloc (mocked or custom), set it to {a}, print it, and free the memory", """
    int mock_val;
    void _start() {
        int *p = &mock_val;
        *p = {a};
        print_int(*p);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("ptr_arith", "compute the sum of an array using pointer arithmetic: {arr_str}", """
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
    ("reverse_str_ptr", "reverse a string \"{s}\" in-place using pointers and print it", """
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
    ("strlen_ptr", "find the length of a string \"{s}\" using pointers", """
    void _start() {
        char s[] = "{s}";
        char *p = s;
        while(*p != '\\0') p++;
        print_int(p - s);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("strcpy_ptr", "copy a string \"{s}\" to another buffer using pointers and print it", """
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
    ("2d_array_ptr", "find the sum of elements of a 2D array of size 2x2 using pointers: {arr_str}", """
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
    """),
    ("date_compare", "compare two dates ({d1}/{m1}/{y1}) and ({d2}/{m2}/{y2}) using a Date structure and print 1 if equal, 0 if not", """
    struct Date { int d; int m; int y; };
    void _start() {
        struct Date date1 = { {d1}, {m1}, {y1} };
        struct Date date2 = { {d2}, {m2}, {y2} };
        int eq = (date1.d == date2.d && date1.m == date2.m && date1.y == date2.y);
        print_int(eq);
        print_char('\\n');
        exit_program(0);
    }
    """),
    ("student_grade", "print the details of a Student with id={id} and grade={grade} using a Student structure", """
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
    """),
    ("point_distance", "compute the distance squared between Point({x1},{y1}) and Point({x2},{y2}) using Point structures", """
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
    """)
]

for i in range(25):
    for name, desc, code_body in struct_pointer_templates:
        params = {
            "w": random.randint(5, 50),
            "h": random.randint(5, 50),
            "side_val": random.randint(2, 20),
            "x": random.randint(1, 100),
            "y": random.randint(1, 100),
            "x1": random.randint(1, 10),
            "y1": random.randint(1, 10),
            "x2": random.randint(11, 20),
            "y2": random.randint(11, 20),
            "r1": random.randint(1, 10),
            "i1": random.randint(1, 10),
            "r2": random.randint(1, 10),
            "i2": random.randint(1, 10),
            "l": random.randint(2, 10),
            "a": random.randint(5, 100),
            "b": random.randint(5, 100),
            "id": random.randint(100, 9999),
            "grade": random.randint(50, 100),
            "m": random.randint(0, 59),
            "d1": random.randint(1, 28),
            "m1": random.randint(1, 12),
            "y1": random.randint(2000, 2030),
        }
        params["d2"] = params["d1"]
        params["m2"] = params["m1"]
        params["y2"] = params["y1"]
        s = random.choice(words_list) + "ptr"
        
        arr_values = [random.randint(1, 20) for _ in range(4)]
        arr_str = f"{{{', '.join(map(str, arr_values))}}}"
        arr_init = f"{{{', '.join(map(str, arr_values))}}}"
        
        # Adjust dynamic parameters
        full_desc = format_str(desc, arr_str=arr_str, s=s, **params)
        prompt = f"Write a C program to {full_desc}."
        
        if name == "ptr_arith":
            full_code = f"{c_header}\n" + format_str(code_body, arr_init=arr_init, size=4)
        elif name == "2d_array_ptr":
            arr_2d_init = f"{{ {{{arr_values[0]}, {arr_values[1]}}}, {{{arr_values[2]}, {arr_values[3]}}} }}"
            full_code = f"{c_header}\n" + format_str(code_body, arr_init=arr_2d_init)
        else:
            full_code = f"{c_header}\n" + format_str(code_body, s=s, **params)
            
        programs.append({"prompt": prompt, "c_code": full_code})

# --- CATEGORY 8: Calculator applications (500 samples) ---
print("Generating Category 8: Calculators...")
for i in range(500):
    start = random.randint(1, 20)
    x = random.randint(1, 10)
    y = random.randint(2, 5)
    z = random.randint(1, 15)
    
    # Random ops
    ops = [
        ("adds", "+"),
        ("subtracts", "-"),
        ("multiplies", "*")
    ]
    op1_name, op1_sym = random.choice(ops)
    op2_name, op2_sym = random.choice(ops)
    op3_name, op3_sym = random.choice(ops)
    
    desc = f"starts with {start}, {op1_name} {x}, {op2_name} {y}, {op3_name} {z}"
    prompt = f"Write a C program to calculate the result of a sequence of operations using a structure or variables that: {desc}, and prints the final result."
    
    c_code = f"""{c_header}
void _start() {{
    long long val = {start};
    val = val {op1_sym} {x};
    val = val {op2_sym} {y};
    val = val {op3_sym} {z};
    print_int(val);
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 9: Tic-Tac-Toe Game simulations (500 samples) ---
print("Generating Category 9: Tic-Tac-Toe Checkers...")
for i in range(500):
    # Construct a valid board state
    slots = [' '] * 9
    num_moves = random.randint(3, 9)
    current_player = 'X'
    for _ in range(num_moves):
        empty_indices = [idx for idx, val in enumerate(slots) if val == ' ']
        if not empty_indices:
            break
        slots[random.choice(empty_indices)] = current_player
        current_player = 'O' if current_player == 'X' else 'X'
        
    board_str = ",".join(slots)
    prompt = f"Write a C program to check the winner of a Tic-Tac-Toe board with state '{board_str}' and print the winner ('X', 'O', 'D' for Draw, or 'I' for In Progress)."
    
    # Generate Tic-Tac-Toe checker C code
    c_slots = ", ".join(f"'{c}'" for c in slots)
    c_code = f"""{c_header}
void _start() {{
    char board[9] = {{{c_slots}}};
    char winner = ' ';
    
    // Rows
    if (board[0] != ' ' && board[0] == board[1] && board[1] == board[2]) winner = board[0];
    else if (board[3] != ' ' && board[3] == board[4] && board[4] == board[5]) winner = board[3];
    else if (board[6] != ' ' && board[6] == board[7] && board[7] == board[8]) winner = board[6];
    
    // Columns
    else if (board[0] != ' ' && board[0] == board[3] && board[3] == board[6]) winner = board[0];
    else if (board[1] != ' ' && board[1] == board[4] && board[4] == board[7]) winner = board[1];
    else if (board[2] != ' ' && board[2] == board[5] && board[5] == board[8]) winner = board[2];
    
    // Diagonals
    else if (board[0] != ' ' && board[0] == board[4] && board[4] == board[8]) winner = board[0];
    else if (board[2] != ' ' && board[2] == board[4] && board[4] == board[6]) winner = board[2];
    
    if (winner != ' ') {{
        print_char(winner);
    }} else {{
        int empty = 0;
        for(int i=0; i<9; i++) if(board[i] == ' ') empty++;
        if(empty == 0) print_char('D');
        else print_char('I');
    }}
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code})

# --- CATEGORY 10: Grid Snake Game simulations (500 samples) ---
print("Generating Category 10: Grid Snake Simulators...")
for i in range(500):
    start_x = random.randint(0, 4)
    start_y = random.randint(0, 4)
    move_len = random.randint(3, 8)
    moves = "".join(random.choice(['R', 'L', 'U', 'D']) for _ in range(move_len))
    
    prompt = f"Write a C program to simulate a snake on a 5x5 grid starting at position ({start_x}, {start_y}) executing move sequence \"{moves}\", and print the final coordinates."
    
    # Generate C code for Snake Simulator
    c_code = f"""{c_header}
void _start() {{
    int x = {start_x};
    int y = {start_y};
    char moves[] = "{moves}";
    for (int i = 0; moves[i] != '\\0'; i++) {{
        if (moves[i] == 'R') x = (x + 1) % 5;
        else if (moves[i] == 'L') x = (x - 1 + 5) % 5;
        else if (moves[i] == 'D') y = (y + 1) % 5;
        else if (moves[i] == 'U') y = (y - 1 + 5) % 5;
    }}
    print_str("X:");
    print_int(x);
    print_str(" Y:");
    print_int(y);
    print_char('\\n');
    exit_program(0);
}}
"""
    programs.append({"prompt": prompt, "c_code": c_code})

# Compile, execute and gather dataset
print(f"Total positive programs generated: {len(programs)}")
dataset = []

temp_dir = tempfile.gettempdir()
success_count = 0

for i, prog in enumerate(programs):
    prompt = prog["prompt"]
    c_code = prog["c_code"]
    
    c_file_path = os.path.join(temp_dir, f"temp_5k_{i}.c")
    obj_file_path = os.path.join(temp_dir, f"temp_5k_{i}.o")
    bin_file_path = os.path.join(temp_dir, f"temp_5k_{i}.bin")
    
    # Write C code
    with open(c_file_path, "w") as f:
        f.write(c_code)
        
    # Compile C code: gcc-12
    compile_cmd = ["/usr/bin/gcc-12", "-c", "-fno-asynchronous-unwind-tables", "-fno-ident", "-fno-stack-protector", "-fno-builtin", "-Os", c_file_path, "-o", obj_file_path]
    compile_res = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if compile_res.returncode != 0:
        if os.path.exists(c_file_path): os.remove(c_file_path)
        continue
        
    # Link using ld
    link_cmd = ["/usr/bin/ld", "-s", "-N", obj_file_path, "-o", bin_file_path]
    link_res = subprocess.run(link_cmd, capture_output=True, text=True)
    
    if link_res.returncode != 0:
        if os.path.exists(c_file_path): os.remove(c_file_path)
        if os.path.exists(obj_file_path): os.remove(obj_file_path)
        continue
        
    # Execute the compiled binary to ensure exit code 0
    try:
        run_res = subprocess.run([bin_file_path], capture_output=True, timeout=1)
        exit_code = run_res.returncode
    except subprocess.TimeoutExpired:
        exit_code = -99
        
    if exit_code == 0:
        # Success! Gather hex and add to dataset
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
    
    # Clean up files
    if os.path.exists(c_file_path): os.remove(c_file_path)
    if os.path.exists(obj_file_path): os.remove(obj_file_path)
    if os.path.exists(bin_file_path): os.remove(bin_file_path)
    
    if (i + 1) % 500 == 0:
        print(f"Processed {i+1} programs. Successful verified: {success_count}")

# Save to c_program_dataset_5k.json in current workspace
workspace_dir = "/home/manifest/Documents/antigravity/mysterious-raman"
json_path = os.path.join(workspace_dir, "c_program_dataset_5k.json")

with open(json_path, "w") as f:
    json.dump(dataset, f, indent=2)
    
print(f"Dataset generated successfully!")
print(f"JSON path: {json_path}")
print(f"Total positive verified samples collected: {len(dataset)}")
