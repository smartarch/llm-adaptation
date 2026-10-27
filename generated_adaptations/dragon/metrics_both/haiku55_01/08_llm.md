## Revised strategy: Higher Warrior Ceiling, Staggered Cave Returns

The last version was slower (22.3 vs 21.0 steps), which suggests the Warrior count is still the bottleneck. Each Warrior attack deals 3 damage, so the 100 HP Dragon needs about 34 attacks. Attack throughput depends on how many Warriors are in the Cave, and spawning depends on wheat and spare Farmer pairs.

**Changes:**

1. **Higher Warrior ceiling.** The target rises from 10 to 14. Spawns happen only when wheat allows, so extra Warriors come in whenever the economy can support them and never cost the Farmer base.
2. **Farmer base first, then Warriors.** Farmers are topped up to 4 before any Warrior spawn. This keeps about 20 wheat per step flowing, which covers eating (about 1 wheat per Warrior every 3 steps) and funds Warrior spawns.
3. **Spawn cost checks use the remaining wheat.** Each pair is only spawned if the wheat stock covers it after eating, so no spawn is wasted.
4. **Unchanged safety rules.** Villagers with 3 or more steps without a meal eat first. Hungry Warriors in the Cave return to eat. Farmers never enter the Cave. Warriors that are not hungry attack every step, so the Dragon is never left unattacked for more than a couple of steps.

Expected effect: more Warriors attack per step in the middle game, so the Dragon's 100 HP runs out a few steps sooner.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Eat when this many steps have passed without a meal (starvation at 6).
    EAT_THRESHOLD = 3
    # A Warrior in the Cave with at least this hunger goes back to eat.
    CAVE_RETURN_THRESHOLD = 3
    # Population targets.
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 14
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

        # 2. Build the Farmer base first (it funds eating and later spawns).
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

        # 3. Surge Warriors with spare Farmer pairs (Farmers never enter the Cave).
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