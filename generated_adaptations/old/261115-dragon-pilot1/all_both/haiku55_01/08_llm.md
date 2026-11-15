## What was wrong

1. **Hungry warrior sent to the Cave.** When wheat ran out, the village logic put an unfed hungry warrior into the "cave" group. The rule says a warrior with 3 or more unfed steps must not be sent to the Cave. Unfed hungry warriors now stay in the Village on "farm" instead. They are not sent to fight, and they produce wheat, so they can eat on the next step.
2. **Dragon left unattacked.** The Cave rotation only started leaving at 3 hungry steps, which left too little slack when warriors were in sync. Warriors now leave at 2 hungry steps, but only when another warrior stays behind to attack. A forced departure happens at 4 steps, which is still well under the 6-step starvation limit.
3. **Wheat reserve.** Spawning only uses wheat left after the planned meals, so a meal is never starved of wheat in favor of a spawn.

Every component is still assigned exactly once per call through a single plan dictionary.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Villagers with steps_since_meal >= HUNGER_THRESHOLD eat (most hungry first)
        as long as wheat is available for the meal.
      - Hungry warriors that cannot be fed stay in the village (never sent to the cave).
      - Fed warriors go to the cave to attack the dragon.
      - Remaining farmers form pairs to spawn warriors, then farmers, and farm otherwise.
    Cave:
      - Farmers go back to the village.
      - Warriors rotate: a warrior leaves for food once it is hungry, but only while
        another warrior stays behind and keeps attacking (or when it is about to starve).
    Every component is assigned exactly once per call.
    """

    HUNGER_THRESHOLD = 3        # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 2         # cave: a warrior may leave for food at this hunger
    FORCE_LEAVE_THRESHOLD = 4   # cave: a warrior must leave for food at this hunger
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

        # Warriors: the most hungry leave first; keep at least one attacker
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