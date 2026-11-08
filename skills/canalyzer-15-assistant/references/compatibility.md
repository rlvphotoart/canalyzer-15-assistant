# Compatibility and provenance

Verified on 2026-11-08.

## Official package

- Product page: https://www.vector.com/en/product/canoe/canoe-ai-features/canoe-ai-package/
- Feature overview: https://www.vector.com/en/product/canoe/canoe-ai-features/
- Release announcement: https://www.vector.com/en/company/press/press-releases/canoe-automates-development-and-testing-workflows-with-ai-agents/
- Download center: https://www.vector.com/en/services/download-center/
- Official global 1.0.2 download resolved from the download-center data: https://portal.vector.com/shared/a22eec51-7ed6-47ee-a645-6cb6e392d0b5
- Downloaded archive SHA-1 matched Vector metadata: 6ea20d37aad23b6835cfbaee52c5c4905a3214cf. SHA-1 is recorded for publisher matching, not as a security guarantee.
- Official runtime compatibility: CANoe 20 SP2 and later; package page specifies CANoe Desktop Edition /pro, not Test Bench Edition. Do not extrapolate support to CANalyzer 15.
- MIT licensed; retain LICENSE.txt for the selected copied references, copyright Vector Informatik GmbH.
- Copied reference files originate in canoe-copilot-plugins/canoe-core/skills/canoe-capl-coding/references of the downloaded package. They reflect newer documentation and require version-15 checks.

## CANalyzer boundaries

- Official CANalyzer overview: https://www.vector.com/en/product/canalyzer/
- CAPL availability depends on variant; /exp does not support creating/executing CAPL programs. Verify the installed version-15 license and local feature matrix before code execution advice.
- Offline log analysis and code drafting need no CANoe MCP connection.
- Installing instructions cannot create MCP support or license features absent from the application.
- COM integration is a separate possible engineering project. Verify exact support and members with installed version-15 documentation; general CANoe COM examples are insufficient proof.
- Do not infer that absence of a connected Windows tool means CANalyzer lacks a capability; distinguish application support, installed license and current assistant access.

## First-use examples

- Explain a supplied CAPL compiler error and propose a minimal patch.
- Check an ASC/CSV capture for a signal reaching its required value within 500 ms after a trigger, once mapping and acceptance criteria are supplied.
- Explain how to filter traffic or prepare an offline replay in CANalyzer 15, checking channel routing and any transmit behavior.
- Inspect a supplied DBC and identify signal units, scaling and message relationships without inventing missing metadata.
