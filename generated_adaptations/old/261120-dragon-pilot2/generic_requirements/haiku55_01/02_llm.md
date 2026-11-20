## Strategy: Eat-Aware Warrior Rush

The strategy aims to kill the Dragon quickly with warriors while keeping every villager fed.

**Village phase (`assign_in_village`):**
1. **Eating has priority.** Any villager with `steps_since_meal >= 3` goes to "eat" (while wheat remains). This keeps everyone well under the 6-step starvation limit and makes warriors fit to attack.
2. **Spawning.** Two remaining farmers are paired into "spawn warrior" while wheat allows (12 per warrior). Warriors are the damage dealers, so this is the priority. A limited number of warrior spawns is issued, and one farmer spawn is allowed later if wheat is plentiful. Wheat is reserved for meals first.
3. **Warriors** that are fed (`steps_since_meal < 3`) and healthy go to the "cave" to attack.
4. **Farmers** that remain stay on the "farm" to produce wheat.

**Cave phase (`assign_in_cave`):**
1. Any villager with `steps_since_meal >= 3` goes to the "village" to eat, so it can return in time. Moving takes one step, so the threshold is set a little below the recommended 4 as a safety margin.
2. Farmers that somehow end up in the cave are sent back to the village.
3. Fed warriors go to "attack", which keeps the Dragon under continuous pressure and limits its regeneration.
4. Everything else stays in the "cave".

Every component is assigned exactly once in each phase, and all group names come from `group_ids`.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Eat-aware warrior rush:
      - Villagers that have not eaten for >= 3 steps are sent to eat first.
      - Remaining farmers are paired up to spawn new warriors while wheat allows.
      - Fed warriors go to the cave and attack the Dragon.
      - Cave villagers that are hungry return to the village; farmers never stay in the cave.
    """

    EAT_THRESHOLD = 3          # eat (or go eat) once this many steps have passed without a meal
    WARRIOR_SPAWN_LIMIT = 3    # maximum number of warrior spawn orders issued in total
    FARMER_SPAWN_LIMIT = 1     # maximum number of farmer spawn orders issued in total

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_orders = 0
        self.farmer_spawn_orders = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        budget = wheat  # wheat still available during this step's decisions

        eaters = []
        others = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                others.append(c)

        # Hungry villagers that cannot eat (no wheat) still need to be placed somewhere.
        # They are kept on the farm; they will starve only if wheat runs out entirely.
        warriors = [c for c in others if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD]
        farmers = [c for c in others if c.role != "Warrior"]
        leftovers_warriors = [c for c in others if c.role == "Warrior" and c.steps_since_meal >= self.EAT_THRESHOLD]

        spawn_warrior = []
        spawn_farmer = []

        # Spawn warriors from pairs of farmers while wheat allows.
        while (len(farmers) - len(spawn_warrior) - len(spawn_farmer) >= 2
               and budget >= 12
               and self.warrior_spawn_orders < self.WARRIOR_SPAWN_LIMIT):
            pool = [f for f in farmers if f not in spawn_warrior and f not in spawn_farmer]
            spawn_warrior.extend(pool[:2])
            budget -= 12
            self.warrior_spawn_orders += 1

        # One farmer spawn if there is still plenty of wheat and enough spare farmers.
        pool = [f for f in farmers if f not in spawn_warrior and f not in spawn_farmer]
        if (len(pool) >= 2 and budget >= 10 + 12
                and self.farmer_spawn_orders < self.FARMER_SPAWN_LIMIT):
            spawn_farmer.extend(pool[:2])
            budget -= 10
            self.farmer_spawn_orders += 1

        # Assign everyone exactly once.
        for c in eaters:
            environment.assign_group(c, "eat")

        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")

        for c in warriors:
            # Fed warriors go to attack the Dragon.
            environment.assign_group(c, "cave")

        for c in leftovers_warriors:
            # Hungry but no wheat to eat right now: stay in village and work to produce wheat.
            environment.assign_group(c, "farm")

        for c in farmers:
            if c in spawn_warrior or c in spawn_farmer:
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior":
                # Farmers are not meant to fight; send them back to farm.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.EAT_THRESHOLD:
                # Hungry warrior must go eat before it starves.
                environment.assign_group(c, "village")
            else:
                # Fed warrior attacks the Dragon.
                environment.assign_group(c, "attack")
```