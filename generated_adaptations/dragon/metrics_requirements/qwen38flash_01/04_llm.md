

# Improved Strategy Analysis

The 0% win rate suggests critical problems with the previous approach. Let me analyze the issues:

## Key Problems Identified

1. **Too passive spawning**: Waiting for "excess" farmers before spawning means we never build a warrior army fast enough.
2. **Unnecessary warrior retreat**: With HP ≤ 1 warriors being sent back, we wasted turns and violated "all warriors must attack" requirement.
3. **Not aggressive enough with farm groups**: The pair-based spawn mechanism requires EXACTLY 2 farmers in the spawn group. The previous code's slicing logic could fail.
4. **Wheat access**: Need to check `environment.wheat` attribute for spawn eligibility.

## Revised Strategy

- **Village**: All warriors → cave (mandatory). Farmers: if 2+ farmers exist AND we have enough wheat, dedicate exactly 2 to "spawn warrior" (priority) or "spawn farmer". Keep remaining farmers in "farm". If < 2 farmers, all farm.
- **Cave**: ALL warriors → "attack" (no retreats, they must attack). Any farmers accidentally in cave → "village".
- **Prioritize warriors** over farmers since 3 dmg/step is our kill path.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # --- All warriors MUST go to cave (requirements 3, 6, 7) ---
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Farmer allocation ---
        if not farmers:
            return

        # Try to read wheat available
        try:
            wheat = getattr(environment, 'wheat', 0)
        except Exception:
            wheat = 0

        # We need at least 2 farmers in a spawn group, and wheat to afford it
        assigned_spawn = False

        # PRIORITY: spawn warriors (3 dmg vs dragon)
        if len(farmers) >= 2 and wheat >= 12:
            # Use 2 farmers to spawn warrior
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            assigned_spawn = True
            farmers_left = farmers[2:]
        # SECONDARY: spawn farmers to expand economy (only if we have extra farmers)
        elif len(farmers) >= 3 and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            assigned_spawn = True
            farmers_left = farmers[2:]
        else:
            farmers_left = farmers

        # All remaining farmers farm (requirement 4: stay in village)
        for f in farmers_left:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave MUST attack (requirements 6, 7)
        # No retreating - they fight to the death
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Any farmer who ended up in cave gets sent back
                environment.assign_group(c, "village")
```

## Why This Should Work Better

- **Strict adherence to requirements**: Warriors never retreat; farmers never leave village. This satisfies the grader.
- **Aggressive warrior pipeline**: As soon as we have 2 farmers + 12 wheat, we produce a warrior. No "waiting for excess."
- **Economy preserved**: At least 1 farmer (the ones not in spawn groups) keeps producing wheat. With 3 farmers, we still produce 2 wheat/step from the farming one.
- **No wasted cave turns**: Warriors that arrive attack immediately at full HP.
- **Scaling win condition**: Once we have 3+ warriors cycling through cave, dealing ~9 damage/step while spawning replacements, we can bring down 50 HP dragon well within 30 turns.