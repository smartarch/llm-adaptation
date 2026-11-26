## Analysis

The bottleneck now is clear: **the army never grows**. With initial wheat around 20 and my reserve of `4×pop + 5 ≈ 25+`, spawning never fired. Meanwhile the Dragon's counterattacks (40% chance of 1 damage, 20% chance of eating a villager) attrit the starting warriors, so damage output only shrinks while the Dragon out-regenerates. With 2–3 warriors the math doesn't close within 30 steps — growth is mandatory, so spawning must happen early and often.

Fixes:

1. **Small spawn buffer** (cost + 10 + meals instead of cost + 4×pop): spawn aggressively whenever affordable.
2. **Prefer spawning from warrior pairs** — this doesn't consume farmers at all, keeping the food economy intact while the army grows.
3. **Proven attack schedule** (the one that won 67% earlier): eat in the Village at `ssm ≥ 3` (or `ssm ≥ 4` for freshly-returned warriors to avoid double-eating pressure — actually keep the simple proven rule: eat at `ssm ≥ 3`), in the Cave attack while `ssm ≤ 3`, return at `ssm ≥ 4`. Natural phase drift between warriors gives near-continuous Dragon coverage, so regeneration rarely triggers.