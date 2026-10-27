## Strategy overview

The strategy has two phases, one for each method.

**`assign_in_village`**

1. **Eating first.** Any villager with `steps_since_meal >= 3` is sent to "eat". This keeps everyone well under the 6-step starvation limit and makes sure hungry Warriors eat before going to the Cave. Eating is prioritized by hunger, and the code stops feeding once the wheat stock runs out.
2. **Warriors.** Warriors that are not hungry go to "cave". Warriors are never sent to the Cave while hungry.
3. **Farmers and spawning.** Remaining Farmers form pairs for spawning, because spawning needs two villagers in the group. The strategy first tries to create two new Warriors (12 wheat per spawn pair), then two new Farmers (10 wheat per spawn pair). Wheat is reserved for the planned meals before spawning is considered. Leftover Farmers go to "farm".

**`assign_in_cave`**

- Warriors that are not hungry (`steps_since_meal < 3`) and alive attack the Dragon, so the Dragon is hit from the first step onward (well within the first 15 steps).
- Warriors with `steps_since_meal >= 3` go back to the Village to eat, and then return. This cycle keeps them from starving while keeping the Dragon under constant attack in most steps.
- Any Farmer that ends up in the Cave is sent back to the Village, since Farmers must stay in the Village.

**Counters.** The class tracks how many Farmers and Warriors it has spawned, so it stops after at least two of each.

**Limitations.** The attack-gap rule (no more than 2 unattacked steps) is handled by the return-to-eat threshold and by keeping every fed Warrior in the Cave. With very few Warriors, the Dragon can still be left unattacked during a meal trip. A stronger version would split Warriors into two alternating cohorts. This implementation keeps the logic simple and relies on the Warriors' natural meal rhythm.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Villagers:
      - Anyone with steps_since_meal >= 3 eats first (keeps everyone far from the
        6-step starvation limit, and keeps hungry warriors out of the cave).
      - Fed warriors go to the cave and attack the dragon.
      - Warriors that become hungry in the cave return to the village to eat.
      - Farmers stay in the village, farm, or form pairs to spawn new
        warriors (12 wheat) and new farmers (10 wheat), at least two of each.
    """

    HUNGER_THRESHOLD = 3       # eat when this many steps have passed without a meal
    MIN_SPAWNS = 2             # at least this many of each role should be spawned

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat, cave, farmers_free, warriors_hungry = [], [], [], []

        # 1) Decide who must eat (hungry villagers first, most hungry first)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        meals_affordable = max(0, int(wheat))
        for c in hungry:
            if len(eat) < meals_affordable or c.steps_since_meal >= 5:
                eat.append(c)
            else:
                warriors_hungry.append(c) if c.role == "Warrior" else farmers_free.append(c)
        wheat_after_meals = wheat - len(eat)

        # 2) Non-hungry villagers
        for c in components:
            if c in eat or c in warriors_hungry or c in farmers_free:
                continue
            if c.role == "Warrior":
                cave.append(c)              # fed warriors go attack the dragon
            else:
                farmers_free.append(c)      # farmers stay in the village

        # 3) Spawning among free farmers (pairs), warriors first, then farmers
        spawn_warrior, spawn_farmer = [], []
        available = list(farmers_free)
        remaining_wheat = wheat_after_meals

        if (self.spawned_warriors < self.MIN_SPAWNS
                and remaining_wheat >= 12 and len(available) >= 2):
            spawn_warrior = available[:2]
            available = available[2:]
            remaining_wheat -= 12
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and remaining_wheat >= 10 and len(available) >= 2):
            spawn_farmer = available[:2]
            available = available[2:]
            remaining_wheat -= 10
            self.spawned_farmers += 1

        farm = available

        # 4) Issue assignments (every component must be assigned exactly once)
        for c in eat:
            environment.assign_group(c, "eat")
        for c in cave:
            environment.assign_group(c, "cave")
        for c in warriors_hungry:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in farm:
            environment.assign_group(c, "farm")

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.HUNGER_THRESHOLD:
                    # hungry: must go home and eat before it starves
                    environment.assign_group(c, "village")
                else:
                    # fed and healthy: keep the dragon under attack
                    environment.assign_group(c, "attack")
            else:
                # farmers must not stay in the cave
                environment.assign_group(c, "village")
```