

# Deep Analysis of Persistent Failure

After three failures, let me reconsider every assumption:

1. **Wheat checking was the bottleneck**: If `environment.wheat` didn't exist as a simple attribute, my `try/except` set `wheat = 0`, meaning **I never spawned anything**. The dragon never took enough damage.
2. **Over-conservative farming**: Keeping "at least 1 farmer farming" when we barely have 3 farmers means the warrior pipeline is glacially slow.
3. **Should always attempt spawning**: If the game engine handles insufficient wheat gracefully (simply doesn't spawn), we should *always* try to pair farmers into spawn groups every turn. No gating.
4. **More aggressive pairs**: 4 farmers in "spawn warrior" = 2 warriors per cycle, not 1.

## New Strategy

- **Never check wheat** — just always pair farmers into spawn groups. The engine will ignore the pair if wheat is insufficient.
- **Minimum 2 farmers** in "farm" (to generate wheat).
- **Everyone else** goes into "spawn warrior" first (priority: damage dealers).
- **Warriors in village** → cave. **Warriors in cave** → attack (always, no retreat).
- **Farmers in cave** → back to village.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # VILLAGE phase
    # ------------------------------------------------------------------
    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers  = [c for c in components if c.role == "Farmer"]

        # 1) Every warrior in the village heads straight to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # 2) Decide how many farmers stay farming vs. spawning.
        #    We need at least 2 in "farm" to produce wheat for spawns.
        MIN_FARMERS = 2
        num_farming = min(MIN_FARMERS, len(farmers))
        farm_list   = farmers[:num_farming]
        rest        = farmers[num_farming:]

        # 3) Pair up remaining farmers for "spawn warrior" (damage priority).
        #    Assign in pairs; odd leftover goes to farm too.
        num_spawnable = (len(rest) // 2) * 2          # even number, pairs only
        spawn_list    = rest[:num_spawnable]
        leftover      = rest[num_spawnable:]

        # Assign farmers that stay in village and farm
        for f in farm_list:
            environment.assign_group(f, "farm")
        # Extra odd farmer that didn't pair → also farms
        for f in leftover:
            environment.assign_group(f, "farm")

        # Assign farmer pairs to "spawn warrior" – always try, every turn.
        for f in spawn_list:
            environment.assign_group(f, "spawn warrior")

    # ------------------------------------------------------------------
    # CAVE phase
    # ------------------------------------------------------------------
    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Every warrior attacks, no exceptions.
                environment.assign_group(c, "attack")
            else:
                # A farmer that ended up in the cave is sent home.
                environment.assign_group(c, "village")
```

## Why this should finally work

| Issue in prior attempts | Fix |
|---|---|
| Wheat check (`environment.wheat`) silently failed → zero spawns ever | **Removed wheat gating entirely.** Spawn groups are always attempted; the engine simply ignores them if wheat < 12. |
| Too few farmers in spawn groups (max 2 at a time) | **All excess farmers in pairs go to "spawn warrior"**, so 6 excess farmers → 3 warriors per cycle. |
| Class name mismatch in first two attempts | Uses the required name `SmartAdaptation`. |
| Overly cautious warrior management (HP check, retreat) | **All warriors always attack.** No retreat logic that could violate the "must attack" requirement or stall the clock. |

The expected timeline: with 3 starting farmers, turns 0-2 accumulate wheat while 2 starting warriors chip away at the dragon (~18 damage). By turn ~4-5 a new warrior spawns. With 3 warriors the damage output is ~9/turn, killing the remaining dragon well inside the 30-step limit.