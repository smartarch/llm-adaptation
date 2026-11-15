

## Analysis

The 33% regression came from over-aggressive 3-pair spawning at `wheat >= 36` which starved the economy, plus a restructured cascade that broke the proven step-based logic. The proven 20.3-turn solution used a precise cascade: double warrior pairs in steps 1-8, single warrior pairs through step 20, farmer spawning after step 5.

The only safe improvement is to **extend the warrior spawn window slightly past step 20** so we keep building attackers in the late game, while keeping the exact proven cascade structure (warriors eat at ssm≥2, cave at ssm≤1; farmers eat at ssm≥3).

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

        # Warriors: strict 3-attack / 6-step cycle
        for c in warriors:
            if c.steps_since_meal <= 1:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "eat")

        # Farmers: eat at ssm>=3
        remaining = [c for c in farmers if c.steps_since_meal < 3]
        for c in farmers:
            if c.steps_since_meal >= 3:
                environment.assign_group(c, "eat")

        # Spawning cascade (proven structure)
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
        elif step <= 24 and len(remaining) >= 2 and wheat >= 12:
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

        for c in components:
            if c.role == "Farmer":
                environment.assign_group(c, "village")

        if not warriors:
            return

        must_return = [c for c in warriors if c.steps_since_meal >= 4]
        can_attack = [c for c in warriors if c.steps_since_meal <= 3]

        # Stagger: never let all warriors leave simultaneously (prevents regen gap)
        if not can_attack and must_return:
            must_return.sort(key=lambda c: c.steps_since_meal)
            keeper = must_return.pop(0)
            can_attack.append(keeper)

        for c in can_attack:
            environment.assign_group(c, "attack")
        for c in must_return:
            environment.assign_group(c, "village")
```