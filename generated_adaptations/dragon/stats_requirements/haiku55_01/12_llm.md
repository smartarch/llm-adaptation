## Revised strategy: economy-first farmer boost, then parallel warrior spawning

**What went wrong:** The Dragon was left at 13 HP in the losing games. Warrior spawning started immediately with a small wheat supply, so the warrior count grew slowly and wheat ran short. Farmers were spawned only after the warrior target was met, so the economy never grew. Attackers averaged 1.3 per step, which is too few to kill a 100 HP Dragon quickly.

**Changes:**

1. **Early farmer economy.** A farmer produces 5 wheat per step and costs 10 wheat, so it pays for itself within about two steps. During the first few steps, idle farmers are paired into "spawn farmer" groups until a farmer target is reached. This increases wheat income for the warrior spawns that follow.
2. **Parallel warrior spawning.** Once the economy is in place, every disjoint pair of idle villagers is assigned to "spawn warrior" in the same step, as long as the wheat budget covers the cost plus the meals still needed. The budget is charged for meals first, so spawning never causes starvation.
3. **Accurate warrior count.** The total is the number of warriors in the Village plus the warriors that stayed in the Cave during the last cave phase. This avoids overspawning or underspawning.
4. **Fill the Cave with fed warriors.** Warriors with `steps_since_meal < 2` go to the Cave. Warriors at 2 or more steps eat first.
5. **Starvation-safe cave rotation.** A warrior in the Cave attacks while `steps_since_meal < 4` and returns to the Village at 4. This keeps everyone below the 6-step starvation limit, and the Dragon is attacked nearly every step.
6. **Farmers stay in the Village** and keep the wheat supply running.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2 (1 wheat each, budgeted first).
      - Early game: spawn farmers in pairs (cheap wheat economy) up to FARMER_TARGET.
      - Then spawn warriors in parallel pairs while below WARRIOR_TARGET and
        wheat covers cost + reserve for meals.
      - Fed warriors (steps_since_meal < 2) go to the Cave; everyone else farms.
    Cave:
      - Warriors with steps_since_meal < 4 attack.
      - Warriors at 4+ steps since meal return to the Village to eat.
      - Farmers never fight; any farmer in the Cave returns to the Village.
    """

    EAT_THRESHOLD = 2
    CAVE_RETURN_HUNGER = 4
    WARRIOR_TARGET = 10
    FARMER_TARGET = 5
    ECONOMY_STEPS = 8          # farmer spawning is prioritized during these steps
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cave_warriors = 0   # warriors that stayed in the Cave last cave phase

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # Reserve wheat for meals of warriors currently in the Cave next step.
        reserve = self._cave_warriors

        idle = [c for c in components if c not in assigned]
        idle_farmers = [c for c in idle if c.role == "Farmer"]
        idle_warriors = [c for c in idle if c.role == "Warrior"]

        village_farmers = sum(1 for c in components if c.role == "Farmer")
        village_warriors = sum(1 for c in components if c.role == "Warrior")
        total_warriors = village_warriors + self._cave_warriors

        # 2) Spawning.
        if step < self.ECONOMY_STEPS and village_farmers < self.FARMER_TARGET:
            # Economy phase: farmer pairs.
            i = 0
            while (i + 1 < len(idle_farmers)
                   and village_farmers < self.FARMER_TARGET
                   and budget - reserve >= self.FARMER_COST):
                a, b = idle_farmers[i], idle_farmers[i + 1]
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                assigned.add(a)
                assigned.add(b)
                budget -= self.FARMER_COST
                village_farmers += 1
                i += 2
            idle_farmers = [c for c in idle_farmers if c not in assigned]

        if total_warriors < self.WARRIOR_TARGET:
            # Warrior pairs, farmers used as spawners first.
            pool = [c for c in idle_farmers if c not in assigned] + \
                   [c for c in idle_warriors if c not in assigned]
            i = 0
            while (i + 1 < len(pool)
                   and total_warriors < self.WARRIOR_TARGET
                   and budget - reserve >= self.WARRIOR_COST):
                a, b = pool[i], pool[i + 1]
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                assigned.add(a)
                assigned.add(b)
                budget -= self.WARRIOR_COST
                total_warriors += 1
                i += 2

        # 3) Remaining villagers: fed warriors to the Cave, everyone else farms.
        for c in components:
            if c in assigned:
                continue
            if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        stayers = 0
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
                stayers += 1
            else:
                environment.assign_group(c, "village")
        self._cave_warriors = stayers
```