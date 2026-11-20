## Fixes

The two remaining failures are starvation at step 7 for the same villager (Laura). Starvation happens when a villager goes 6 steps without eating. Three things in the previous version caused this:

1. **Eating threshold too late.** Villagers were only fed at `steps_since_meal >= 3`. Any delay, such as a shortage of wheat or a trip to the Cave, could push a villager to 6 steps. The village threshold is now 2, so everyone eats well before the limit.
2. **Spawning consumed the food reserve.** A spawn could use the wheat that the next step's meals needed. Spawning now only happens if enough wheat remains to feed every villager who will be hungry next step.
3. **Cave return came too late.** A warrior in the Cave needs one step to walk back, and then one step to eat. Warriors now leave the Cave at `steps_since_meal >= 3` instead of 4, so they reach the Village before the limit.

The spawn requirements (at least one Farmer and two Warriors) are still tracked. Spawning is still prioritized, but only when the reserve allows it.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - In the Village, villagers eat early (after 2 unfed steps), limited by wheat,
        with the most hungry fed first.
      - A spawn is only issued if enough wheat remains to feed the villagers who will
        be hungry next step, so spawning never starves anyone.
      - Unfed or hungry Warriors stay in the Village to eat; fed Warriors go to the Cave.
      - In the Cave, Warriors attack while fed; Warriors with 3+ unfed steps and any
        Farmers return to the Village early enough to eat before starving.
    """

    EAT_THRESHOLD_VILLAGE = 2
    CAVE_RETURN_THRESHOLD = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LAST_SPAWN_STEP = 20
    MIN_FARMER_SPAWNS = 1
    MIN_WARRIOR_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self.warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # Most hungry villagers first.
        ordered = sorted(components, key=lambda c: c.steps_since_meal, reverse=True)

        # Feed hungry villagers, limited by available wheat.
        hungry = [c for c in ordered if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        eat_list = hungry[:wheat]
        eat_ids = {id(c) for c in eat_list}
        budget = wheat - len(eat_list)

        # Villagers who will need a meal next step must keep their wheat reserved.
        next_step_hungry = sum(
            1 for c in ordered
            if id(c) not in eat_ids and c.steps_since_meal + 1 >= self.EAT_THRESHOLD_VILLAGE
        )

        not_eating = [c for c in ordered if id(c) not in eat_ids]
        farmers = [c for c in not_eating if c.role == "Farmer"]

        spawn_group = None  # (group name, members)
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            want_farmer_first = self.farmers_spawned < self.MIN_FARMER_SPAWNS
            can_farmer = budget - self.FARMER_SPAWN_COST >= next_step_hungry
            can_warrior = budget - self.WARRIOR_SPAWN_COST >= next_step_hungry
            if want_farmer_first and can_farmer:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1
            elif can_warrior:
                spawn_group = ("spawn warrior", farmers[:2])
                budget -= self.WARRIOR_SPAWN_COST
                self.warriors_spawned += 1
            elif can_farmer:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1

        spawn_ids = {id(c) for c in spawn_group[1]} if spawn_group else set()

        # Assign every villager to exactly one group.
        for c in ordered:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, spawn_group[0])
            elif c.role == "Farmer":
                environment.assign_group(c, "farm")
            elif c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                # Unfed warrior: stay and eat as soon as wheat allows.
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```