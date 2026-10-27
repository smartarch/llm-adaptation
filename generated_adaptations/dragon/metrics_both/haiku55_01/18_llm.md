## Revised strategy: Revert to the Best Configuration

The last result (24.3 steps) is worse than the best earlier run (20.3 steps). Two changes in the most recent version probably caused the regression:

- **The wheat reserve delayed spawns.** Holding 2 wheat back each step means Warriors are often 1 wheat short of a spawn, so the Warrior count grows more slowly.
- **Pre-eating sent Warriors to the Village early.** A Warrior that eats before leaving spends extra steps walking between the Cave and the Village instead of attacking.
- **The higher Warrior cap (16) did not help.** Extra Warriors past about 12 mostly add eating load and wheat use, and the Dragon dies on schedule anyway.

This version returns to the 20.3-step configuration:

1. **Warriors are spawned first.** Spare Farmer pairs become Warriors whenever wheat covers the cost, then Farmers fill any remaining gap.
2. **Five Farmers and a Warrior target of 12.** These give steady wheat for eating and spawning without over-committing.
3. **No pre-eating and no reserve.** Warriors leave the Village as soon as they are not starving. Only villagers at 3 or more steps without a meal eat first, which keeps everyone under the 6-step starvation limit.
4. **Cave returns at 4 steps of hunger.** A Warrior reaches the Village with at most 5 steps of hunger and eats before the limit.
5. **Farmers never enter the Cave, and healthy Warriors attack every step.** The Dragon is never left unattacked for long.

Simulation results vary, so the gain over the 21-step versions may be within noise. This version is the most reliable of the configurations tested so far.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: any villager at this hunger eats now (starvation at 6).
    EAT_THRESHOLD = 3
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

        # 1. Eat first: villagers close to starving eat now.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
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

        # 2. Spend spare Farmer pairs on Warriors first (Warriors deal the damage).
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

        # 3. Top up the Farmer base with leftover wheat and pairs.
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

        # 4. Warriors that are ready go to the Cave to attack.
        for c in warriors_ready:
            environment.assign_group(c, "cave")
            assigned.add(c)

        # 5. Everyone else farms.
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