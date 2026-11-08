# Offline timing checker

Use `scripts/check_timing.py` for the narrow binary transition requirement below. It uses Python 3.10+ and the standard library, reads a local CSV, writes JSON to stdout, and never connects to CANalyzer or a bus. It does not decode BLF/ASC, DBC or ARXML.

## Required evidence and semantics

- Columns must be exactly `time_s,trigger,response`, in that order; UTF-8 with optional BOM. Signal values must be `0` or `1`. Timestamps are nonnegative decimal seconds, strictly increasing, with at most 15 significant digits, magnitude below 1e13 and up to 9 decimal places. Normalize units before use.
- Each row is a simultaneous state of both signals. The first row establishes initial state; it cannot establish an edge. A response rising in the same row as a trigger has zero delay. If actual event ordering at a shared timestamp matters, this format cannot resolve it.
- All changes must be present, with valid values held between rows and no capture gaps. Periodically sampled data alone cannot establish that no transition happened between samples. Do not use this checker for such data, invalid/sentinel values, or unknown export semantics.
- Every observed trigger 0→1 requires a response 0→1 within a positive configured window, inclusive. A response already high is insufficient. Retriggers at or before the preceding deadline are rejected rather than assigned an arbitrary overlap policy.
- The final row is the end of available evidence. A missing on-time response is Fail only when the complete deadline is captured; otherwise Inconclusive. There is no extrapolation beyond the final row. A late transition is reported up to, but excluding, the next trigger.

`--complete-event-export` asserts these export semantics; the script cannot verify completeness from the CSV. Establish this from capture/export metadata before running it. Keep channel, frame identity, signal mapping, sampling and conversion provenance alongside the result: those are absent from this normalized CSV.

## Run from an installed skill

```text
python /path/to/canalyzer-15-assistant/scripts/check_timing.py export.csv --window-ms 500 --complete-event-export
```

Use `python3` or `py -3` if that is the Python 3 command in the environment. Decimal timestamp and delay fields are JSON strings to preserve exact inclusive-boundary comparisons.

Exit status: 0 = all observed triggers Pass; 1 = at least one Fail (possibly also Inconclusive); 2 = Inconclusive without Fail, including no observed triggers; 3 = invalid/unsupported input or file error. Argument syntax errors use argparse's status 2 and emit no report. Read counts and individual checks as well as the overall result; a file with no observed triggers never proves the requirement passed.

The checker verifies this analysis rule only. It does not verify CANalyzer 15 SP5 runtime compatibility, CAPL compilation, license capabilities or physical bench behavior.
