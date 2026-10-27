## Revised strategy: Five Farmers for Wheat, Warriors Spawned Whenever Affordable

The 20.3-step result came from shorter Cave trips. The remaining limit is wheat: each Warrior spawn costs 12 wheat, and Farmers supply the wheat. Each spawn also takes two Farmers off the farm for that step, so the economy has to stay ahead of the spawn rate.

**Changes:**

1. **Five Farmers instead of four.** An extra Farmer adds about 5 wheat per step. That covers the eating cost and funds Warrior spawns earlier.
2. **Warrior spawns as soon as wheat allows.** Warrior spawns use a Farmer pair whenever wheat is at least 12 and the Warrior target is not reached. Farmer spawns happen only while the Farmer count is below 5, and they run after Warrior spawns when wheat is enough for both.
3. **Warrior target raised to 12, kept as a cap.** The cap stops the wheat budget from being spent on Warriors that cannot reach the Cave in time.
4. **Unchanged safety rules.** Villagers with 3 or more steps without a meal eat first. A Warrior in the Cave returns to eat at 4 steps of hunger, so it arrives with at most 5 and eats before the 6-step limit. Farmers never enter the Cave, and every healthy Warrior attacks each step, so the Dragon is not left unattacked for long.

**Expected effect:** Slightly more wheat in the early game, so Warriors arrive in the Cave sooner and the Dragon's HP falls faster. The gain is probably small, and the exact result depends on the simulation's starting wheat and villager counts.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: eat immediately once hunger reaches this (starvation at 6).
    EAT_THRESHOLD = 3
    # Cave: a Warrior returns to eat only at this hunger (reaches Village at <= 5).
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
        warriors_in_village = [c for c in components
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

        # 3. Top up the Farmer base with any remaining wheat and pairs.
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

        # 4. Non-hungry Warriors in the Village go straight to the Cave to attack.
        for c in warriors_in_village:
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
                # Hungry Warriors go back to eat before attacking again.
                environment.assign_group(c, "village")
            else:
                # Healthy Warriors keep attacking the Dragon.
                environment.assign_group(c, "attack")
                attackers += 1
        self._cave_attackers = attackers
```