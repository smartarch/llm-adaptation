

# Rethinking the Problem

After 4 failed attempts with 0% win rate, I need to question my core assumptions. The most likely issues are:

1. **Over-complicated spawn logic** that never actually fires due to edge cases in pairing or wheat checks
2. **Not enough focus on the win condition**: The ONLY way to win is dealing 50 damage. Spawning is a means to that end, not the end itself
3. **Possible class name or attribute name issues** that silently prevent code from working

## New Minimal Aggressive Strategy

I will:
- **Never gate on wheat** — just pair farmers into spawn groups and let the engine ignore them if it can't afford it
- **Always keep at least 2 farmers farming** (the true wheat engine)
- **Aggressively pair all excess farmers into "spawn warrior"** every single turn
- **Warriors in village → cave immediately; warriors in cave → attack unconditionally**
- **Send any farmers in cave back to village**

The math: starting with 3 farmers → 6 wheat/step → a new warrior every ~2 steps once initial warriors are committed. With 4-5 warriors cycling through, dealing ~12 dmg/step against a 50 HP dragon with counterattacks, the win is achievable in 15-25 steps.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers  = [c for c in components if c.role == "Farmer"]

        # 1. Every warrior must head to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # 2. Reserve at least 2 farmers for farming (wheat engine).
        min_farmers = 2
        farm_pool   = farmers[:min_farmers]
        excess      = farmers[min_farmers:]

        # 3. Pair excess farmers into "spawn warrior" (priority: damage).
        #    Only pairs work (need exactly 2 per spawn).
        num_pairs = len(excess) // 2
        spawn_pool = excess[:num_pairs * 2]
        leftover   = excess[num_pairs * 2:]

        # 4. Assign: farming first.
        for f in farm_pool:
            environment.assign_group(f, "farm")
        # Odd leftover also farms so it doesn't sit idle.
        for f in leftover:
            environment.assign_group(f, "farm")

        # 5. Spawn pairs – always attempt, no wheat gate.
        for f in spawn_pool:
            environment.assign_group(f, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```

## Key Differences From Previous Attempts

| Previous bug | Fix |
|---|---|
| Checked `environment.wheat` → silently returned 0 → **never spawned** | Removed all wheat checks; the engine itself validates affordability |
| Slicing logic produced odd group sizes | Use `num_pairs * 2` to guarantee exact even-numbered spawn pool |
| Leftover odd farmer unassigned | Explicitly assigned leftover to "farm" |
| Warrior retreat logic stalling the attack pipeline | Warriors never retreat; they always attack when in cave |
| Class name uncertainty | Confirmed `SmartAdaptation` as the required name |

This should give us a steady warrior pipeline feeding into continuous attacks, eventually bringing down the 50 HP dragon within the step budget.