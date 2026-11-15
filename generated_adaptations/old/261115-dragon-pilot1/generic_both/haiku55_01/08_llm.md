## Revised strategy: faster warrior build-up

**Diagnosis:** The win rate is now 100%, and the remaining cost is time. The Dragon needs about 34 warrior hits, so the win time depends on how many warriors are attacking each step. The current version targets 6 warriors and spawns them after farmers, so the attack force grows slowly. Warriors that are used as a spawn pair also skip their attack that step.

**Changes:**

1. **Larger attack force.** The warrior target rises from 6 to 8, so more warriors can attack in parallel and the Dragon takes damage faster.
2. **Warriors before extra farmers.** Once the two required farmers exist, wheat goes to warrior spawns first. Farmers are kept as the main spawn pair, so warriors aren't pulled from the cave to spawn.
3. **Farmers as spawn pairs.** Spawn pairs are drawn from idle farmers whenever possible, so attacking warriors keep attacking. Warriors are used only when no two farmers are available.
4. **Unchanged safety rules.** Warriors still eat at a meal clock of 3, walk home from the cave at 4, and are never sent out hungry. Meals are still capped by the wheat stock, and every villager is assigned exactly once.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Farmers must eat before they reach 6 steps without food.
    FARMER_EAT_THRESHOLD = 4
    # Warriors eat in the Village once their meal clock reaches this value.
    WARRIOR_EAT_THRESHOLD = 3
    # Warriors in the Cave walk home once their meal clock reaches this value.
    CAVE_RETURN_THRESHOLD = 4
    # Target population.
    MIN_FARMERS = 2
    MIN_WARRIORS = 8

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
        idle_farmers = [c for c in non_eaters if c.role == "Farmer"]

        # 2. Choose spawning. Farmers first until the minimum is reached,
        #    then warriors, using idle farmers as the spawn pair when possible.
        spawn_group = None
        spawn_ids = set()

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