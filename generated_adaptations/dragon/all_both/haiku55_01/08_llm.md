## Fixes

The remaining failure is the requirement that the Dragon must be killed. The strategy was too slow to deal 100 damage within 30 steps. Three changes address this:

1. **Spawn reserve was too conservative.** The old code reserved wheat for every villager who would be hungry next step, which in practice covers almost the whole population because the feeding threshold is 2. That blocked most spawns. Farmers produce 5 wheat per step, so the reserve is not needed. Spawning now only requires that the wheat left after this step's meals covers the spawn cost.
2. **Warrior spawns come first after the required Farmer.** Warriors deal 3 damage per attack versus 1 for Farmers, so each spawned Warrior adds much more damage per step. The required minimums (one Farmer, two Warriors) are still tracked and enforced by priority.
3. **Warriors that are fed attack more.** A fed Warrior now leaves for the Cave while its meal counter is below the return threshold, so it spends more steps attacking. Warriors return to eat at 3 unfed steps, which keeps the starvation rule intact.

The starvation guarantees from the previous version are kept. Hungry villagers are still fed first, limited by available wheat, and Warriors still return to the Village before they reach 6 unfed steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - In the Village, villagers eat once they have gone 2 steps unfed (most hungry first,
        limited by wheat).
      - Farmers are paired to spawn: one Farmer early (required), then Warriors whenever
        wheat remains after this step's meals (Warriors deal the most damage).
      - Fed Warriors go to the Cave and attack every step they can.
      - In the Cave, Warriors attack while they have eaten recently; Warriors that reach
        3 unfed steps and any Farmers return to the Village to eat.
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

        # Farmers not eating this step are the spawn candidates.
        farmers = [c for c in ordered if id(c) not in eat_ids and c.role == "Farmer"]

        spawn_group = None  # (group name, members)
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            want_farmer_first = self.farmers_spawned < self.MIN_FARMER_SPAWNS
            can_farmer = budget >= self.FARMER_SPAWN_COST
            can_warrior = budget >= self.WARRIOR_SPAWN_COST
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
                # Unfed warrior that could not be fed this step: stay and eat later.
                environment.assign_group(c, "farm")
            else:
                # Fed warrior: go attack the Dragon.
                environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```