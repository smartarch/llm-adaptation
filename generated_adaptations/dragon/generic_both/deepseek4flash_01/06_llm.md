Strategy for the faster version:
- **Multi-spawn**: the previous version spawned only one group per step. Since a spawn group converts *every pair* of villagers plus wheat, I now use all spare farmers in pairs, so 4 spare farmers can spawn 2 warriors in one step. This is the biggest speed lever.
- **Aggressive early ramp**: get to ~3 farmers, then dump every spare farmer-pair into warrior spawning. When wheat is high, use all free farmers even at the cost of skipping a farm step (burst spawning), to get attackers online sooner.
- **Immediate attacks**: fresh warriors go straight to the Cave and attack while `steps_since_meal <= 5`, so they contribute damage almost immediately.
- **Feeding discipline**: emergency meals at 5+ steps, warriors eat at 3+ steps before travelling, farmers eat at 5 steps. This keeps villagers alive without wasting wheat.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat_left = max(0, int(getattr(environment.farm, "wheat", 0)))
        assigned = {}

        # --- Meals (highest priority) ---
        # Villagers must eat before they reach 6 steps without food.
        # Warriors also need to eat before being sent to the Cave (rule: not if 3+).
        for c in sorted(comps, key=lambda x: -x.steps_since_meal):
            if c in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat_left > 0:
                assigned[c] = "eat"
                wheat_left -= 1
            elif c.role == "Warrior" and c.steps_since_meal >= 3 and wheat_left > 0:
                assigned[c] = "eat"
                wheat_left -= 1

        free = [c for c in comps if c not in assigned]
        free_warriors = [c for c in free if c.role == "Warrior"]
        free_farmers = [c for c in free if c.role == "Farmer"]

        # --- Warriors: go to the Cave immediately if fresh enough ---
        for w in free_warriors:
            if w.steps_since_meal < 3 and w.hp > 0:
                assigned[w] = "cave"
            else:
                assigned[w] = "farm"  # wait for a meal (should be rare)

        # --- Farmers: spawn (multi-pair) or farm ---
        total_farmers = sum(1 for c in comps if c.role == "Farmer")
        pool = sorted(free_farmers, key=lambda x: x.steps_since_meal)
        n = len(pool)

        # How many farmers we may use for spawning (must be even).
        # - With <=2 farmers, use them all: otherwise we cannot grow at all.
        # - With a healthy wheat stock, burst: use them all to spawn more attackers.
        # - Otherwise keep at least one farmer farming to sustain income.
        if total_farmers <= 2:
            usable = n
        elif wheat_left >= 20:
            usable = n
        else:
            usable = n - 1
        usable -= usable % 2
        if usable < 0:
            usable = 0

        idx = 0
        farmer_target = 3
        wanted_farmers = max(0, farmer_target - total_farmers)

        # Grow toward the farmer target first.
        while wanted_farmers > 0 and usable - idx >= 2 and wheat_left >= 10:
            assigned[pool[idx]] = "spawn farmer"
            assigned[pool[idx + 1]] = "spawn farmer"
            idx += 2
            wheat_left -= 10
            wanted_farmers -= 1

        # Then spawn as many warriors as the remaining pairs and wheat allow.
        while usable - idx >= 2 and wheat_left >= 12:
            assigned[pool[idx]] = "spawn warrior"
            assigned[pool[idx + 1]] = "spawn warrior"
            idx += 2
            wheat_left -= 12

        # Everyone else farms.
        for c in pool[idx:]:
            assigned[c] = "farm"

        # Safety net + apply assignments.
        for c in comps:
            if c not in assigned:
                assigned[c] = "farm" if c.role == "Farmer" else "cave"
            environment.assign_group(c, assigned[c])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        comps = list(components)
        for c in comps:
            # Warriors attack as long as they still deal damage (starving starts at 6).
            # Otherwise travel back so they can eat in the Village.
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= 5:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```