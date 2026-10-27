

## Analysis and Strategy Improvement

The v3 strategy (20.7 steps, 100% win) has warriors leaving the cave at `scm >= 4`, giving only 3 attacks per cycle. But villagers only starve at `scm >= 6` (6 consecutive steps without eating). This means warriors can safely attack at `scm=5` before leaving, gaining 2 extra attacks per cycle (5 instead of 3) for just 1 HP loss during the transit back.

**Key improvements:**
1. **5 attacks per warrior cycle** (scm=1→5) instead of 3, at cost of 1 HP per cycle from brief starvation during transit. This gives ~67% more DPS per warrior.
2. **Tighter village→cave rotation**: Warriors enter cave when `scm <= 1` (arrive with `scm=2`, attack through `scm=5`).
3. **Aggressive spawning**: Spawn warriors every opportunity to build up attack pressure faster.
4. **Early everyone-farms phase**: First 2 steps all villagers farm to quickly accumulate wheat for spawning.
5. **Endgame all-in at HP ≤ 12**: All villagers (farmers included) rush to cave for final blow.

```py
from