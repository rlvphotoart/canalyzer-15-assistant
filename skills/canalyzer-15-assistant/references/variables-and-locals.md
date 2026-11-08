# Variables and Locals

Declaration discipline, scope, lifetime, and the globals block. For strings, arrays, and associative fields, see `strings-and-arrays.md`.

## Scope: where variables live

- **Global** variables go in `variables { }` and are visible from every function and event.
- **Local** variables belong to the `{ }` block they are declared in, and are declared at the top of that block. A function/event-handler body is one such block, but so is any nested block opened by `if`, `else`, `while`, `for`, or `switch`. Each nested block gets its own declaration area at its own top.

```capl
void exampleScopes()
{
    int i;              // scope: the function body

    if (i == 0)
    {
        int j;          // scope: the if-block
        j = 1;
    }
}
```

All variables (except timers) are zero-initialized by default.

## Constants with `const`

Use `const` for named compile-time constants. This matters for array sizes: an initialized variable is still a variable, not a constant integer expression.

Wrong:

```capl
variables
{
    int my_size = 3;
    char my_array[my_size];  // Compiler error: array size must be constant integer expression
}
```

Right:

```capl
variables
{
    const int my_size = 3;
    char my_array[my_size];
}
```

The same rule applies to local declarations. If a local array uses a named size, declare the `const` size before the array, both at the top of the block that uses them.

## Local variable discipline

THIS SECTION IS EXTREMELY CRITICAL, CONSIDER IT WHENEVER YOU DECLARE AND INITIALIZE VARIABLES:

Every local variable must be declared at the top of the block (the innermost enclosing `{ }`) it is used in. That block is not necessarily the whole function - a nested `if`/`while`/`for`/`switch` body is its own block with its own top. Within a single block, every declaration must come **before any logic** in that same block - before assignments, before `if`/`for`/`while`, and even before function calls that produce values you're about to store (a function call counts as a statement). CAPL locals are `static` by default; their values persist across calls unless declared with the `stack` keyword. Regardless of lifetime, **every** declaration must sit above the first statement *of its own block*, so keep declaration separate from any computed assignment.

Wrong (a declaration follows an executable statement in the *same* block -> compile error):

```capl
void exampleFunction()
{
  int i, idx, length;
  qword result;

  idx = 0;                // a statement has now executed in this block
  int arr[3] = {1,2,3};   // too late: declaration after a statement in the same block -> parse error, 'arr' unknown
  length = elcount(arr);
  result = idx + length;
}
```

Right (all declarations first in each block, computed assignments after):

```capl
void exampleFunction()
{
  int i, idx, length;
  int arr[3] = {1,2,3};   // declaration with initializer: still must be at the top of this block
  qword result;

  idx = 0;                // computed/assigned values come AFTER all declarations in this block
  length = elcount(arr);
  result = idx + length;

  for (i = 0; i < 10; i++)
  {
    int doubled;          // for-loop body is its own block: declaration at the top of this block
    doubled = i * 2;
  }
}
```

No declarations inside a `for` header -- declare the loop variable at the top:

```capl
// WRONG
for (int i = 0; i < count; i++) { /* ... */ }

// RIGHT
int i;
for (i = 0; i < count; i++) { /* ... */ }
```

## Globals in `variables { }`

```capl
variables
{
  int idx = 0;
  int arr[3] = {1,2,3};
  int length = elcount(arr); // ATTENTION: This assignment is only valid in `variables {}` blocks. Anywhere else initialization must be separated from declaration!
}
```

### What else `variables { }` holds

User-defined TYPES (`struct`, `enum`) and message/timer INSTANCES are declared here too -- types never inside a function. Access struct members with `.`, never `->`.

```capl
variables
{
  enum WheelState { IDLE, SPINNING, LOCKED };
  struct WheelInfo { int speed; enum WheelState state; };
  struct WheelInfo gFrontLeft;   // variable of that struct type
  msTimer gPollTimer;            // instance; arming: see events-and-timers.md
}
```

Message INSTANCES also belong in `variables { }` (e.g. `message 0x100 gReqMsg;`), but they need a bus/database context to compile -- declaration form and sending are covered in `messages-and-signals.md`.

In CAPL, local variables are created "static" by default (in contrast to C). "static" is NOT a keyword in CAPL if used it creates a syntax error. In order to create a non-static local variable on the stack, you can use the keyword `stack` in the declaration.

Behavioural difference -- a plain local keeps its value across calls; the `stack` variant resets on every entry:

```capl
variables { int gPersistentCount; }
void countStatic()
{
  int n;        // static by default: keeps its value between calls
  n = n + 1;    // 1, then 2, then 3 ... across successive calls
  gPersistentCount = n;
}
void countStack()
{
  stack int n = 0;  // opted out of static-by-default: fresh on every call
  n = n + 1;        // always 1 -- reset each entry
  gPersistentCount = n;
}
```

Use `stack` when a function-local must start clean each call (counters, accumulators, scratch buffers); as always, assign before reading.

## Calls inside `variables { }`

Function calls in initializers are allowed inside `variables { }` only. Anywhere else, initialization must be separated from declaration.

```capl
variables
{
    int arr[3] = {1, 2, 3};
    int length = elcount(arr);     // calls are allowed inside variables{} initializers
}
```

## Common Mistakes

### Declaring a variable after the first statement in the same block

CAPL requires local variable declarations to appear before any executable statement *in that same block*. Placing a declaration after a function call, assignment, or control-flow construct within the same `{ }` is a compile error. A nested block (e.g. the body of an `if` or `for`) is a fresh scope and may still declare its own locals at its own top.

```capl
// WRONG
void f()
{
    doSomething();
    int i;              // too late — a statement already ran in this block
}

// RIGHT
void f()
{
    int i;              // all function-level declarations up front
    doSomething();
    for (i = 0; i < 10; i++)
    {
        int doubled;    // fine: top of the for-body's own block
        doubled = i * 2;
    }
}
```

### Declaring a loop counter inside the `for` header

CAPL does not support C99-style in-header declarations. The loop variable must be declared at the top of the enclosing block.

```capl
// WRONG
void f()
{
    for (int i = 0; i < 10; i++) { }   // declaration in for-header: invalid
}

// RIGHT
void f()
{
    int i;
    for (i = 0; i < 10; i++) { }
}
```

### Multi-counter `for` loops

CAPL allows exactly one assignment in the `for` init clause. Using a comma to initialize multiple variables is a syntax error.

```capl
// WRONG
for (i = 0, j = 0; i < 10; i++) { j++; }

// RIGHT
j = 0;
for (i = 0; i < 10; i++) { j++; }
```

### Using `static` as a keyword

`static` is not a valid keyword in CAPL and causes a compile error. Local variables are already static by default (their values persist across calls). Use the `stack` keyword to opt out of that behavior and get a fresh value on every call.

```capl
// WRONG
void f()
{
    static int counter = 0;   // compile error: "static" not valid in CAPL
    counter++;
}

// RIGHT — locals persist across calls by default
void f()
{
    int counter;              // already static by default
    counter++;
}

// RIGHT — opt out of static lifetime
void f()
{
    stack int counter;        // reset to 0 on each call
    counter++;
}
```

### Mixing `const` and non-`const` sizes for arrays

An initialized variable is not a constant integer expression. Array size bounds must use `const`-declared values; otherwise the compiler rejects the declaration.

```capl
// WRONG
variables
{
    int my_size = 3;
    char my_array[my_size];   // error: array size must be a constant integer expression
}

// RIGHT
variables
{
    const int my_size = 3;
    char my_array[my_size];
}
```

### Calling functions in local initializers (outside `variables { }`)

Function calls in initializers are only permitted inside a `variables { }` block. Inside a function or event handler, declaration and initialization must be two separate statements.

```capl
// WRONG (inside a function)
void f()
{
    int length = elcount(arr);   // call in initializer: not allowed outside variables{}
}

// RIGHT
void f()
{
    int length;
    length = elcount(arr);
}
```
