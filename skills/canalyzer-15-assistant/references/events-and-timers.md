# Events and Timers

CAPL is event-driven: you do not write a `main()`. You declare event procedures with `on <event>`, and the runtime calls them when the event occurs. Inside any handler the keyword `this` is the event data (message, timer, key code, ...). This file OWNS the event catalogue, dispatch, and the timer API. Signal VALUE access ($ syntax, raw/phys) lives in `messages-and-signals.md`; `on sysVar*` lives in `system-variables.md`.

Event catalogue (each has its own section below): `on preStart`, `on start`, `on preStop`, `on stopMeasurement` (lifecycle); `on key`; `on message <id|name|*>`, `on errorFrame`, `on busOff` (CAN); `on signal` / `on signal_change` / `on signal_update`; `on timer <name>`; `on *` (catch-all); `on sysVar` / `on sysVar_update` (see `system-variables.md`). Source: General Event Procedures; CAN CAPL Functions.

Dispatch rule: the most specific handler wins. If both `on message 0x100` and `on message *` exist, `0x100` handles ID 0x100 and `*` handles the rest (`*` is NOT also called for 0x100). The boxed form `on message [*]` is the exception: it ALWAYS runs, before the specific handler. Source: on message; Unconditional (Boxed) Event Procedures.

Special callbacks: some interfaces use named callback functions instead of `on` handlers (e.g. `OnTcpReceive` for TCP/IP). `OnSomething(...) {}` is a callback whose return type is implicitly `void`; look up its signature, do not guess.

## Lifecycle events

Order: `on preStart` -> `on start` -> (running) -> `on preStop` -> `on stopMeasurement`. `on preStart` runs before the bus is up: init only, NO `output()`. `on start` is where you send start values and arm timers. `on preStop` runs on a stop request; call `deferStop(ms)` to buy time for a shutdown handshake. Source: Events of the Measurement System.

```capl
// requires: simulation node + CAN bus context (for message/output/deferStop)
variables { long rxCount; }

on preStart       { rxCount = 0; }                 // init only -- bus not up yet
on start          { /* arm timers, send start values */ }

on preStop
{
  message 0x7FF shutdown;
  output(shutdown);
  deferStop(1000);   // postpone stop up to 1000 ms so the frame goes out
}

on stopMeasurement { write("received %d messages", rxCount); }
```

## on key

The key code is a character `'c'`, a numeric code `0x20`, or a predefined identifier. `on key *` reacts to every key; inside it `this` is the key code.

```capl
on key 'a'        { /* the letter a */ }
on key ' '        { /* spacebar (same as on key 0x20) */ }
on key F1         { /* function key F1 */ }
on key ctrlF12    { /* Ctrl+F12 */ }

on key *
{
  switch (this)        // this = pressed key code
  {
    case 'a': break;
    case F10: break;
  }
}
```

Identifiers: `F1`-`F12`, `shiftF1`-`shiftF12`, `ctrlF1`-`ctrlF12`, `PageUp`/`PageDown`, `Home`/`End`, `InsertKey`/`DeleteKey`, `CursorLeft/Right/Up/Down` (and `ctrl` variants). `<ESC>`, `<F7>`, `<F8>`, `<F9>` are NOT supported. Source: on key.

## CAN message and bus-event arrival

Filter forms for `on message` (decimal unless `0x`; trailing `x` = extended ID; `Chip.` prefix pins a channel):

```capl
on message 123        { }   // dec, standard ID 123
on message 0x123      { }   // hex standard ID
on message 0x123x     { }   // hex EXTENDED ID (trailing x)
on message EngineData { }   // by database name -- requires: DBC defining message EngineData
on message CAN1.123   { }   // only on CAN1 chip
on message 0,1,10-20  { }   // a list / range of IDs
on message *          { }   // all messages not handled more specifically
```

Inside the handler `this` is the received message. Read selectors, never assume:

```capl
// requires: CAN bus context (resetCanEx needs a CAN controller)
on message 0x100
{
  write("ID 0x%x, dlc %d, t %d", this.id, this.dlc, this.time);
}

on errorFrame
{
  write("error frame on channel %d", this.can);
}

on busOff
{
  write("bus off: errTx=%d errRx=%d", this.errorCountTX, this.errorCountRX);
  resetCanEx(this.can);
}
```

Source: on message; Events of the CAN Controller. (Signal value access via `this.<signal>` / `$`: see `messages-and-signals.md`.)

## on signal vs signal_change vs signal_update

```capl
// requires: DBC defining signal EngineSpeed
on signal EngineSpeed        { }   // fires only when the value CHANGES
on signal_change EngineSpeed { }   // identical to 'on signal'
on signal_update EngineSpeed { }   // fires on EVERY reception, even if unchanged
```

Use `on signal_update` when you must count or timestamp every frame carrying the signal; use `on signal` when only value transitions matter. This mirrors `on sysVar` vs `on sysVar_update` (see `system-variables.md`). Source: CAN CAPL Functions (Event Procedures).

## Timers: declare, start, handle

Two types: `timer` counts in SECONDS, `msTimer` in MILLISECONDS. Pick by interval (max for each: 2147483647 of its unit, ~596 h for ms, ~596523 h for s):

| Need | Type | Start call | Unit |
|---|---|---|---|
| 200 ms periodic tick | `msTimer` | `setTimer(t, 200)` | ms |
| 5 s timeout | `timer` | `setTimer(t, 5)` | s |
| sub-ms (ns) on a `timer` | `timer` | `setTimer(t, sec, ns)` | s + ns |

A timer MUST be declared in `variables {}` but armed in code (never in `variables {}`). One-shot by default: it fires `on timer` once. For a cyclic tick, either re-arm inside `on timer` or use `setTimerCyclic`. Source: on timer.

Two ways to get a periodic tick (pick ONE per timer -- do NOT combine on the same timer): a one-shot you re-arm inside `on timer`, or `setTimerCyclic`. Give every armed timer its own `on timer` handler.

```capl
variables
{
  msTimer tick;        // ms -- periodic via manual re-arm
  msTimer heartbeat;   // ms -- periodic via setTimerCyclic
  timer   slow;        // seconds -- one-shot
}

on start
{
  setTimer(tick, 200);            // one-shot: fire once in 200 ms (re-armed in its handler)
  setTimerCyclic(heartbeat, 200); // auto-repeat every 200 ms (no manual re-arm)
  setTimer(slow, 5);              // one-shot: fire once in 5 s
}

on timer tick
{
  // periodic work ...
  setTimer(tick, 200);            // MANUAL re-arm to keep it ticking
}

on timer heartbeat
{
  // periodic work ... (setTimerCyclic re-arms automatically -- do NOT re-arm here)
}

on timer slow
{
  // one-shot done; re-arm only if you need it again
}

on key 'c'
{
  cancelTimer(heartbeat);         // function form: stop an active timer
  heartbeat.cancel();             // method form (msTimer only) -- equivalent
}
```

Timer API (function form and method form). Source: setTimer, setTimerCyclic, cancelTimer, isTimerActive, timeToElapse, on timer.

| Call | Method form | Meaning |
|---|---|---|
| `setTimer(t, dur)` | `t.set(dur)` | arm one-shot; `dur` is s for `timer`, ms for `msTimer` |
| `setTimer(t, sec, ns)` | (none) | `timer` only: arm one-shot with seconds + nanoseconds |
| `cancelTimer(t)` | `t.cancel()` | stop an active timer (prevents `on timer`) |
| `isTimerActive(t)` | (none) | 1 if armed, else 0; returns 0 inside `on timer` |
| `timeToElapse(t)` | `t.timeToElapse()` | remaining time (s for `timer`, ms for `msTimer`); -1 if inactive |

Cyclic arming differs by timer type -- the units and the available forms are NOT the same:

| Timer | Call | Method form | Period unit |
|---|---|---|---|
| `msTimer` | `setTimerCyclic(t, period)` | `t.setCyclic(period)` | ms (first run also after `period`) |
| `msTimer` | `setTimerCyclic(t, first, period)` | `t.setCyclic(first, period)` | ms (first run after `first`, then every `period`) |
| `timer` | `setTimerCyclic(t, periodInNs)` | `t.setCyclic(periodInNs)` | **nanoseconds** (single period; no 3-arg form) |

Inside `on timer`, `this` is the timer; `this.name` (v7.2+) is its name as a string. The same timer firing more than once requires re-arming it.

### Timer arrays (v7.5+) -- supported

You CAN store timers in an array and share ONE handler across all of them (valid since v7.5). The handler takes a `dword index` parameter naming which element fired; inside it `this` is the WHOLE array, so index it as `this[index]`.

```capl
variables
{
  msTimer myTimers[10];
}

void armAll()                        // arm each timer individually
{
  dword i;
  for (i = 0; i < elcount(myTimers); ++i)
    myTimers[i].set(100 + 20 * i);   // 100 ms, 120 ms, 140 ms, ...
}

on timer myTimers(dword index)       // ONE handler for all elements of the array
{
  write("Timer %s [%d] fired", this[index].name, index);
  setTimer(this[index], 2000);       // re-arm just the element that fired
}
```

Source: on timer, "Version Extensions" (v7.5). NOTE: the `on timer arr(dword index)` header is valid and documented -- it compiles even though it can look like an invalid event format. Do NOT remove the parameter to "fix" it.

What is INVALID is a bracket index/wildcard IN THE EVENT SPECIFIER itself:

```capl
on timer myTimers[3] { }   // WRONG -- no index allowed in the specifier
on timer myTimers[*] { }   // WRONG -- no wildcard index in the specifier
```

Only a bare name (or the `(dword index)` parameter form above) is allowed after `on timer`. No expressions or calculations in any event specifier.

## Time functions and units (read the unit!)

The most common timing bug is treating `timeNow()` as milliseconds. It is NOT.

| Function | Returns | Unit |
|---|---|---|
| `timeNow()` | dword | **10 microseconds** (divide by 100000.0 for seconds) |
| `timeNowFloat()` | float | 10 microseconds |
| `timeNowNS()` / `timeNowInt64()` | nanoseconds | **nanoseconds** |
| `timeDiff(m1, now)` / `timeDiff(m1, m2)` | long | **milliseconds** between messages |

Source: timeNow, timeNowFloat, timeNowNS, timeDiff.

```capl
on message 0x100
{
  double tSec;
  tSec = timeNow() / 100000.0;   // CORRECT: timeNow is 10 us units -> /100000 = seconds
  write("now = %.3f s", tSec);
}
```

For per-frame timing of LIN frames, use the frame's own selectors (below), not `timeNow` deltas.

## LIN frames and frame timing

LIN frames arrive on `on linFrame <id|name|*>`, **not** `on message`. Read frame timing from the event's selectors rather than from `timeNow`/`timeNowNS` deltas. Mind the units -- the timestamp selectors are nanoseconds, the duration selectors are bit time:

| Selector | Meaning | Unit | Type |
|---|---|---|---|
| `this.SOF` | start-of-frame timestamp | ns | int64 |
| `this.EOH` | end-of-header timestamp | ns | int64 |
| `this.EOB[i]` | end-of-byte timestamp of data byte `i` (0..7) | ns | int64 |
| `this.LIN_HeaderTime` | header transmission duration | bit time | byte |
| `this.LIN_Fulltime` | full-event transmission duration | bit time | byte |

```capl
on linFrame *
{
  write("header took %d ns", this.EOH - this.SOF);
}
```

## Catch-all events

For the all-bus catch-all the event name is `*`. Inside `on *`, `this` is usable ONLY for `output(this)` and to read the timestamp (`this.time`) -- selectors like `this.id` are NOT available there. To read message selectors, use a bus-specific catch-all (`on message *`), where `this` is the message. A CAPL node in the analysis branch is NOT transparent: messages are blocked unless you forward them with `output(this)` in `on *` / `on message *` (beware recursion in a simulation node).

A bus-specific catch-all (e.g. `on ethernetPacket *`) DOES give `this` its full selector set:

```capl
// requires: Ethernet/TCP-IP stack context
on ethernetPacket *
{
  if (this.ipv6.IsAvailable())
  {
    // more code here
  }
}
```

## Anti-patterns (do NOT do these)

```capl
// WRONG -- timer started in variables{}. Declare here, arm in on start / a function.
variables { msTimer t = setTimer(t, 100); }

// WRONG -- index/wildcard in the event specifier (see Timer arrays for the valid form).
on timer myTimers[3] { }
on timer myTimers[*] { }

// WRONG -- expressions/calculations are not allowed in an event specifier.
on message (0x100 + gOffset) { }

// WRONG -- output() in on preStart; the bus is not up yet. Use on start.
on preStart { message 0x100 m; output(m); }

// WRONG -- assumes timeNow() is milliseconds; it is 10 us units (~100x off).
on timer t { write("%d ms elapsed", timeNow()); }
```

## Common Mistakes

### Array indexing or wildcard index in event specifier

```capl
// WRONG
on timer myTimers[3] { }
on timer myTimers[*] { }
```

```capl
// RIGHT
on timer myTimer { }
```

CAPL event specifiers only accept a single, plain variable name. Array element access and wildcard indices are not supported in the specifier position.

### Expression or calculation in event specifier

```capl
// WRONG
on message (0x100 + 1) { }
```

```capl
// RIGHT
on message 0x100 { }
on message MotorStatus { }
on message * { }
```

The event specifier must be a literal constant, a symbolic name, or `*`. Arithmetic expressions and parenthesised sub-expressions are not evaluated and will cause a compiler error.

### Starting a timer inside the `variables` block

```capl
// WRONG
variables
{
    timer myTimer;
    setTimer(myTimer, 1000); // NOT allowed here
}
```

```capl
// RIGHT
variables
{
    timer myTimer;
}

on start
{
    setTimer(myTimer, 1000);
}
```

The `variables` block is a declaration section; no executable statements are permitted there. Timers must be started from an event handler or a callable function.

### Handling a timer that was never declared in `variables`

```capl
// WRONG — timer used without declaration
on start
{
    setTimer(localTimer, 500); // localTimer not declared in variables {}
}

on timer localTimer { }
```

```capl
// RIGHT
variables
{
    msTimer localTimer;
}

on start
{
    setTimer(localTimer, 500);
}

on timer localTimer { }
```

Every timer used in an `on timer` handler or passed to `setTimer` / `cancelTimer` must be declared in the `variables` block; locally-scoped timer variables are not supported as event specifiers.

### Confusing `timer` (seconds) with `msTimer` (milliseconds)

```capl
// WRONG — expecting a 200 ms delay but using timer (seconds)
variables { timer myTimer; }

on start { setTimer(myTimer, 200); } // fires after 200 SECONDS
```

```capl
// RIGHT
variables { msTimer myTimer; }

on start { setTimer(myTimer, 200); } // fires after 200 ms
```

`timer` counts in seconds and `msTimer` counts in milliseconds. Mixing them up produces delays that are 1000x longer than intended and is a common source of hard-to-spot timing bugs.
