

# Rethinking — Aggressive Spawning Was the Bottleneck

Re-examining the requirements: *"All farmers should remain in the Village"* does **not** require them to farm — it just prohibits them from going to the Cave. So I was being too conservative by insisting on ≥2 farming at all times, which starved the warrior pipeline.

With a typical starting roster (2 warriors, 3 farmers), my old rule (`spawn only if ≥4 farmers`) **never fired** until the player had grown the farmer population — which itself required spawning farmers I never did. Result: no new warriors, dragon survives, 0% win.

## New Rule
- **Always try to pair farmers into "spawn warrior"** whenever there are at least 2. The engine will silently reject the spawn if wheat is short — no need to gate.
- **Any odd farmer** also goes to farm (keeps wheat flowing).
- **Warriors**: village → cave → attack, unconditionally, every turn.
- **Any stray farmer in cave** → sent back to village.

This yields a warrior roughly every few turns as wheat accumulates, while the starting warriors already put ~6 dmg/turn on the 50 HP dragon. Replacements keep DPS high as the dragon's 40% AoE whittles us down. Expected kill well under 30 steps.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Every warrior in the village must head to the cave right now.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers: greedily form warrior-spawn pairs; leftovers farm.
        # The engine will ignore the pair if wheat < 12, so we always try.
        num_pairs = len(farmers) // 2
        spawn_pool = farmers[: num_pairs * 2]
        leftover = farmers[num_pairs * 2:]

        for f in spawn_pool:
            environment.assign_group(f, "spawn warrior")
        for f in leftover:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # A farmer that ended up in the cave goes home.
                environment.assign_group(c, "village")
```

## What's different from every prior attempt

| Prior bug | Fix here |
|---|---|
| Wheat gating via `environment.wheat` silently returned 0 → **no spawns ever** | Removed all wheat checks; always pair farmers and let the engine decide |
| Spawn threshold `≥4` farmers meant pipeline never started with a small roster | Threshold lowered to `≥2`; we try to spawn *every* turn from the start |
| Defensive `try/except` masked real errors (e.g., missing attributes) | Removed; code only touches documented fields (`c.role`, group names) |
| Conservative "keep 2 farmers farming" stalled economy | Let the engine refuse a spawn if wheat is short; meanwhile every farmer either pairs or farms, so no unit sits idle |
| Warrior retreat / HP logic stalled DPS | Warriors in cave always attack |
| Class name | `SmartAdaptation` (required name) |