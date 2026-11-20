## Strategy: SmartAdaptation

The strategy uses simple priority rules that match the game's constraints.

**In the Village**
1. **Eat first:** any villager (Farmer or Warrior) that has gone 3 or more steps without eating goes to the "eat" group. This keeps everyone clear of the 6-step starvation limit and makes Warriors eat before they go to the Cave.
2. **Send fed Warriors to the Cave:** Warriors that ate recently go to the "cave" group to attack.
3. **Spawn while wheat allows:** after reserving wheat for the meals planned this step, the strategy spawns a new Warrior (12 wheat, using 2 Farmers in "spawn warrior") if affordable, otherwise a new Farmer (10 wheat, using 2 Farmers in "spawn farmer"). Spawning stops after step 20 so new units can still fight within the 30-step limit.
4. **Farm:** every remaining Farmer stays in the Village on the "farm" group. Farmers never go to the Cave.

**In the Cave**
- Warriors that have gone 4 or more steps without eating return to the "village" group so they can eat in time.
- Other Warriors stay in the Cave and attack the Dragon every step, which avoids Dragon regeneration.
- Any Farmer that ends up in the Cave is sent back to the Village.

The Warrior threshold (Cave return at 4 steps) leaves room for the one-step trip back, so no villager reaches 6 steps without eating. The cave rules are mirrored from the village eating rule. The code only uses the group names and attributes given in the specification.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - Villagers that have not eaten for >= 3 steps eat in the Village first.
      - Fed Warriors go to the Cave and attack the Dragon.
      - Farmers stay in the Village, farm, and spawn new villagers when wheat allows
        (Warriors preferred, as they deal more damage).
      - In the Cave, Warriors that have not eaten for >= 4 steps return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 3
    EAT_THRESHOLD_CAVE = 4
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LAST_SPAWN_STEP = 20

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat_list = []
        cave_list = []
        farmers = []

        # 1) Eat first: anyone who has not eaten for a while.
        # 2) Fed warriors go to the cave; farmers are candidates for farming/spawning.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                eat_list.append(c)
            elif c.role == "Warrior":
                cave_list.append(c)
            else:
                farmers.append(c)

        # Wheat budget after reserving wheat for this step's meals.
        budget = wheat - len(eat_list)

        spawn_warrior = []
        spawn_farmer = []

        # Spawning uses pairs of farmers that are not eating this step.
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            if budget >= self.WARRIOR_SPAWN_COST:
                spawn_warrior = farmers[:2]
                farmers = farmers[2:]
                budget -= self.WARRIOR_SPAWN_COST
            elif budget >= self.FARMER_SPAWN_COST:
                spawn_farmer = farmers[:2]
                farmers = farmers[2:]
                budget -= self.FARMER_SPAWN_COST

        # Assign every component to exactly one group.
        for c in eat_list:
            environment.assign_group(c, "eat")
        for c in cave_list:
            environment.assign_group(c, "cave")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_CAVE:
                # Healthy enough warrior: attack the Dragon.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and any farmers return to the Village.
                environment.assign_group(c, "village")
```