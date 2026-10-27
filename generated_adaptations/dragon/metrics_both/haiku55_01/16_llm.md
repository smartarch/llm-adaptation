## Revised strategy: Reserve Wheat for Meals and Raise the Warrior Cap

The last several versions landed between 20 and 22 steps. The differences are small enough to be simulation noise, so this version changes only the spending rules and the Warrior cap.

**Changes:**

1. **Wheat reserve for meals.** Before spawning, the strategy keeps 2 wheat in reserve for the next step's meals. A starving Warrior is never left without food because the wheat went to a spawn.
2. **Higher Warrior cap.** The target rises from 12 to 16. Spawning is still limited by wheat and Farmer pairs, so the cap only matters when the economy can support it.
3. **Pre-eating only when wheat allows.** Warriors at 2 or more steps without a meal eat before leaving for the Cave, but only from wheat above the reserve.
4. **Unchanged safety rules.** Villagers at 3 or more steps without a meal always eat. Warriors in the Cave return to eat at 4 steps. Farmers never enter the Cave. Healthy Warriors attack every step.

**Expected effect:** Fewer forced returns to the Village caused by missing food, and more Warriors when wheat is plentiful. The gain may be small, and the simulation will show whether it helps.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: any villager at this hunger eats now (starvation at 6).
    EAT_THRESHOLD = 3
    # Village: a Warrior tops up before leaving for the Cave.
    WARRIOR_PRE_EAT = 2
    # Cave: a Warrior returns to eat at this hunger (reaches Village at <= 5).
    CAVE_RETURN_THRESHOLD = 4
    # Wheat kept back so that meals for the next step are always affordable.
    WHEAT_RESERVE = 2
    # Population targets.
    TARGET_FARMERS = 5
    TARGET_WARRIORS = 16
    # Wheat costs.
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warriors that stayed in the Cave attacking at the last cave step.
        self._cave_attackers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        # 1. Eat first: villagers close to starving always eat.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                wheat -= 1

        # 2. Partly hungry Warriors top up before leaving, if wheat is spare.
        for c in components:
            if c in assigned or c.role != "Warrior":
                continue
            if c.steps_since_meal >= self.WARRIOR_PRE_EAT and wheat - 1 >= self.WHEAT_RESERVE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                wheat -= 1

        pool = [c for c in components if c not in assigned and c.role == "Farmer"]
        warriors_ready = [c for c in components
                          if c not in assigned and c.role == "Warrior"]

        # Each villager is counted once: those in the Village now, plus
        # Warriors still attacking in the Cave from the last cave step.
        total_farmers = len([c for c in components if c.role == "Farmer"])
        total_warriors = len([c for c in components if c.role == "Warrior"]) + self._cave_attackers

        # Wheat available for spawning after keeping a reserve for meals.
        spendable = wheat - self.WHEAT_RESERVE

        # 3. Spend spare Farmer pairs on Warriors first (Warriors deal the damage).
        if total_warriors < self.TARGET_WARRIORS and spendable >= self.WARRIOR_COST and len(pool) >= 2:
            pairs = min(len(pool) // 2,
                        spendable // self.WARRIOR_COST,
                        self.TARGET_WARRIORS - total_warriors)
            n = pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(c)
            pool = pool[n:]
            spendable -= pairs * self.WARRIOR_COST
            total_warriors += pairs

        # 4. Top up the Farmer base with leftover wheat and pairs.
        if total_farmers < self.TARGET_FARMERS and spendable >= self.FARMER_COST and len(pool) >= 2:
            pairs = min(len(pool) // 2,
                        spendable // self.FARMER_COST,
                        self.TARGET_FARMERS - total_farmers)
            n = pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(c)
            pool = pool[n:]
            spendable -= pairs * self.FARMER_COST
            total_farmers += pairs

        # 5. Warriors that are ready go to the Cave to attack.
        for c in warriors_ready:
            environment.assign_group(c, "cave")
            assigned.add(c)

        # 6. Everyone else farms.
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "farm")
                assigned.add(c)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Farmer":
                # Farmers never fight; they return to the Village.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Hungry Warriors go back to eat before they starve.
                environment.assign_group(c, "village")
            else:
                # Healthy Warriors keep attacking the Dragon.
                environment.assign_group(c, "attack")
                attackers += 1
        self._cave_attackers = attackers
```