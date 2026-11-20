## Strategy: Threshold-based feeding, spawn-first farming, and continuous cave attacks

**Village phase (`assign_in_village`):**
- **Feeding first:** Any villager with `steps_since_meal >= 3` goes to "eat". This leaves a margin before the 6-step starvation limit, which matters because a warrior needs one step to walk back from the Cave.
- **Warriors:** Warriors that are fed (`steps_since_meal < 3`) go to "cave" to attack. Warriors are never assigned to farm or spawn, so they can keep attacking.
- **Spawning with the remaining wheat:** Wheat is budgeted after meals are reserved. Farmers are used as spawn inputs first, so that warriors (the main damage dealers) are produced as early as possible. Two farmers go to "spawn warrior" whenever at least 12 spare wheat exists. Then, with any leftover wheat, pairs of farmers go to "spawn farmer" at 10 wheat each. This meets the requirement of at least one new farmer and at least two new warriors.
- **Farming:** All remaining fed farmers go to "farm".

**Cave phase (`assign_in_cave`):**
- **Attacking:** Fed warriors (`steps_since_meal < 3`) attack the Dragon. Keeping them attacking every step prevents regeneration.
- **Retreating to eat:** Warriors with `steps_since_meal >= 3` go to "village" so they can eat before they starve.
- **Farmers:** Any farmer found in the Cave is sent back to the Village.

The Dragon's HP and the wheat stock are read from `environment.dragon` and `environment.farm`. Every component receives exactly one group assignment in each phase, since the strategy reassigns all components every step.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Villagers that have not eaten for >= 3 steps are sent to eat (safety margin
      below the 6-step starvation limit).
    - Warriors that are fed go to the Cave and attack the Dragon.
    - Farmers stay in the Village: they eat if needed, spawn new villagers when wheat
      allows (warriors first, since they deal more damage), and farm otherwise.
    - In the Cave, fed warriors attack; hungry warriors (>= 3 steps without a meal)
      return to the Village to eat. Farmers in the Cave are sent back to the Village.
    """

    EAT_THRESHOLD = 3
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        hungry = []
        warriors_ready = []
        farmers_ready = []

        for c in components:
            steps = c.steps_since_meal
            if steps >= self.EAT_THRESHOLD:
                hungry.append(c)
            elif c.role == "Warrior":
                warriors_ready.append(c)
            else:
                farmers_ready.append(c)

        # Meals are reserved first (1 wheat each).
        wheat_avail = wheat - len(hungry)

        # Spawning uses fed farmers as inputs (they are not needed in the Cave).
        spawn_warrior = []
        spawn_farmer = []
        pool = list(farmers_ready)

        if wheat_avail >= self.WARRIOR_SPAWN_COST and len(pool) >= 2:
            spawn_warrior = pool[:2]
            pool = pool[2:]
            wheat_avail -= self.WARRIOR_SPAWN_COST

        while wheat_avail >= self.FARMER_SPAWN_COST and len(pool) >= 2:
            pair = pool[:2]
            pool = pool[2:]
            spawn_farmer.extend(pair)
            wheat_avail -= self.FARMER_SPAWN_COST

        # Anyone not yet placed in a spawn group keeps farming.
        farming = pool

        # Warriors that are fed go to the Cave to attack.
        cave_group = warriors_ready

        for c in components:
            if c in hungry:
                environment.assign_group(c, "eat")
            elif c in spawn_warrior:
                environment.assign_group(c, "spawn warrior")
            elif c in spawn_farmer:
                environment.assign_group(c, "spawn farmer")
            elif c in cave_group:
                environment.assign_group(c, "cave")
            elif c in farming:
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior":
                # Farmers should not be in the Cave.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.EAT_THRESHOLD:
                # Hungry warriors must go back to eat in time.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```