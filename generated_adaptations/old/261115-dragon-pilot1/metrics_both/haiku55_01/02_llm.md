## Strategy: Warrior Strike Cycle with Farmer Breeding

**Core idea:** Farmers stay in the Village to produce wheat, feed everyone, and breed new villagers. Warriors do the damage. Every villager eats before its hunger reaches the danger zone.

**Village rules (`assign_in_village`):**
1. **Eat first.** Any villager with `steps_since_meal >= 3` goes to `eat`. This keeps everyone well under the 6-step starvation limit and means a hungry Warrior eats before it leaves for the Cave.
2. **Breed.** Two spare Farmers go to `spawn warrior` when wheat is at least 12 and the Warrior count is below target. Otherwise, two spare Farmers go to `spawn farmer` when wheat is at least 10 and the Farmer count is below target. Spawning draws only on Farmers, so the Warriors keep attacking.
3. **Send Warriors out.** Every non-hungry Warrior goes to `cave` on the first step, so the Dragon is hit within the first 15 steps.
4. **Farm.** All remaining Farmers go to `farm`.

**Cave rules (`assign_in_cave`):**
1. Farmers never stay in the Cave, so they go back to `village`.
2. Warriors with `steps_since_meal < 3` go to `attack`.
3. Warriors with `steps_since_meal >= 3` return to `village` to eat, then come back. This prevents starvation and keeps them from attacking while starving.

**Known limitations:** The strategy tracks cave population only from the previous cave step, so population targets are approximate. The "never unattacked for more than 2 steps" rule is only partly enforced: Warriors leave for meals at different times, but the strategy does not explicitly stagger departures. Thresholds are tuned for a 6-step starvation limit with a 1-step travel time.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Eat when this many steps have passed without a meal (starvation at 6).
    EAT_THRESHOLD = 3
    # A Warrior in the Cave with at least this hunger goes back to eat.
    CAVE_RETURN_THRESHOLD = 3
    # Population targets for breeding.
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 4
    # Wheat costs.
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Population seen in the cave during the last cave step (approximate).
        self._cave_farmers = 0
        self._cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        # 1. Eat first: every villager close to starving eats now.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD:
                environment.assign_group(c, "eat")
                assigned.add(c)
                wheat -= 1

        rest = [c for c in components if c not in assigned]
        village_farmers = [c for c in rest if c.role == "Farmer"]
        village_warriors = [c for c in rest if c.role == "Warrior"]

        # Estimated total population (village now + cave at last step).
        total_farmers = len([c for c in components if c.role == "Farmer"]) + self._cave_farmers
        total_warriors = len([c for c in components if c.role == "Warrior"]) + self._cave_warriors

        # 2. Breeding: spawn groups need at least two villagers each.
        spawn_pool = list(village_farmers)
        spawned_warrior = False
        if (total_warriors < self.TARGET_WARRIORS
                and wheat >= self.WARRIOR_COST
                and len(spawn_pool) >= 2):
            for c in spawn_pool[:2]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(c)
            spawn_pool = spawn_pool[2:]
            wheat -= self.WARRIOR_COST
            spawned_warrior = True

        if (not spawned_warrior
                and total_farmers < self.TARGET_FARMERS
                and wheat >= self.FARMER_COST
                and len(spawn_pool) >= 2):
            for c in spawn_pool[:2]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(c)
            spawn_pool = spawn_pool[2:]
            wheat -= self.FARMER_COST

        # 3. Warriors that are not hungry go to the Cave to attack.
        for c in village_warriors:
            if c in assigned:
                continue
            environment.assign_group(c, "cave")
            assigned.add(c)

        # 4. Everyone else (remaining Farmers) farms.
        for c in components:
            if c in assigned:
                continue
            environment.assign_group(c, "farm")
            assigned.add(c)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        farmers = 0
        warriors = 0
        for c in components:
            if c.role == "Farmer":
                # Farmers stay in the Village.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Hungry Warriors go back to eat before attacking again.
                environment.assign_group(c, "village")
            else:
                # Healthy Warriors attack the Dragon.
                environment.assign_group(c, "attack")
            if c.role == "Farmer":
                farmers += 1
            else:
                warriors += 1
        self._cave_farmers = farmers
        self._cave_warriors = warriors
```