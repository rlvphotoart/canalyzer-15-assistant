# Synthetic timing check

This is a synthetic decoded signal export, not a real CAN capture. Timestamps are seconds. Rows record every change in either signal plus explicit observation samples; values remain valid until the next row. There are no invalid values or missing samples within the capture. Capture ends at 4.200 s.

## Requirement

Each rising edge of `trigger` starts an independent observation window. `response` must transition from 0 to 1 at or before trigger time + 0.500 s. No retriggers occur inside a window. A response already at 1 at the trigger does not satisfy the transition requirement. Missing response before a complete deadline is Fail; capture ending before the deadline is Inconclusive.

## Prompt

Use $canalyzer-15-assistant to analyze `timing-check.csv` using this requirement and these export semantics. Report each trigger, response delay and outcome, with evidence. Do not generate or transmit bus traffic.

## Expected findings

| Trigger time | Response time | Delay | Result |
| --- | --- | --- | --- |
| 1.000 s | 1.320 s | 320 ms | Pass |
| 2.000 s | 2.500 s | 500 ms | Pass: inclusive boundary |
| 3.000 s | 3.600 s | 600 ms | Fail: deadline expired at 3.500 s |
| 4.000 s | Not observed | Only 200 ms captured | Inconclusive |

Totals: 2 Pass, 1 Fail, 1 Inconclusive; 4 triggers. Of the 3 conclusive checks, 2 passed (66.7%). This exercise verifies analysis semantics, not CAPL compilation or CANalyzer runtime compatibility.

## Reproduce with the offline checker

From the repository root, using Python 3.10+:

```sh
python3 skills/canalyzer-15-assistant/scripts/check_timing.py examples/timing-check.csv --window-ms 500 --complete-event-export
```

The JSON includes every trigger, deadline, response transition, delay, observed window end and outcome. Exit status is 1 because this fixture intentionally includes a Fail. The completeness assertion is justified by the synthetic export semantics above; establish those semantics separately before using a real export. See [the full input contract](../skills/canalyzer-15-assistant/references/offline-timing.md).
