## Revised Strategy: Faster Warrior Surge

The win in 25 steps can be improved by reducing wasted steps. The main sources of waste are:

1. **Early return trips.** Warriors return to eat at 3 steps without food, so about half their time in the Cave is spent travelling. Eating at 4 steps still leaves a margin under the 6-step starvation limit, and a returning Warrior eats the step it arrives.
2. **Spawn throughput.** The old cap of two spawns per step was not binding, but spawning was also gated behind an early-farmer rule. Spawning Warriors as soon as wheat and two free Farmers allow maximizes damage per step.
3. **Meal reserve.** Wheat is reserved for meals before spawning, so spawns never starve the economy. The budget logic is kept.

Changes from the previous version:
- Village meals happen at `steps_since_meal >= 3`, so Farmers and newly returned Warriors never reach the starvation limit.
- Warriors in the Cave stay until `steps_since_meal >= 4` before returning.
- Warrior spawns are no longer capped per step; every affordable pair of Farmers spawns a Warrior.
- Early Farmer spawns happen only when no Warrior is affordable and wheat is plentiful, to build the economy without slowing the Warrior surge.

Expected effect: more Warriors in the Cave earlier and fewer transit steps, which should reduce the win time below 25 steps. The exact figure depends on the simulation's starting wheat and villager counts, so it should be checked against the simulator.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Faster warrior surge:
      - Warriors are spawned as soon as wheat and free Farmers allow (no per-step cap).
      - Warriors stay in the Cave longer (return at 4 steps without a meal) to cut transit time.
      - Farmers and Warriors eat in the Village before they risk starvation.
    """

    EAT_THRESHOLD = 3          # Village: eat when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 4  # Cave: Warriors go home to eat at this point
    WARRIOR_COST = 12
    FARMER_COST = 10
    EARLY_FARMER_STEPS = 6     # only consider extra farmers in the first few steps
    EARLY_FARMER_MIN_WHEAT = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        eaters = []
        rest = []
        # 1) Meals first: anyone close to starving eats (1 wheat each)
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []
        spawn_farmer = []

        # 2) Warrior surge: spawn as many Warriors as affordable (no per-step cap)
        if dragon_alive:
            while len(free_farmers) >= 2 and budget >= self.WARRIOR_COST:
                spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
                budget -= self.WARRIOR_COST

        # 3) Early economy: a Farmer pair only if no Warrior was possible and wheat is comfortable
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.EARLY_FARMER_MIN_WHEAT):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Free Warriors head to the Cave to attack
        to_cave = list(free_warriors) if dragon_alive else []
        farming = free_farmers + ([] if dragon_alive else free_warriors)

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farming:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Farmers go home to farm; Warriors go home only when meal is due
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```