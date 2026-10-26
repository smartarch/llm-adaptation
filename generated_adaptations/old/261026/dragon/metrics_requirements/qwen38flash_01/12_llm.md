

# Rethinking From First Principles

After 5 failed runs at 0% win rate, I conclude my code likely had **silent exceptions** (from `getattr` on missing attributes, or `int()` casts) that were swallowed by my `try/except` blocks, causing farmers/warriors to go *unassigned* every turn. Unassigned units do nothing — so we never attacked and never spawned.

## New Principles

1. **No defensive programming that hides bugs.** If something is wrong, I want to know, not silently fail.
2. **Maximum aggression.** The only win path is damage. Every warrior in cave → attack, every turn, unconditionally.
3. **Simple, robust spawn rule.** Only spawn warriors when we clearly have surplus (≥ 4 farmers), pairing exactly 2 into "spawn warrior". Otherwise all farmers farm (wheat engine must stay healthy).
4. **Minimal branching** so there's no path where a unit ends up unassigned.

## Expected Timeline (assuming a reasonable starting roster like 2 warriors + 3 farmers)

- Turn 0: both warriors → cave; 3 farmers all farm → +6 wheat.
- Turn 1: warriors attack (−6 HP dragon, dragon eats maybe 1); farmers farm.
- As farmers accumulate surplus, we spawn warriors steadily. With a few warriors cycling and ~9–12 dmg/turn, the 50 HP dragon falls within 15–20 steps, well inside the 30-step budget.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        # Split by role — straightforward, no hidden failures.
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior in the village must go to the cave immediately.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: at least 2 must farm to produce wheat.
        # If we have 4 or more farmers, dedicate a pair to spawning a warrior.
        if len(farmers) >= 4:
            # 2 farmers → spawn warrior, all remaining farmers → farm.
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            # Too few farmers to risk a spawn; everyone farms.
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Every warrior in the cave attacks, no exceptions.
        # Any non-warrior (a stray farmer) is sent back to the village.
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```

## What Changed vs. Prior Attempts

- **Removed all `try/except` and `getattr` wheat checks** — these were masking the real bug. The code now only uses documented attributes (`c.role`) and documented group names (`"farm"`, `"cave"`, `"spawn warrior"`, `"attack"`, `"village"`).
- **Every single component is guaranteed to be assigned** to some group on every call — no orphaned units.
- **Spawn threshold of 4 farmers** ensures we always keep 2 farming so the wheat pipeline doesn't collapse, while still feeding new warriors into the cave.
- **Zero retreat / zero HP checks** — warriors that arrive in cave attack on the very next step, satisfying the "must attack" requirement and maximizing DPS.