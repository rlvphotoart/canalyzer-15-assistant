# CANalyzer 15 Assistant

AI skill for CAPL assistance, trace analysis and automotive bench validation with Vector CANalyzer 15.

Maintained by Radu Luca Victor. Independent adaptation using selected MIT-licensed references from Vector's CANoe AI Package 1.0.2. Not an official Vector product.

## What it helps with

- Translate validation requirements into explicit triggers, timing windows and acceptance criteria.
- Draft, review and debug CAPL programs with version and license checks.
- Analyze supplied BLF, ASC or CSV captures; interpret signals using a matching DBC/ARXML or explicit mapping.
- Explain Measurement Setup, Trace filters, logging and offline replay.
- Produce evidence-based findings with timestamps and Pass, Fail or Inconclusive outcomes.

## Compatibility and validation status

| Component | Status |
| --- | --- |
| CANalyzer 15 | Intended target; exact service pack, variant and bus options must be checked |
| CANalyzer 15 SP5 | User-reported target; not compiled or bench-tested by this project |
| CAPL execution | Requires a compatible license/variant; do not assume /fun or /exp can execute authored CAPL |
| Official CANoe AI Package MCP integration | Requires CANoe 20 SP2+; not provided for CANalyzer 15 by this project |
| Direct bench/application control | Not included; requires a separate verified local integration |
| Bundled CAPL reference material | From newer Vector documentation; verify version-sensitive APIs in local CANalyzer 15 Help |

This repository contains instructions, reference material and a narrow offline CSV timing checker. It does not include a CANalyzer license, application installer, MCP server, raw trace decoder or bench test runner. Generated CAPL remains uncompiled until checked with the target installation.

## Install in Codex

1. Download the repository using **Code → Download ZIP**, or clone it.
2. Copy the complete `skills/canalyzer-15-assistant` folder into a Codex skill discovery directory configured for your installation. A common user-level location is `~/.codex/skills/canalyzer-15-assistant` (on Windows, `%USERPROFILE%\.codex\skills\canalyzer-15-assistant`). Use your configured skills root if different.
3. Preserve the complete folder, including `SKILL.md`, `references/`, `scripts/`, `agents/`, `assets/` and `LICENSE.txt`.
4. Invoke `$canalyzer-15-assistant` in a session that has discovered the skill.

For another assistant, use its documented skill import mechanism or supply `SKILL.md` together with the linked reference files. GitHub publication alone does not install the skill into ChatGPT or another client. It does not connect an assistant to CANalyzer.

## A first bench-validation task

Supply the exact version/variant, the requirement, the execution context, and the relevant code or trace plus signal definitions. For example:

> Use $canalyzer-15-assistant. I use CANalyzer 15 SP5 /pro on a bench. After the rising edge of Trigger, Response must become 1 within 500 ms, inclusive. Analyze the supplied signal export, report measured delays, and distinguish failures from incomplete capture windows. Do not transmit traffic.

For code drafting, also state the program location, channel, database symbols, units and intended measurement behavior. For a first real use, compile in the target application and run known positive and negative scenarios before relying on the result.

See [the synthetic example](examples/timing-check.md) for a complete timing-analysis exercise.

## Repeatable offline timing check

For a complete decoded binary signal event export matching the example's semantics, run from the repository root with Python 3.10+ (standard library only):

```sh
python3 skills/canalyzer-15-assistant/scripts/check_timing.py examples/timing-check.csv --window-ms 500 --complete-event-export
```

The JSON report reproduces 2 Pass, 1 Fail and 1 Inconclusive across 4 triggers. This example exits with status 1 because it includes a deliberate failure. The checker uses exact decimal comparisons, treats the deadline as inclusive, and rejects overlapping trigger windows and malformed input. `--complete-event-export` asserts that every signal change is recorded, values remain valid between rows and there are no capture gaps. Do not assert it for periodic samples or exports of unknown completeness.

See [the checker contract](skills/canalyzer-15-assistant/references/offline-timing.md) for input limits, result fields and exit codes. This checks supplied data only; it provides no CANalyzer or bench connection.

Run the synthetic regression tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

## Privacy and contributions

Use synthetic or authorized sanitized inputs in issues and pull requests. Keep customer DBCs, configurations, traces, VINs and credentials out of this public distribution. Include the exact product version and variant with compatibility reports.

## License and attribution

[LICENSE](LICENSE) includes MIT notices for the adaptation and bundled Vector reference material. The copied Vector references retain their upstream copyright notice in the skill's `LICENSE.txt`. See [provenance and product boundaries](skills/canalyzer-15-assistant/references/compatibility.md).
