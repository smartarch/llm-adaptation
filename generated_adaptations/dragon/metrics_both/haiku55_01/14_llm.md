## Revised strategy: Eat Before Leaving for the Cave

The last several versions plateaued around 20 to 22 steps, and the differences are within noise. Warriors spend the most time out of the fight: they walk to the Village, eat, and walk back. To cut that waste, this version changes when Warriors eat, not how many Farmers or Warriors exist.

**Changes:**

1. **Warriors top up before leaving.** A Warrior in the Village with 2 or more steps without a meal eats first, if wheat allows. It then leaves for the Cave with a fresh meal, so it can attack for about 4 steps before it must return. Previously Warriors left hungry and turned around sooner.
2. **Round trips are shorter in the Cave.** Warriors in the Cave still return to eat at 4 steps without a meal, so they reach the Village with at most 5 steps of hunger. Eating then happens in the Village on the arrival step, so the 6-step starvation limit is respected.
3. **Eating has priority over spawning, and spawning uses leftover wheat.** Wheat for meals is reserved first. Farmer pairs go to Warriors while wheat covers the cost, then to Farmers.
4. **Unchanged safety rules.** Farmers never enter the Cave. Healthy Warriors attack every step. Villagers at 3 or more steps without a meal always eat.

**Expected effect:** Warriors attack for more consecutive steps per trip, so the Dragon's HP falls faster and the Dragon is less likely to regenerate between attacks. The gain may be modest, and the simulation results will show whether it is real.

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
    # Population targets.
    TARGET_FARMERS = 5
    TARGET_WARRIORS = 12
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

        # 1. Eat first: starving-risk villagers always eat.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                wheat -= 1

        # 2. Warriors that are partly hungry eat before leaving for the Cave,
        #    so they have more attacking steps per trip.
        for c in components:
            if c in assigned or c.role != "Warrior":
                continue
            if c.steps_since_meal >= self.WARRIOR_PRE_EAT and wheat >= 1:
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

        # 3. Spend spare Farmer pairs on Warriors first (Warriors deal the damage).
        if total_warriors < self.TARGET_WARRIORS and wheat >= self.WARRIOR_COST and len(pool) >= 2:
            pairs = min(len(pool) // 2,
                        wheat // self.WARRIOR_COST,
                        self.TARGET_WARRIORS - total_warriors)
            n = pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(c)
            pool = pool[n:]
            wheat -= pairs * self.WARRIOR_COST
            total_warriors += pairs

        # 4. Top up the Farmer base with leftover wheat and pairs.
        if total_farmers < self.TARGET_FARMERS and wheat >= self.FARMER_COST and len(pool) >= 2:
            pairs = min(len(pool) // 2,
                        wheat // self.FARMER_COST,
                        self.TARGET_FARMERS - total_farmers)
            n = pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(c)
            pool = pool[n:]
            wheat -= pairs * self.FARMER_COST
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