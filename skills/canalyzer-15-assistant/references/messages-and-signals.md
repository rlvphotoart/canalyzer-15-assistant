# Messages and Signals

Owns CAN message construction, transmission, message-data selectors, signal value access (`$` and function forms), ID types, CAN FD, signal limits, and qualification.
See data-types-reference.md for `byte`/`word`/`dword` sizes and `.phys`. See events-and-timers.md for `on message` / `on signal` dispatch and timing.

## Decision matrix (read first)

| I want to ... | Use | Notes |
|---|---|---|
| Send a message at a point decided by control flow (key press, after a check) | `message` variable + `output()` | Set signals on the **instance** (`status.rpm.phys = ...`; bare `status.rpm` is raw), then `output(status)`. |
| Set a signal for the next **cyclic** send handled by the IL | `$Signal = value;` | Do NOT use `$` to fill a message you then `output()` — see anti-pattern below. |
| Read the latest received value of a signal | `$Signal` or `getSignal(Signal)` | `$` needs the name at compile time; `getSignal` takes a `Signal` object. |
| Access a signal whose name is only known at **runtime** (or built as a string) | `lookupSignal("…")` -> `signal *`, then `$handle` | Resolve once (ideally at measurement start), then read/write via `$handle`. See *Runtime signal lookup* below. |
| Read/write a signal wider than 32 bits | `$Signal.raw64`, `GetRawSignal`/`SetRawSignal` | The plain `$Signal` (double) cannot hold > 52 significant bits. |
| Read raw bytes of a received frame | `this.byte(n)` / `this.word(n)` ... in `on message` | Guard with `if (this.dir != rx) return;`. |
| Resolve a non-unique signal/message name | qualify: `Node::Signal`, `Channel::Node::Signal` | Applies to both `$` and the function forms. |

CAPL looks like C but is not C: a database signal is not a variable, message data is accessed through selector *functions* like `byte(0)`, and message-instance signal members (`status.rpm`) are resolved by the compiler against the DBC.

## Creating Message variables

```capl
message <id> <variable_name>;
message <msg_name> <variable_name>;
```

Where `<id>` is the hexadecimal CAN identifier or `msg_name` is the name of a defined message in the DBC database.
Where `<variable_name>` is the name of the variable you want to use for the message instance.

Messages can be initialized in the `variables` block:

```capl
variables
{
  message 0x100 msg = { dlc = 1 };
}
```

Alternatively, their values can be set after their declaration:

```capl
variables
{
  message 0x100 msg;
}

on start
{
  // Example, can also be set in other blocks (including `variables` block)
  msg.dlc = 1;
}
```

### Channel- and database-qualified declarations

Qualify the declaration when the same ID/name exists on more than one channel or database. The channel qualifier uses a **dot** (`CAN2.`), not `::`. `message CAN2::0x125 …` is a parse error. The dot form may be combined with an aggregate initializer.

```capl
// requires: a CAN database / channel context (compiles inside a CANoe CAN node)
variables
{
  message CAN2.0x125 ctrl = { dlc = 8 };   // 0x125 on channel CAN2 (dot, not ::)
  message CAN1.EngineData eng;             // database message, bound to CAN1
}
```

This is the declaration-side counterpart of the `$Channel::Node::Signal` qualification used for signal access (see *Signal Qualification* below). Note the asymmetry: declarations qualify the channel with a dot (`CAN2.id`), `$`-signal access uses `::` (`$CAN2::Node::Signal`). Source: output (CAN), on message.

## Accessing Message Data

```capl
message 0x100 msg;

msg.byte(0) = 0xFF;  // Access first byte
msg.word(2) = 0xABCD;  // Access 2 bytes starting at byte offset 2 (bytes 2 and 3)
msg.long(4) = 0x12345678;  // Access 4 bytes starting at byte offset 4 (bytes 4 through 7)
msg.dlc = 8;  // Set data length code
```

The index passed to every data selector is **byte-oriented**, not element-oriented: `word(1)` starts at byte 1 and spans bytes 1..2; `long(1)` spans bytes 1..4. See the full selector table below for valid index ranges per width.

## Symbolic Signal Access

A database signal is **not** a CAPL variable. Read/write its value with `$`-notation: `$EngineTemp = 80; x = $EngineTemp;` (or `setSignal`/`getSignal`). Writing the bare name (`FeedbackSignal = timePoint;`) does not compile. For signals wider than 32 bits, avoid plain `$Signal` (a double loses precision above 52 bits): use `$Signal.raw64` when the name is statically known, or `GetRawSignal`/`SetRawSignal` for a function/handle form.

Use this notation to get the latest value or to set the value of a signal for the next transmission.

```capl
// Reading signal value
value = $EngineSpeed;  // Physical value
value = $EngineSpeed.raw;  // Raw value
value = $EngineSpeed.raw64;  // Raw value for signals > 52 bits

// Setting signal value
$EngineSpeed = 500.0;  // Set physical value
$EngineSpeed.raw = 1000;  // Set raw value
```

To send a message on the bus at a control-flow point (not cyclic), use a message variable and `output`: declare the variable, set the signals on the **instance**, then call `output`. Do **not** use `$Signal` to fill an instance you then `output()` (see the anti-pattern under *Signal Qualification*). See *Sending a message* below for the canonical `MotorStatus` example.

### Function-form signal access (`getSignal` / `setSignal` family)

The `$` form needs the signal name fixed at compile time. The function form takes a `Signal` object and is the right choice when you resolve ambiguous names, read the raw value of a wide signal, or query the last-sent time. The recommended (compiled) form is form 1 — pass the signal symbol directly; the runtime environment is faster because the signal object is resolved at compile time. Source: Signal Access CAPL Functions.

| Function | Signature (form 1) | Use |
|---|---|---|
| `getSignal` | `float getSignal(Signal s)` | Latest physical value; returns the DB start value if not yet on the bus. |
| `setSignal` | `void setSignal(Signal s, double v)` | Set physical value for the next (cyclic) transmission. |
| `GetRawSignal` | `int64 GetRawSignal(dbSignal s)` | Raw value; form 2 `(s, byte data[], dword len)` for signals > 32 bits. |
| `SetRawSignal` | `long SetRawSignal(dbSignal s, int64 v)` | Set raw value; form 2 `(s, byte data[], dword len)` for > 32-bit signals. |
| `getSignalTime` | `dword getSignalTime(Signal s)` | Time (units: 10 us) the signal was last sent; `0` if never sent. |

```capl
variables
{
  message MotorStatus status;
}

void demoSignalAccess()
{
  float v;
  dword t;
  int64 rawVal;   // 'raw' is a reserved selector keyword; use a different local name

  v = getSignal(MotorStatus::rpm);     // physical value (ambiguity resolved by Node::Signal)
  setSignal(MotorStatus::rpm, 3000.0); // set physical value
  rawVal = GetRawSignal(MotorStatus::rpm);
  SetRawSignal(MotorStatus::rpm, 1000);
  t = getSignalTime(MotorStatus::rpm); // last-sent time, 0 if never sent
  write("v=%f raw=%d t=%d", v, rawVal, t);
}
```

```capl
// CORRECT — wide signal (> 32 bits): use the raw64 / Raw functions, not plain $Signal
raw64Val = $WideCounter.raw64;
SetRawSignal(MyMsg::WideCounter, raw64Val);

// WRONG — plain $Signal is a double; it silently loses precision above 52 significant bits
x = $WideCounter;            // WRONG — use .raw64 / GetRawSignal for > 32-bit signals
```

### Runtime signal lookup (`lookupSignal` / `signal *` / `$handle`)

`$Signal` and `getSignal(Signal)` need the name **at compile time**. When the name is only known at runtime (built from a string, chosen by config), resolve it with `lookupSignal` into a `signal *` handle, then read/write via `$handle`. Source: lookupSignal.

| Form | Signature | Use |
|---|---|---|
| Compile-time symbol | `$Signal`, `getSignal(Signal)` | Name fixed in source; fastest (resolved at compile time). |
| Runtime / non-unique name | `signal * lookupSignal(char name[])` | Name built/chosen at runtime; the string is the qualified name (see below). |
| From a `dbSignal` (generic) | `lookupSignal(dbSignal)`, `lookupSignal(dbSignal, dbNode)` | Program generically; form 3 picks the sender when several nodes send it (e.g. J1939). |

The string is qualified right-to-left: `[Channel::][Database name (alias)::][Node::][Message::]Signal`. Include the database name (drag-and-drop from the Symbol Explorer omits it). If the name is missing or not unique, `lookupSignal` returns an invalid signal (test modules error; analysis nodes warn) — so qualify enough to be unique. Calling it on every event hurts realtime performance; resolve once at measurement start.

```capl
// requires: a database whose signal "LightSwitch" exists (compiles inside a CANoe node)
variables
{
  signal * gSwitch;   // runtime-resolved handle
}

on start
{
  gSwitch = lookupSignal("LightSwitch");   // qualify further if not unique: "DB::Node::Msg::Signal"
  $gSwitch = 1;                            // write via the handle
}

on key 'r'
{
  double v;
  v = $gSwitch;                            // read via the handle
  write("LightSwitch = %g", v);
}
```

### Physical vs raw on a message instance

On a message **instance**, the bare member `<instance>.<signal>` reads/writes the **raw** (unscaled bus) value; `<instance>.<signal>.phys` reads/writes the scaled physical value. There is no `.raw` selector on a message instance (`status.rpm.raw` / `this.rpm.raw` fail with "Invalid expression") — `.raw` only exists on `$`-access (`$Signal.raw`).

```capl
variables
{
  message MotorStatus status;
}

void showRawPhys()
{
  double phys;
  int64 rawVal;            // 'raw' is a reserved selector keyword; use a different local name
  phys = status.rpm.phys;  // physical (factor/offset applied)
  rawVal = status.rpm;      // bare member = raw bus value (no .raw on an instance)
  write("phys=%g raw=%d", phys, rawVal);
}
```

```capl
// WRONG — the bare member is RAW; a physical number written to it is stored unscaled.
status.rpm = 3000.0;   // WRONG — stores raw 3000, not 3000 rpm; use status.rpm.phys = 3000.0;
status.rpm.raw = 1000; // WRONG — does not compile ("Invalid expression"); bare status.rpm is already raw
```

**Pitfall — silent float truncation:** assigning a floating-point value to a bare message-instance signal truncates it to a raw integer with **no compiler warning**. With factor 0.1, `msg.Voltage = 12.6;` stores raw `12`, i.e. 1.2 V on the bus. Always write physical values via `.phys` (`msg.Voltage.phys = 12.6;`). When reviewing code, treat a bare `msg.Signal = <physical value>` as a bug unless the signal's factor is 1 and offset is 0.

```capl
// requires: DBC message BatteryStatus with signal Voltage (factor 0.1, offset 0)
variables
{
  message BatteryStatus msg;
}

void sendVoltage()
{
  msg.Voltage = 12.6;       // WRONG — truncated to raw 12 -> 1.2 V, no warning
  msg.Voltage.phys = 12.6;  // CORRECT — raw 126 -> 12.6 V
  output(msg);
}
```

### Initializing signals to their database start values

`setSignalStartValues(msg)` fills every signal in a message instance with the start value defined in the database (returns `0` on success, `1` if the message is not in the DB, `2` if a start value did not fit). Source: setSignalStartValues.

```capl
variables
{
  message MotorStatus status;
}

void initStartValues()
{
  long r;
  r = setSignalStartValues(status);
  if (r != 0)
    write("setSignalStartValues failed, code=%d", r);
  output(status);
}
```

## Sending a message (Tx via control flow)

`output(message msg)` transmits a message instance. Set the data on the instance first, then call `output`. This is the **canonical** control-flow Tx example referenced elsewhere in this file. Source: output (CAN).

```capl
// requires: a DBC with message `MotorStatus` (signal `rpm`), inside a CANoe CAN node
// Send a `MotorStatus` message with rpm = 3000 at this point in control flow.

message MotorStatus status;
status.rpm.phys = 3000;   // .phys = physical; bare status.rpm would be raw

output(status);
```

## Receiving a message (Rx via `on message`)

Inside `on message`, the keyword `this` is the received frame. Read data with the same selectors used for Tx (`this.byte(n)`, `this.word(n)`, `this.dlc`, `this.id`, `this.CAN`). A CAPL node in the evaluation branch does **not** forward frames automatically. Always guard with the direction selector. (For full dispatch syntax — `on message 0x123`, ID ranges, `CAN1.*` — see events-and-timers.md.) Source: on message.

```capl
// requires: a CAN database / channel context (compiles inside a CANoe CAN node)
variables
{
  message CAN2.0x125 ctrl = { dlc = 8 };   // dot, not :: (the :: form is a parse error)
}

void sendCtrl()
{
  ctrl.byte(0) = 0xFF;
  ctrl.word(1) = 0xABCD;
  ctrl.long(4) = 0x12345678;
  output(ctrl);
}

on message EngineData
{
  if (this.dir != rx) return;   // important: ignore our own Tx echo
  if (this.CAN != 1) return;    // optional: only frames received on CAN1
  write("ch=%d dlc=%d b0=%d", this.CAN, this.dlc, this.byte(0));
}
```

```capl
// WRONG — no direction guard: the handler also fires on the frame you transmit, causing double counting / echo loops
on message EngineData
{
  write("b0=%d", this.byte(0));  // WRONG — fires on Tx echoes too; add: if (this.dir != rx) return;
}
```

## CAN Message Selectors

Access control information and data of a CAN message object (instance or `this`) with these selectors. The data-access index is **byte-oriented**; the maximum index shrinks as the access width grows. Source: CAN Message Selectors.

| Selector | Meaning | Type |
|---|---|---|
| `CAN` / `MsgChannel` | Channel the frame was sent/received on (1..32) | word |
| `ID` | Message identifier | dword |
| `name` | Unqualified symbolic name from the database | char[] (read only) |
| `DIR` | Direction: `Rx`, `Tx`, `TXREQUEST` | byte |
| `RTR` | Remote Transmission Request: 0 / 1 | byte |
| `TYPE` | `(RTR << 8) \| DIR` | word |
| `DLC` | Data Length Code (Classic/FD: 0..15) | byte |
| `DataLength` | Data length in bytes | byte |
| `TIME` | Timestamp, units 10 us | dword |
| `TIME_NS` | Timestamp, units ns | int64 (read only) |
| `FDF` | FD format: 0 = Classic, 1 = CAN FD | char |
| `BRS` | Bitrate switch (FD only): 0 / 1 | char |
| `ESI` | Error State Indicator (FD only) | char |

Data-access selectors (index `x` is a byte offset):

| Selector | Reads/writes | Signed? | Valid `x` |
|---|---|---|---|
| `byte(x)` | 8 bit | unsigned | 0..63 |
| `char(x)` | 8 bit | signed | 0..63 |
| `word(x)` | 16 bit | unsigned | 0..62 |
| `int(x)` | 16 bit | signed | 0..62 |
| `dword(x)` | 32 bit | unsigned | 0..60 |
| `long(x)` | 32 bit | signed | 0..60 |
| `qword(x)` | 64 bit | unsigned | 0..56 |
| `int64(x)` | 64 bit | signed | 0..56 |
| `float(x)` | IEEE float (32 bit) | — | 0..60 |
| `double(x)` | IEEE double (64 bit) | — | 0..56 |

```capl
// WRONG — index out of range for the access width. word() is valid 0..62; byte 63 has no second byte.
on message EngineData
{
  word w;
  w = this.word(63);  // WRONG — word(x) max index is 62 (would read past byte 63)
}
```

## Standard vs Extended identifiers

CAN IDs are 11-bit (standard) or 29-bit (extended). In `on message` filters and ID literals, append `x` for extended (`123x`, `0x18DAF110x`). Programmatically, build/inspect IDs with these functions. Source: CAN CAPL Functions (General Functions), mkExtId, isStdId/isExtId, valOfId.

| Function | Signature | Returns |
|---|---|---|
| `mkExtId` | `dword mkExtId(dword id)` | The id marked as extended (29-bit). |
| `isExtId` | `long isExtId(dword id)` / `long isExtId(message m)` | 1 if extended, else 0. |
| `isStdId` | `long isStdId(dword id)` / `long isStdId(message m)` | 1 if standard, else 0. |
| `valOfId` | `long valOfId(message m)` / `long valOfId(dword id)` | Numeric id value, independent of std/ext type. |

```capl
variables
{
  message 0x18DAF110x req;   // 'x' suffix = extended-id literal
}

on message *
{
  if (isExtId(this))
    write("extended id, value=0x%x", valOfId(this));
  else
    write("standard id, value=0x%x", valOfId(this));
}

void sendExtended()
{
  req.id = mkExtId(0x100);   // force the id to be sent as extended
  output(req);
}
```

## CAN FD

For a CAN FD frame, set `FDF` (FD format) and `BRS` (faster data-phase bitrate). A CAN FD DLC encodes more than 8 bytes: DLC 9..15 map to 12/16/20/24/32/48/64 data bytes (DLC 15 = 64 bytes). `canGetDataLength(msg)` returns the actual valid payload length (0..64). The selectors `FDF`/`BRS`/`ESI` are typed `char`. Cast the literal: `fd.FDF = (char) 1;` (or assign from a `char` variable); a bare `fd.FDF = 1;` is an int->char type mismatch. CAPL does have scalar `(type)` casts — see [data-types-reference.md](data-types-reference.md) for when to cast vs use `.phys`/`.raw`/typed helpers. Source: CAN Message Selectors, canGetDataLength.

```capl
variables
{
  message MyFdMsg fd;   // an FD message defined with up to 64 data bytes in the DBC
}

void sendFd()
{
  long len;
  fd.FDF = (char) 1;   // FD format (FDF/BRS/ESI are char; cast the literal)
  fd.BRS = (char) 1;   // use FD bitrate for the data phase
  fd.dlc = 15;         // DLC 15 maps to 64 data bytes on CAN FD
  fd.byte(63) = 0xAA;  // valid: byte index goes up to 63 on a 64-byte frame
  len = canGetDataLength(fd);
  output(fd);
  write("valid payload length = %d", len);
}
```

```capl
// WRONG -- bare int literal: fd.FDF = 1; is an int->char type mismatch
fd.FDF = 1;          // WRONG -- cast it: fd.FDF = (char) 1; (or assign from a char variable)
```

## Signal Qualification (for resolving ambiguities)

When signal or message names are not unique across the database or network, qualify them:

```capl
// Node::Signal
value = $ECU1::Temperature;

// Node::Message::Signal
value = $BodyControl::ClimateStatus::FanSpeed;

// Channel::Node::Signal (e.g., CAN1, CAN2)
value = $CAN1::Gateway::VehicleMode;

// Network::Node::Signal (e.g., Ethernet)
value = $Ethernet::Camera1::FrameCounter;
```

When a signal or message name is not unique across databases (common on LIN with per-node fault signals), qualify the `$`-access with the owning node/database — `$BMS::FaultFlagVoltage = 1;` — rather than a bare or locally-declared `$FaultFlagVoltage`. If ownership is unknown, state the assumption instead of inventing one.

The function forms take the same qualification: `getSignal(LightSwitch::OnOff)`, `setSignal(CAN1::Status, 1)`. Source: getSignal, SetSignal.

These get the latest value of the signal or set the value of the signal for the next cyclic send. Do NOT use these to send a message via control flow — use a message variable and `output` as shown in *Sending a message* above (set the value on the `status` instance, not via `$`).

This is the anti-pattern and MUST be avoided:

```capl
message MotorStatus status;
$MotorStatus::rpm = 3000; // This is wrong when sending a message via the control flow. `status.rpm` is not changed!

output(status); // rpm value is not set and garbage is send!
```

## DBC introspection

Look up message metadata from the loaded database at runtime. Source: CAN CAPL Functions (CANdb API), getMessageID, getMessageName, getSignalName.

| Function | Signature | Returns |
|---|---|---|
| `getMessageID` | `dword getMessageID(char name[])` (form 2 adds `char dbName[]`) | Message ID, or `(dword)-1` if not found. |
| `getMessageName` | `dword getMessageName(dword id, dword context, char buf[], dword size)` | Writes the name into `buf`; non-zero on success. `context` = (busSystem << 16) \| channel; CAN bus system = 1. |
| `getSignalName` | `char[] getSignalName(caplCanMessage* msg, dword startBit)` | Signal name at a start bit inside the message. |

```capl
void introspect()
{
  dword id;
  char buffer[64];
  id = getMessageID("MotorStatus");
  if (getMessageName(id, 0x00010000 | 1, buffer, elcount(buffer)))   // context: CAN (1) on channel 1
    write("name=%s id=0x%x", buffer, id);
}
```

## Signal Limit

Each signal has members to check signal limits and different other properties. They are located under `<sig>.<attribute>`. These limits / properties exists:

- `factor` for conversion
- `offset` for conversion
- `unit` this is a string
- `maximum` physical maximum
- `minimum` physical minimum

```capl
// This example assumes that a message MotorStatus is defined in the DBC including rpm as signal.
// We want to send the a MotorStatus message with the rpm signal set to the minimum end afterwards
// maximum at the start of the measurement.

variables
{
  message MotorStatus status;
}

on start
{
  status.rpm.phys = status.rpm.minimum; // The DBC minimum is in physical units; .phys converts it to the raw value sent on the bus.
  output(status);

  status.rpm.phys = MotorStatus.rpm.maximum; // note this uses the message `MotorStatus` itself.
  output(status);
}
```

## Anti-pattern quick reference

| WRONG | Why | Correct |
|---|---|---|
| `FeedbackSignal = x;` | Bare signal name is not a variable; does not compile. | `$FeedbackSignal = x;` or `setSignal(FeedbackSignal, x);` |
| `x = $WideCounter;` for a > 32-bit signal | `$Signal` is a double; loses precision above 52 bits. | `$WideCounter.raw64` / `GetRawSignal` |
| `$MotorStatus::rpm = 3000; output(status);` | `$` does not change the `status` instance; garbage is sent. | `status.rpm.phys = 3000; output(status);` |
| `status.rpm = 3000.0;` / `msg.Voltage = 12.6;` | The bare instance member is **raw**; a physical/float value is stored unscaled and truncated to an integer — no compiler warning. | `status.rpm.phys = 3000;` (physical) or assign the correct raw integer. |
| `status.rpm.raw` / `this.rpm.raw` | `.raw` is not a message-instance selector; "Invalid expression". | Bare `status.rpm` (raw) or `$Signal.raw`. |
| `this.word(63)` | Index out of range; `word(x)` valid only 0..62. | Use a valid index for the access width. |
| `fd.FDF = 1;` | `FDF`/`BRS`/`ESI` are `char`; the bare `int` literal is a type mismatch. | `fd.FDF = (char) 1;` (cast, or assign from a `char` variable) |
| `on message X { ... }` with no `dir` guard | Handler also fires on transmitted echoes. | `if (this.dir != rx) return;` first. |

## Common Mistakes

### Using `$Signal` assignment instead of message-instance + `output()`

WRONG:
```capl
message MotorStatus status;
$MotorStatus::rpm = 3000; // Does NOT write into `status`

output(status); // rpm is uninitialized — garbage is sent
```

RIGHT:
```capl
message MotorStatus status;
status.rpm.phys = 3000; // Write the physical value into the message-instance variable

output(status); // Sends the message with rpm = 3000
```

`$Signal = X` updates the value used for the next *cyclic* transmission managed by CANoe; it has no effect on a separately declared message variable. Always set fields on the message instance and call `output()` when you need to send a message at a specific point in the control flow.

### Forgetting to set `dlc` before calling `output()`

WRONG:
```capl
message 0x200 msg;
msg.byte(0) = 0xAB;

output(msg); // dlc defaults to 0 — no payload bytes are transmitted
```

RIGHT:
```capl
message 0x200 msg;
msg.dlc = 1;
msg.byte(0) = 0xAB;

output(msg); // Transmits one data byte as intended
```

If `dlc` is not explicitly set (and not initialised in the `variables` block), it defaults to `0`, so the receiver sees an empty frame even though you wrote data bytes into the variable.

### Reading a signal via `$Signal` and expecting it to reflect a value just written to a message variable

WRONG:
```capl
message MotorStatus status;
status.rpm.phys = 5000;
output(status);

value = $MotorStatus::rpm; // May still return the old bus value, not 5000
```

RIGHT:
```capl
message MotorStatus status;
status.rpm.phys = 5000;
output(status);

value = status.rpm.phys; // Reads the physical value from the local message instance
```

`$Signal` reflects the latest value *received from the bus* (or set for cyclic transmission). Reading it immediately after `output()` does not guarantee you see the value you just sent — use the message-instance field instead.

### Using an unqualified signal name when the same signal exists in multiple messages or nodes

WRONG:
```capl
value = $Temperature; // Ambiguous if Temperature exists in several messages/nodes
```

RIGHT:
```capl
value = $ECU1::Temperature;          // Qualified by node
value = $BodyControl::Climate::Temp; // Qualified by node and message
```

When a signal name is not unique across the loaded databases, CANoe may silently resolve to the wrong signal or raise a compile error. Always qualify the path to the degree needed to make the reference unambiguous.
