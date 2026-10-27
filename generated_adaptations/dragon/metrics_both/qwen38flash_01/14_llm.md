

## Analysis

The 20.3-turn solution used a different warrior cycle: eat at ssm≥3 (not ≥2), go to cave at ssm<3 (not ≤1), attack at ssm<4 in cave. Combined with farmer eat at ssm≥3 and the specific step-based spawning cascade. The 24.0 solutions were slightly less aggressive in early spawning and had farmers eating less frequently (≥5), which paradoxically slowed warrior buildup in the critical early steps.

Key differences to restore speed:
1. Warriors go to cave at ssm 0,1,2 (arrive at cave ssm 1,2,3) and attack until ssm=3, return at ssm≥4. This gets warriors attacking in the cave one step earlier for those with ssm=2.
2. Farmers eat at ssm≥4 (not 5) to cycle faster and be available for spawning sooner.
3. Step-based spawning cascade: step≤8 doubles warrior spawns when affordable; step≥5 also spawns farmers to boost wheat production long-term.
4. The `wheat` variable is a snapshot — checking it multiple times correctly verifies affordability of multiple pairs.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import abc


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors: go to cave at ssm 0-2, eat at ssm >= 3
        for c in warriors:
            if c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # Farmers: eat at ssm >= 4, free for spawn/farm otherwise
        free = []
        for c in farmers:
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
            else:
                free.append(c)

        # Spawning cascade
        remaining = list(free)

        if step <= 8 and len(remaining) >= 2 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
            if len(remaining) >= 2 and wheat >= 24:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]
            elif len(remaining) >= 2 and wheat >= 22:
                environment.assign_group(remaining[0], "spawn farmer")
                environment.assign_group(remaining[1], "spawn farmer")
                remaining = remaining[2:]

        elif step <= 20 and len(remaining) >= 2 and wheat >= 12:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            remaining = remaining[2:]
            if len(remaining) >= 2 and wheat >= 24:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]

        elif step >= 5 and len(remaining) >= 2 and wheat >= 10:
            environment.assign_group(remaining[0], "spawn farmer")
            environment.assign_group(remaining[1], "spawn farmer")
            remaining = remaining[2:]
            if len(remaining) >= 2 and wheat >= 22:
                environment.assign_group(remaining[0], "spawn warrior")
                environment.assign_group(remaining[1], "spawn warrior")
                remaining = remaining[2:]

        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers in cave: return to village immediately
        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        # Attack at ssm <= 3 (up to 3 attacks per trip), return at ssm >= 4
        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger protection: never let all warriors leave simultaneously
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")

        for c in must_return:
            environment.assign_group(c, "village")
```