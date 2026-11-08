#!/usr/bin/env python3
"""Check complete, decoded binary signal event exports; no CANalyzer access."""

import argparse
import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def number(value, label):
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{label}: expected a finite decimal") from exc
    if not result.is_finite():
        raise ValueError(f"{label}: expected a finite decimal")
    # Bound precision so Decimal arithmetic stays exact at supported magnitudes.
    if (len(result.as_tuple().digits) > 15 or result.adjusted() > 12
            or result.as_tuple().exponent < -9 or result.as_tuple().exponent > 12):
        raise ValueError(f"{label}: use at most 15 digits, magnitude < 1e13, and 9 decimal places")
    return result


def read_samples(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != ["time_s", "trigger", "response"]:
            raise ValueError("expected exactly the CSV columns: time_s,trigger,response")
        samples = []
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"row {line}: missing or extra fields")
            time = number(row["time_s"], f"row {line} time_s")
            if time < 0 or (samples and time <= samples[-1][0]):
                raise ValueError(f"row {line}: timestamps must be nonnegative and strictly increasing")
            if row["trigger"] not in ("0", "1") or row["response"] not in ("0", "1"):
                raise ValueError(f"row {line}: signals must be exactly 0 or 1")
            samples.append((time, int(row["trigger"]), int(row["response"])))
    if len(samples) < 2:
        raise ValueError("at least two rows are required, including an initial state")
    return samples


def analyze(samples, window):
    """Rows are simultaneous states; every transition is present, without gaps."""
    triggers = []
    responses = []
    for previous, current in zip(samples, samples[1:]):
        if previous[1] == 0 and current[1] == 1:
            triggers.append(current[0])
        if previous[2] == 0 and current[2] == 1:
            responses.append(current[0])
    for earlier, later in zip(triggers, triggers[1:]):
        if later <= earlier + window:
            raise ValueError("overlapping trigger windows are unsupported (including a retrigger at the deadline)")
    end = samples[-1][0]
    checks = []
    response_index = 0
    for index, trigger in enumerate(triggers):
        deadline = trigger + window
        next_trigger = triggers[index + 1] if index + 1 < len(triggers) else None
        while response_index < len(responses) and responses[response_index] < trigger:
            response_index += 1
        response = responses[response_index] if response_index < len(responses) else None
        if response is not None and next_trigger is not None and response >= next_trigger:
            response = None
        if response is not None and response <= deadline:
            result, reason = "Pass", "response transition within inclusive deadline"
        elif end >= deadline:
            result, reason = "Fail", "deadline fully observed without an on-time response transition"
        else:
            result, reason = "Inconclusive", "capture ended before deadline"
        checks.append({
            "trigger_s": str(trigger), "deadline_s": str(deadline),
            "response_s": str(response) if response is not None else None,
            "delay_ms": str((response - trigger) * 1000) if response is not None else None,
            "observed_until_s": str(min(end, deadline)),
            "result": result, "reason": reason,
        })
    counts = {name: sum(c["result"] == name for c in checks)
              for name in ("Pass", "Fail", "Inconclusive")}
    overall = ("Fail" if counts["Fail"] else
               "Inconclusive" if counts["Inconclusive"] or not checks else "Pass")
    return {
        "scope": "offline decoded signal analysis; no CAPL compilation or bench validation",
        "capture_start_s": str(samples[0][0]), "capture_end_s": str(end),
        "window_ms": str(window * 1000), "trigger_count": len(checks),
        "counts": counts, "conclusive_count": counts["Pass"] + counts["Fail"],
        "overall": overall, "checks": checks,
        "initial_trigger_high": samples[0][1] == 1,
        "notes": ["The first row establishes state; an initial high is not a proven rising edge.",
                  "Assumes every signal change is recorded, with valid held values and no capture gaps.",
                  "A late response is associated only until the next trigger."],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--window-ms", required=True, help="positive inclusive response deadline in milliseconds")
    parser.add_argument("--complete-event-export", action="store_true", required=True,
                        help="assert all changes are recorded, values hold between rows, and no invalid values/gaps exist")
    args = parser.parse_args(argv)
    try:
        window_ms = number(args.window_ms, "window-ms")
        if window_ms <= 0:
            raise ValueError("window-ms must be positive")
        report = analyze(read_samples(args.csv_path), window_ms / 1000)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(report, indent=2))
    return {"Pass": 0, "Fail": 1, "Inconclusive": 2}[report["overall"]]


if __name__ == "__main__":
    sys.exit(main())
