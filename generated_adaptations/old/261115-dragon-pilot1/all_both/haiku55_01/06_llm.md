## What was wrong

1. **Invalid `eat` assignments.** A hungry villager at 5+ steps was sent to "eat" even when no wheat was left, which the environment rejects.
2. **Unassigned components.** The village logic built several overlapping lists and tested membership with `in`. Some components ended up in no list, so they were never assigned.
3. **Dragon left unattacked.** Warriors left the Cave only at 5 steps of hunger, and only if another warrior stayed. With one warrior, or with warriors in sync, the Dragon went unattacked for too long.

## Fix

**Village phase.** Each component is placed into exactly one bucket, and every bucket is written to a single `{id: group}` map that is then applied once per component. This makes it impossible to skip or double-assign a villager.
- Villagers with `steps_since_meal >= 3` eat, most hungry first, as long as wheat remains. Each meal costs 1 wheat, so the budget is tracked.
- A hungry villager who cannot be fed is never sent to "eat". Warriors go to "cave" and farmers to "farm".
- Fed warriors go to the Cave. Warriors only leave the Cave when hungry, so they always come back to the Cave after eating.
- Spawning (warriors first, then farmers) and farming are unchanged, but spawning uses the wheat left after meals.

**Cave phase.** Warriors leave for food earlier, at `steps_since_meal >= 3`, which keeps their counter at 4 or below on arrival. They leave only if at least one other warrior stays and keeps attacking. The hunger limit for a forced departure is 4. A single warrior is away for about two steps per cycle, which keeps the unattacked streak within the 2-step limit.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Villagers with steps_since_meal >= HUNGER_THRESHOLD eat (most hungry first),
        as long as wheat is available for the meal.
      - Fed warriors go to the cave to attack the dragon.
      - Remaining farmers form pairs to spawn warriors, then farmers, and farm otherwise.
    Cave:
      - Farmers go back to the village.
      - Warriors rotate: a hungry warrior leaves for food only while another warrior
        stays behind and keeps attacking (or when it is about to starve).
    Every component is assigned exactly once per call.
    """

    HUNGER_THRESHOLD = 3        # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 3         # cave: a warrior may leave for food at this hunger
    FORCE_LEAVE_THRESHOLD = 4   # cave: a warrior must leave for food at this hunger
    MIN_SPAWNS = 2              # at least this many of each role should be spawned

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = int(environment.farm.wheat)
        plan = {}  # id(component) -> (component, group)

        def put(c, group):
            plan[id(c)] = (c, group)

        # 1) Hungry villagers eat, most hungry first, limited by available wheat
        budget = max(0, wheat)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if budget > 0:
                put(c, "eat")
                budget -= 1
            else:
                # cannot be fed: "eat" would be invalid without wheat
                put(c, "cave" if c.role == "Warrior" else "farm")
        wheat_after_meals = budget

        # 2) Fed villagers
        free_farmers = []
        for c in components:
            if id(c) in plan:
                continue
            if c.role == "Warrior":
                put(c, "cave")          # fed warriors attack the dragon
            else:
                free_farmers.append(c)

        # 3) Spawning among free farmers (pairs), warriors first, then farmers
        remaining = wheat_after_meals
        if (self.spawned_warriors < self.MIN_SPAWNS
                and remaining >= 12 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                put(c, "spawn warrior")
            free_farmers = free_farmers[2:]
            remaining -= 12
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and remaining >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                put(c, "spawn farmer")
            free_farmers = free_farmers[2:]
            remaining -= 10
            self.spawned_farmers += 1

        for c in free_farmers:
            put(c, "farm")

        # 4) Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)][1])

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        plan = {}

        # Farmers must not stay in the cave
        warriors = []
        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                plan[id(c)] = "village"

        # Warriors: decide who leaves for food, keeping at least one attacker
        # in the cave unless someone is about to starve.
        staying = len(warriors)
        for w in sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True):
            s = w.steps_since_meal
            if s >= self.FORCE_LEAVE_THRESHOLD:
                plan[id(w)] = "village"
                staying -= 1
            elif s >= self.LEAVE_THRESHOLD and staying - 1 >= 1:
                plan[id(w)] = "village"
                staying -= 1
            else:
                plan[id(w)] = "attack"

        # Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])
```