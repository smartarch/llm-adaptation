## Revised strategy: longer cave stays with staggered warrior rotation

**Diagnosis of the 33% win rate:** The Dragon has 100 HP and each warrior hit does 3 damage, so about 34 warrior hits are needed. The old rules return a warrior to the Village as soon as its meal clock reaches 2, and a warrior that arrives in the Village eats immediately. Each warrior therefore spends about half its time walking or eating, and the average damage per step is low. Wins also came late, at about step 30.

**Changes:**

1. **Longer cave stays.** A warrior now attacks until its meal clock reaches 4 (`CAVE_RETURN_THRESHOLD = 4`), then walks home. It arrives with a clock of about 5, which is still under the 6-step starvation limit, and eats right away.
2. **Warriors skip unnecessary meals.** In the Village, a warrior eats only once its clock reaches 3 (`WARRIOR_EAT_THRESHOLD`). A warrior with a clock of 0 to 2 goes straight back to the Cave. This follows the rule that a warrior with 3 or more unfed steps must eat before going out.
3. **More warriors.** The target is 6 warriors, which means more hits per step.
4. **Coverage.** Warriors with lower clocks are staggered, so at least one warrior attacks in every step. This keeps the Dragon from regenerating.
5. **Wheat stays capped.** Meals are still limited to the wheat in stock, and each villager is assigned exactly once.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors eat in the Village once their meal clock reaches this value.
    WARRIOR_EAT_THRESHOLD = 3
    # Warriors in the Cave walk home once their meal clock reaches this value.
    CAVE_RETURN_THRESHOLD = 4
    # Target population used to decide what to spawn.
    MIN_FARMERS = 2
    MIN_WARRIORS = 6

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1. Collect everyone who needs a meal now.
        wants_food = []
        for c in components:
            if c.role == "Farmer":
                needs = c.steps_since_meal >= self.FARMER_EAT_THRESHOLD
            else:
                needs = c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD
            if needs:
                wants_food.append(c)

        # Feed the most urgent first, never more villagers than the wheat stock allows.
        wants_food.sort(key=lambda c: c.steps_since_meal, reverse=True)
        eaters = wants_food[:max(0, wheat)]
        eater_ids = {id(c) for c in eaters}
        wheat_after_meals = wheat - len(eaters)

        non_eaters = [c for c in components if id(c) not in eater_ids]

        # 2. Choose spawning from idle (non-eating) villagers, preferring farmers as the pair.
        spawn_group = None
        spawn_ids = set()
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        if len(farmers) < self.MIN_FARMERS and wheat_after_meals >= 10 and len(non_eaters) >= 2:
            spawn_group = "spawn farmer"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_ids = {id(c) for c in pool[:2]}
        elif len(warriors) < self.MIN_WARRIORS and wheat_after_meals >= 12 and len(non_eaters) >= 2:
            spawn_group = "spawn warrior"
            pool = idle_farmers if len(idle_farmers) >= 2 else non_eaters
            spawn_ids = {id(c) for c in pool[:2]}

        # 3. Assign every villager to exactly one group.
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif spawn_group is not None and cid in spawn_ids:
                environment.assign_group(c, spawn_group)
            elif c.role == "Warrior" and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                # Warriors with a fresh enough meal clock go (back) to the Cave.
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Farmers should never be here; send them home.
        for c in farmers:
            environment.assign_group(c, "village")

        attackers = []
        returners = []
        for c in warriors:
            # Warriors walk home to eat once their meal clock is high.
            if c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                returners.append(c)
            else:
                attackers.append(c)

        # Keep the Dragon attacked every step: if nobody is eligible,
        # keep the freshest warrior in the fight.
        if not attackers and returners:
            freshest = min(returners, key=lambda c: c.steps_since_meal)
            returners = [c for c in returners if c is not freshest]
            attackers.append(freshest)

        for c in attackers:
            environment.assign_group(c, "attack")
        for c in returners:
            environment.assign_group(c, "village")
```