## Strategy: Phased Warrior Raids with Farmer Support

**Core idea:** Farmers stay in the Village to produce wheat, eat, and breed the population. Warriors do the fighting in short raids. Each warrior eats before its hunger timer reaches the limit, and it returns to the Village only when it needs food.

**Village rules (`assign_in_village`):**
1. **Eat first.** Farmers eat at 3 steps without a meal. Warriors eat at 2 steps. This keeps everyone well under the 6-step starvation limit. Meals are limited by the available wheat.
2. **Warriors raid.** A warrior that is not eating and has fresh food (`steps_since_meal <= 1`) and enough HP goes to the Cave.
3. **Spawning.** Spawns use farmers from the "spawn" groups, after eating is budgeted. The strategy spawns a Warrior first (12 wheat) until there are at least 2 Warriors, then Farmers (10 wheat) until there are at least 2 Farmers. A cooldown of 2 steps prevents over-spawning, since the population count lags by a step.
4. **Everyone else farms.**

**Cave rules (`assign_in_cave`):**
1. Warriors attack while they are fresh (`steps_since_meal < 3`) and healthy.
2. A warrior returns to the Village (to eat) once its hunger reaches 3, which leaves room to reach the village before starvation.
3. Farmers that happen to be in the Cave go back to the Village.

**Trade-offs:** Each warrior's cycle is roughly three attack steps, one trip, one meal, and one trip back. With several warriors, their trips are staggered by hunger timing, which helps keep the Dragon from going unattacked for more than two steps. The strategy tracks the Cave population so it can make spawn decisions. It is a heuristic and does not guarantee the Dragon dies within 30 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Hunger thresholds (steps without eating) that trigger a meal
    FARMER_EAT_AT = 3
    WARRIOR_EAT_AT = 2
    # A warrior in the Cave returns to the Village to eat at this hunger level
    WARRIOR_RETURN_AT = 3
    # Warriors may only be sent to the Cave when this fresh
    WARRIOR_RAID_MAX_HUNGER = 1
    # Minimum HP for a warrior to fight
    WARRIOR_MIN_HP = 3
    # Target population
    TARGET_WARRIORS = 2
    TARGET_FARMERS = 2
    SPAWN_COOLDOWN = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0
        self.cave_farmers = 0
        self.spawn_cooldown = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        if self.spawn_cooldown > 0:
            self.spawn_cooldown -= 1

        # 1. Decide who must eat this step (eating has priority over wheat use)
        eaters = []
        for c in components:
            threshold = self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT
            if c.steps_since_meal >= threshold:
                eaters.append(c)

        # Limit eaters by available wheat; the rest farm and may starve
        budget = wheat
        eating = []
        for c in sorted(eaters, key=lambda x: -x.steps_since_meal):
            if budget >= 1:
                eating.append(c)
                budget -= 1
        eating_ids = set(id(c) for c in eating)

        for c in eating:
            environment.assign_group(c, "eat")

        # 2. Warriors that are fresh and healthy go raid the Dragon
        remaining = [c for c in components if id(c) not in eating_ids]
        spawn_candidates = []
        for c in remaining:
            if c.role == "Warrior":
                if c.steps_since_meal <= self.WARRIOR_RAID_MAX_HUNGER and c.hp >= self.WARRIOR_MIN_HP:
                    environment.assign_group(c, "cave")
                else:
                    # Not ready to raid: stay and eat / farm
                    environment.assign_group(c, "farm")
            else:
                spawn_candidates.append(c)

        # 3. Spawning with the remaining wheat (after eating)
        total_warriors = len(warriors) + self.cave_warriors
        total_farmers = len(farmers) + self.cave_farmers
        spawn_assigned = set()

        if self.spawn_cooldown == 0 and budget >= 12 and total_warriors < self.TARGET_WARRIORS:
            if len(spawn_candidates) >= 2:
                for c in spawn_candidates[:2]:
                    environment.assign_group(c, "spawn warrior")
                    spawn_assigned.add(id(c))
                budget -= 12
                self.spawn_cooldown = self.SPAWN_COOLDOWN
        elif self.spawn_cooldown == 0 and budget >= 10 and total_farmers < self.TARGET_FARMERS:
            if len(spawn_candidates) >= 2:
                for c in spawn_candidates[:2]:
                    environment.assign_group(c, "spawn farmer")
                    spawn_assigned.add(id(c))
                budget -= 10
                self.spawn_cooldown = self.SPAWN_COOLDOWN

        # 4. Everyone else farms
        for c in spawn_candidates:
            if id(c) not in spawn_assigned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        self.cave_warriors = 0
        self.cave_farmers = 0

        for c in components:
            if c.role == "Warrior":
                # Go back to eat before starving; otherwise keep attacking
                if c.steps_since_meal >= self.WARRIOR_RETURN_AT or c.hp < self.WARRIOR_MIN_HP:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
                    self.cave_warriors += 1
            else:
                # Farmers never fight; send them home
                environment.assign_group(c, "village")
                self.cave_farmers += 1
```