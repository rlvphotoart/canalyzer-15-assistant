# Strings, Arrays, and Associative Fields

Sizing rules, length functions, string literals, the string-function family, arrays, and maps. For declaration discipline and the globals block, see `variables-and-locals.md`. For the `%`-format-specifier table used by `snprintf`/`write`, see `special-features.md`.

## Strings are `char[]`: all the rules

### Sizing

- Declare with a compile-time size that includes the null terminator.
- `char s[5] = "Test";` uses 5 bytes: 4 letters plus `\0`.
- Never write `char[] s = "...";` without a size. That's not valid CAPL.

### Length

- *DO NOT* assume the length of a string or `char[]` stored in a variable. Use always `strlen()` for ASCII strings (or char[]) and `mbstrlen()` for multibyte strings to get the length of a string.
- When you size a `char[]`, always add `+1` for the null terminator. If a user says "make it 256 chars," double-check whether they mean "buffer of 256" or "up to 256 printable chars"; the buffer usually has to be larger.
- When working with strings or `char[]` use `strlen()` or `mbstrlen()` to get the length of a string instead of `elcount`. `elcount` returns the length of the array, not the length of the string.

### Where literals can live

String literals can be assigned at declaration time. After that, use copy functions:

```capl
void foo()
{
    char name[16] = "initial";              // OK: at declaration

    strncpy(name, "later", elcount(name));  // OK: max arg is the buffer size = elcount(dst)
    // name = "later";                      // NOT OK: literal assignment after declaration
}
```

`strncpy`'s third argument is the **destination buffer size**, written `elcount(dst)`. CAPL has no `sizeof`, so never write `strncpy(dst, src, sizeof(dst))`. Right form: `char day[16]; strncpy(day, "Sunday", elcount(day));`.

Indexing a literal directly is also invalid:

```capl
// WRONG: "test"[i]
// RIGHT: declare char[] and index that
```

## String-function decision table

Decision-first: pick the row by what you want to DO. Each operation has a **byte** form (`str*`, positions/lengths in bytes) and a **multibyte/character** form (`mbstr*`, positions/lengths in characters). Use the `mb*` form when the text may contain non-ASCII (UTF-8, Japanese ANSI, etc.); otherwise the byte form is correct for plain ASCII. Source: General "String Functions" table.

| I want to...                         | byte form (ASCII)                   | char form (multibyte)        |
| ------------------------------------ | ----------------------------------- | ---------------------------- |
| get length                           | `strlen`                            | `mbstrlen`                   |
| copy a whole string                  | `strncpy`, `strncpy_off`            | `mbstrncpy`, `mbstrncpy_off` |
| copy a substring                     | `substr_cpy`, `substr_cpy_off`      | `mbsubstr_cpy`, `mbsubstr_cpy_off` |
| append to a string                   | `strncat`                           | (use `strncat`)              |
| compare                              | `strncmp`, `strncmp_off`            | `mbstrncmp`, `mbstrncmp_off` |
| search for a substring               | `strstr`, `strstr_off`              | `mbstrstr`, `mbstrstr_off`   |
| format into a buffer                 | `snprintf`                          | (`snprintf`)                 |
| string -> integer (checked)          | `strtol`/`strtoll`/`strtoul`/`strtoull` | (same)                   |
| string -> double (checked)           | `strtod`                            | (same)                       |
| string -> number (quick)             | `atol`, `_atoi64`, `atodbl`         | (same)                       |
| number -> string                     | `ltoa` (int), `_gcvt` (double)      | (same)                       |
| change case (a-z / A-Z only)         | `toLower`, `toUpper`                | (same)                       |
| byte[] <-> formatted string          | `BytesToString`, `StringToBytes`    | (same)                       |
| regex match / search / replace       | `str_match_regex`, `strstr_regex`, `str_replace_regex` | (same)    |

Rule of thumb: search the help for `str` / `mbstr` and chain library functions rather than hand-rolling character loops. It is both safer and more idiomatic.

### Copy, search, compare, append

All copy/append functions take a **max** (= destination buffer size, `elcount(dst)`) and guarantee a terminating `\0`, so at most `max-1` bytes land in the buffer.

```capl
void demo_copy_search_compare()
{
    char src[18] = "Vector Informatik";
    char dst[32];
    char part[8];
    char needle[4] = "Inf";
    char suffix[7] = " CANoe";
    char prefix[7] = "Vector";
    long pos;
    long cmp;

    // COPY whole string -- max arg is dest size. Source: strncpy
    strncpy(dst, src, elcount(dst));            // dst = "Vector Informatik"

    // COPY a substring: srcStart=0, len=6, max=elcount(dst). len=-1 copies to end.
    // Source: substr_cpy
    substr_cpy(part, src, 0, 6, elcount(part)); // part = "Vector"

    // SEARCH for a substring -> first byte position, or -1 if not found. Source: strstr
    pos = strstr(src, needle);                  // pos = 7

    // APPEND -- len is the max size of the COMPOSITE string incl '\0', NOT the
    // number of bytes to add. Source: strncat
    strncpy(dst, prefix, elcount(dst));
    strncat(dst, suffix, elcount(dst));         // dst = "Vector CANoe"

    // COMPARE up to len bytes -> 0 equal, -1 if s1<s2, +1 if s1>s2. Source: strncmp
    cmp = strncmp(src, prefix, 6);              // cmp = 0  (use ==0 to test equality)
}
```

### Format (snprintf)

`snprintf(dst, len, format, ...)` is CAPL's `sprintf`. `len` is the buffer size (`elcount(dst)`); it returns the number of characters written. The `format` string uses the SAME `%`-specifiers as `write` -- see `special-features.md` for the full table.

```capl
void demo_format()
{
    char buf[64];
    char who[7] = "Vector";
    long written;
    // common specifiers: %d (integer), %s (string), %x (hex), %f (float), %g (double)
    written = snprintf(buf, elcount(buf), "id=%d name=%s", 42, who); // buf = "id=42 name=Vector"
}
```

### Convert (string <-> number)

```capl
void demo_convert()
{
    char digits[8] = "0xFF";
    char num[12];
    long n;
    double d;
    int idx;

    // STRING -> integer, CHECKED. strtol returns the index of the first char AFTER
    // the number; -1 on overflow; -2 if empty or startIndex past end.
    // Base auto-detected: 0x..=hex, 0..=octal, else decimal. Source: strtol
    idx = strtol(digits, n);     // n = 255, idx = 4
    // form 2 starts parsing at a given index: strtol(s, startIndex, result)

    // STRING -> double, CHECKED. strtod mirrors strtol: returns the index of the
    // first char AFTER the number; -1 on overflow; -2 if empty or startIndex past end.
    // Result written via the out-param (0 on no-conversion). Source: strtod
    idx = strtod("  -3.7", d);   // d = -3.7, idx = 6
    // form 2 starts parsing at a given index: strtod(s, startIndex, result)

    // STRING -> number, QUICK (returns 0 / 0.0 on failure, no index). Source: atol, atodbl
    n = atol("200");             // n = 200   (0x.. -> base 16)
    d = atodbl("  -3.7");        // d = -3.7

    // NUMBER -> string. ltoa(value, dest, base) with base 2..36. Source: ltoa
    ltoa(255, num, 16);          // num = "ff"
    // for doubles use _gcvt(val, significantDigits, dest). Source: _gcvt
}
```

### The `_off` offset idiom (CAPL's "no pointer arithmetic" answer)

CAPL has **no pointer arithmetic and no address-of**: `temp + i` and `&temp[i]` are invalid. When you need to start a search or copy at an index, pass the index to the `_off` variant as a parameter -- that is the whole purpose of the `_off` family.

```capl
void demo_offset_idiom()
{
    char temp[32] = "abc,def,ghi";
    char field[8];
    char comma[2] = ",";
    long firstComma;
    long secondPos;

    firstComma = strstr(temp, comma);                    // 3

    // search for the NEXT comma, starting after the first. Source: strstr_off
    secondPos = strstr_off(temp, firstComma + 1, comma); // 7

    // copy substring "def" (src start = 4, len = 3) into field. Source: substr_cpy_off
    substr_cpy_off(field, 0, temp, firstComma + 1, 3, elcount(field)); // field = "def"

    // CORRECT: secondPos = strstr_off(temp, firstComma + 1, comma);
    // WRONG:   secondPos = strstr(temp + firstComma + 1, comma);  // -- no pointer arithmetic
    // WRONG:   substr_cpy(field, &temp[firstComma + 1], 0, 3, elcount(field)); // -- no &
}
```

`_off` variants of the byte family: `strstr_off`, `strncpy_off(dst, destOffset, src, max)`, `strncmp_off`, `substr_cpy_off(dst, destOffset, src, srcStart, len, max)`. Each has an `mb*` counterpart for multibyte text.

### Byte arrays and `byte[]` <-> string

A `byte[]` holds raw bytes (e.g. a CAN payload); a `char[]` holds text. They are different types -- do not pass one where the other is expected. Convert between them with `BytesToString` / `StringToBytes`, where `format` is a single-`%` printf specifier and `sep` is the separator inserted between bytes.

```capl
void demo_bytes()
{
    byte payload[3] = {5, 15, 255};
    byte parsed[5];
    char text[20];
    char fmt[5] = "%02X";
    char sep[2] = "-";
    long res;

    res = BytesToString(payload, fmt, sep, text); // text = "05-0F-FF"; res = chars written, -1 if too small
    res = StringToBytes(text, fmt, sep, parsed);  // parsed = {5,15,255}; res = bytes parsed, -1/-2 on error
}
```

### Regex (Perl syntax)

Backslashes must be doubled inside a string literal: `"\\d"` matches a digit. Source: str_match_regex, strstr_regex, str_replace_regex.

```capl
void demo_regex()
{
    char buffer[70] = "Vector Informatik";
    long ok;
    long pos;

    ok  = str_match_regex(buffer, "Vector [A-Za-z]*");  // 1 -- whole string must match (anchored)
    pos = strstr_regex(buffer, "Inf[a-z]*");            // 7 -- byte position of match, or -1
    str_replace_regex(buffer, "Inf[a-z]*", "CANoe");    // buffer = "Vector CANoe"; returns 1 ok / 0 too long
}
```

`strstr_regex_off(s, offset, pattern)` starts the search at an offset (same `_off` idiom as above).

### 2D string arrays

```capl
void bar()
{
    // three strings, longest is "three" (5 chars + \0 = 6), so [3][6]
    char numbers[3][6] = {"one", "two", "three"};
    // numbers[0] => "one"
    // numbers[1] => "two"
    // numbers[2] => "three"
}
```

## Arrays

- Sizes must be compile-time constants at declaration. Use the `const` keyword for named sizes, for example `const int N = 10; int arr[N];`. A plain non-`const` variable will not work.
- Multi-dimensional arrays are supported: `int m[3][4];`.
- Arrays are **passed to functions by reference automatically**.
- `elcount(arr)` returns the element count.
- **No pointer arithmetic**: `arr + 5` and `&arr[5]` are invalid. If a function expects a start offset, pass the offset as a separate parameter (same idiom as the string `_off` functions above).

## Associative fields (maps)

Syntax:
- Simple: `VALUE_TYPE name[KEY_TYPE];`
- Array of maps: `VALUE_TYPE name[N][KEY_TYPE];`

Allowed value types: any scalar, enum, struct, or array.
Allowed key types: `long`, `int64`, `float`, `double`, `char[]`, enum types. **`int` is not allowed as a key type**; use `long` instead.

When the value or key is a struct/enum, prefix with the keyword:

```capl
variables
{
    enum MyEnum { A, B, C };
    struct MyStruct { int x; };

    int map_1[int64];
    char[10] map_2[float];
    double map_3[char[]];
    struct MyStruct map_4[enum MyEnum];
    int map_5[2][3][float];          // 2x3 arrays of int keyed by float
}
```

Associative fields are passed by reference automatically.

## Anti-patterns (correct vs wrong)

```capl
// 1. elcount is NOT string length
//    CORRECT: len = strlen(s);                 // bytes of text up to '\0'
//    WRONG:   len = elcount(s);                // -- that is the BUFFER size, not the text length

// 2. char[] must be sized
//    CORRECT: char buf[64];
//    WRONG:   char[] buf;                      // -- no size; not valid CAPL

// 3. Do not index a literal
//    CORRECT: char s[5] = "test"; c = s[i];
//    WRONG:   c = "test"[i];                   // -- cannot index a string literal

// 4. strncpy max is a buffer size, not sizeof
//    CORRECT: strncpy(dst, src, elcount(dst));
//    WRONG:   strncpy(dst, src, sizeof(dst));  // -- CAPL has no sizeof

// 5. Need an offset? Use the _off variant, never pointer math
//    CORRECT: pos = strstr_off(s, i, needle);
//    WRONG:   pos = strstr(s + i, needle);     // -- no pointer arithmetic
//    WRONG:   pos = strstr(&s[i], needle);     // -- no address-of
```

## Common Mistakes

### `char[]` declared without an explicit size

```capl
// WRONG
char s[] = "test";               // no size: rejected
char[] data = "This is data!";   // wrong syntax shape

// RIGHT
char s[5] = "test";              // 4 chars + \0 = 5
char data[14] = "This is data!"; // 13 chars + \0 = 14
```

CAPL requires a compile-time size for every `char[]`. Always add 1 for the null terminator.

### `elcount` vs `strlen`

```capl
// WRONG — elcount gives the buffer capacity, not the used length
char name[32] = "Ada";
int len = elcount(name); // 32, not 3

// RIGHT
int len = strlen(name);  // 3
```

`elcount(buf)` returns the allocated buffer size; `strlen(buf)` returns the current string length. Mixing them causes off-by-N bugs whenever the buffer is only partially filled.

### Indexing a string literal directly

```capl
// WRONG
char ch = "test"[i];

// RIGHT
char s[5] = "test";
char ch = s[i];
```

CAPL does not support indexing a string literal inline. Assign the literal to a named `char[]` first, then index that variable.

### Assigning a string literal after declaration

```capl
// WRONG
char name[16];
name = "Ada"; // literal assignment after declaration is invalid

// RIGHT
char name[16];
strncpy(name, "Ada", elcount(name));
```

Literal assignment is only valid at the declaration site. For all subsequent assignments use `strncpy` or another copy function.

### Using `int` as an associative-field key type

```capl
// WRONG
int map[int]; // int key is not allowed

// RIGHT
int map[long]; // use long (or int64, float, double, char[], enum)
```

The allowed key types for associative fields are `long`, `int64`, `float`, `double`, `char[]`, and enum types. `int` is explicitly not permitted.

### Array size given as a non-`const` variable

```capl
// WRONG
int n = 10;
int arr[n]; // runtime variable as size: not valid

// RIGHT
const int N = 10;
int arr[N];
```

Array sizes must be compile-time constants. Declare the size with the `const` keyword.

### Pointer arithmetic on arrays

```capl
// WRONG
int arr[10];
int *p = arr + 5; // pointer arithmetic is invalid in CAPL

// RIGHT
// pass the offset as a separate parameter to the function
void process(int arr[], int offset) { ... }
```

CAPL has no pointer arithmetic. If a function needs to operate on a sub-range of an array, pass the start offset as an explicit parameter.
