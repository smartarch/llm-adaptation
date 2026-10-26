

# Diagnosis

The Dragon HP stays at 50 for all 30 steps in every game, meaning **no attack ever lands**. This strongly suggests:

1. There may be **zero initial warriors** — the game might start with only farmers.
2. My spawning logic was too conservative (requiring 4+ farmers as buffer), so warriors were never spawned.
3. Without warriors, nothing ever attacks.

# New Strategy

- **Ultra-aggressive spawning**: As soon as wheat ≥ 12 and we have ≥ 2 farmers, immediately spawn a warrior. No buffer requirement — use ALL available farmers for spawning when it makes strategic sense.
- **Phase 1 (early)**: All farmers farm to build wheat quickly.
- **Phase 2**: Once wheat reaches 12, spawn warriors using 2 farmers. Keep remaining farmers farming.
- **Phase 3**: Once we have enough farmers (≥ 4), simultaneously spawn and farm.
- **Warriors**: Always sent to cave → attack immediately.
- **No persistent state** to avoid cross-game contamination.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.wheat
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Send ALL warriors to cave immediately - they must attack!
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farming/spawning logic for farmers
        # Goal: spawn warriors ASAP (12 wheat, 2 farmers), then farmers (10 wheat, 2 farmers)
        # Keep at least 2 farmers farming to sustain wheat income
        
        remaining = list(farmers)
        n = len(remaining)
        
        # Very aggressive spawning - if we have enough wheat and farmers, spawn NOW
        # Strategy: if n >= 4, we can spare 2 for spawning while 2 farm
        # If n == 2 and wheat is very high (e.g., >= 20), also spawn (emergency)
        # If n == 3, we can use 2 to spawn and 1 farms (slower but still productive)
        
        if n >= 4 and wheat >= 12:
            # Spawn a warrior: use 2 farmers for spawn, rest farm
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
        elif n >= 4 and wheat >= 10:
            # Spawn a farmer for economy growth
            environment.assign_group(remaining[0], "spawn farmer")
            environment.assign_group(remaining[1], "spawn farmer")
            remaining = remaining[2:]
        elif n == 3 and wheat >= 12:
            # 1 farmer farming, 2 spawning a warrior
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
        elif n == 3 and wheat >= 10:
            environment.assign_group(remaining[0], "spawn farmer")
            environment.assign_group(remaining[1], "spawn farmer")
            remaining = remaining[2:]
        elif n == 2 and wheat >= 20:
            # Emergency: we have tons of wheat but only 2 farmers - spawn warrior
            # Accept one turn of no farming to get a warrior out
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]

        # All remaining farmers farm
        for f in remaining:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # ALWAYS attack - this is the only way to damage the dragon
                environment.assign_group(c, "attack")
            else:
                # Any non-warrior in cave should return to village
                environment.assign_group(c, "village")
```

### Why this should work:
- **Step 0-2**: 2 farmers farm → wheat builds (2→4→6→8→10→12 by step ~5 with 2 farmers at 2 wheat each)
- **Step ~5**: wheat hits 12 → spawn warrior using 2 farmers
- **Step ~6**: New warrior appears in village → sent to cave
- **Step ~7**: Warrior in cave → assigned to "attack" → Dragon HP drops by 3!
- Continue farming, spawning more warriors as wheat accumulates
- With 3-4 warriors attacking (3 dmg each), Dragon dies in ~5-6 attack turns