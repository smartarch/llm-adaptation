## What was wrong

1. **Starvation of a farmer.** Villagers that were placed in a spawn pair were left unfed while they waited, and they could starve. Eating now also takes priority over spawning, so a villager that reaches the hunger threshold is always fed first.
2. **Dragon gaps.** The cave rule left a warrior in the cave at hunger 2 and 3 without any real check on the others. When two warriors were in sync, both left together, and a gap of 3 or more steps followed. Warriors now leave for food only at hunger 3 and only if another warrior stays in the cave that is still fresh (hunger below 3). A warrior is forced to leave at hunger 4, which is still safely under the 6-step limit.

The trip for a warrior takes about three steps (leave, eat in the village, return), so a second fresh warrior must keep the dragon under attack during that time. Every component is still assigned exactly once per call.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Villagers with steps_since_meal >= HUNGER_THRESHOLD eat first (most hungry first),
        as long as wheat is available for the meal.
      - Hungry warriors that cannot be fed stay in the village (never sent to the cave).
      - Fed warriors go to the cave to attack the dragon.
      - Remaining farmers form pairs to spawn warriors, then farmers, and farm otherwise.
    Cave:
      - Farmers go back to the village.
      - Warriors rotate: a warrior with hunger LEAVE_THRESHOLD leaves for food only while
        another fresh warrior stays in the cave to attack. A warrior at FORCE_LEAVE_THRESHOLD
        leaves regardless, so it never starves.
    Every component is assigned exactly once per call.
    """

    HUNGER_THRESHOLD = 3        # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 3         # cave: a warrior may leave for food at this hunger
    FORCE_LEAVE_THRESHOLD = 4   # cave: a warrior must leave for food at this hunger
    FRESH_LIMIT = 3             # cave: a warrior with hunger below this counts as "fresh"
    MIN_SPAWNS = 2              # at least this many of each role should be spawned

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = int(environment.farm.wheat)
        plan = {}  # id(component) -> group

        # 1) Hungry villagers eat, most hungry first, limited by available wheat
        budget = max(0, wheat)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if budget > 0:
                plan[id(c)] = "eat"
                budget -= 1
            else:
                # cannot be fed: never send a hungry warrior to the cave
                plan[id(c)] = "farm"
        wheat_after_meals = budget

        # 2) Fed villagers
        free_farmers = []
        for c in components:
            if id(c) in plan:
                continue
            if c.role == "Warrior":
                plan[id(c)] = "cave"        # fed warriors attack the dragon
            else:
                free_farmers.append(c)

        # 3) Spawning among free farmers (pairs), warriors first, then farmers
        remaining = wheat_after_meals
        if (self.spawned_warriors < self.MIN_SPAWNS
                and remaining >= 12 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn warrior"
            free_farmers = free_farmers[2:]
            remaining -= 12
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and remaining >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn farmer"
            free_farmers = free_farmers[2:]
            remaining -= 10
            self.spawned_farmers += 1

        for c in free_farmers:
            plan[id(c)] = "farm"

        # 4) Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        plan = {}
        warriors = []
        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                plan[id(c)] = "village"     # farmers must not stay in the cave

        # Most hungry warriors are decided first
        ordered = sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True)
        leaving = set()

        for w in ordered:
            s = w.steps_since_meal
            if s >= self.FORCE_LEAVE_THRESHOLD:
                leaving.add(id(w))          # about to starve: must go eat
            elif s >= self.LEAVE_THRESHOLD:
                # leave only if another fresh warrior keeps attacking
                others_fresh = [
                    o for o in ordered
                    if o is not w
                    and id(o) not in leaving
                    and o.steps_since_meal < self.FRESH_LIMIT
                ]
                if others_fresh:
                    leaving.add(id(w))

        # If nobody is left to attack, keep the least hungry warrior in the cave
        if warriors and all(id(w) in leaving for w in warriors):
            least_hungry = min(warriors, key=lambda c: c.steps_since_meal)
            if least_hungry.steps_since_meal < self.FORCE_LEAVE_THRESHOLD:
                leaving.discard(id(least_hungry))

        for w in warriors:
            plan[id(w)] = "village" if id(w) in leaving else "attack"

        # Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])
```