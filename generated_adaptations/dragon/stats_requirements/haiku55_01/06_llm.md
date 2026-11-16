## Revised strategy: maximize simultaneous attackers, with the cave kept full

**What went wrong:** The Dragon survived at 83 HP, and the average number of attackers per step was only 0.8. Warriors were sent to the Cave in too few numbers, and the cave count was reset at the end of every village phase, so the target was often wrong. Dragon damage scales with the number of attackers, so a small, slowly rotating group barely hurts it. Regeneration (5 HP per unattacked step) then undoes much of the progress.

**Changes:**

1. **Track cave occupancy correctly.** `_cave_count` is the number of warriors that stayed in the Cave in the last cave phase, which is the true number of attackers. Warriors sent during the village phase are added to it. It is no longer reset to zero, so the target is not overfilled or underfilled.
2. **Fill the Cave aggressively.** Every fed warrior (`steps_since_meal < 2`) is sent to the Cave until the Cave holds the whole warrior force. Damage per step is the main driver of the win, and the Dragon regenerates whenever it is not hit.
3. **Stay within starvation limits.** Warriors in the Cave attack while `steps_since_meal <= 3`. At 4 or more steps they return to the Village. Anyone at 2 or more steps eats first in the Village, so no villager reaches 6 steps without a meal.
4. **Warrior-first spawning.** Two spare farmers (never attackers) spawn a warrior whenever wheat covers the cost and the next meals. Farmers are spawned only after the warrior target is reached.
5. **Farmers stay on the farm.** They are never sent to the Cave, which keeps wheat flowing for meals and spawns.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2 first.
      - Spawn warriors early using two spare farmers as spawners (they are not
        consumed); spawn one farmer afterwards.
      - Send fed warriors (steps_since_meal < 2) to the Cave until the Cave holds
        all warriors (maximizes damage per step, so the Dragon rarely regenerates).
      - Farmers keep farming.
    Cave:
      - Warriors with steps_since_meal <= 3 attack.
      - Warriors at 4+ steps since meal return to the Village to eat.
      - Farmers never enter the Cave (they go back to the Village if present).
    """

    EAT_THRESHOLD_VILLAGE = 2
    CAVE_RETURN_HUNGER = 4      # attack while steps_since_meal < 4
    WARRIOR_TARGET = 5
    FARMER_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10
    MIN_CAVE_ATTACKERS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self._cave_count = 0   # warriors currently in the Cave (attackers)

    def _count(self, components, role):
        return sum(1 for c in components if c.role == role)

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # 2) Spawning: one spawn group per step.
        total_warriors = (self.warriors_spawned * 0
                          + self._count(components, "Warrior")
                          + self._cave_count)
        free = [c for c in components if c not in assigned]
        farmers_free = [c for c in free if c.role == "Farmer"]
        others_free = [c for c in free if c.role != "Farmer"]

        if total_warriors < self.WARRIOR_TARGET and budget >= self.WARRIOR_COST:
            spawners = (farmers_free + others_free)[:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn warrior")
                    assigned.add(c)
                budget -= self.WARRIOR_COST
                self.warriors_spawned += 1
        elif (self.farmers_spawned < self.FARMER_TARGET
              and total_warriors >= self.WARRIOR_TARGET
              and budget >= self.FARMER_COST):
            spawners = [c for c in farmers_free if c not in assigned][:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn farmer")
                    assigned.add(c)
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Send fed warriors to the Cave until it holds all warriors.
        remaining = [c for c in components if c not in assigned]
        fed_warriors = [c for c in remaining
                        if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE]
        want_in_cave = max(self.MIN_CAVE_ATTACKERS, total_warriors)
        slots = max(0, want_in_cave - self._cave_count)

        sent = set()
        for c in fed_warriors:
            if slots <= 0:
                break
            environment.assign_group(c, "cave")
            sent.add(c)
            slots -= 1

        for c in remaining:
            if c not in sent:
                environment.assign_group(c, "farm")

        # Warriors sent now will be in the Cave; track them.
        self._cave_count += len(sent)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
                attackers += 1
            else:
                environment.assign_group(c, "village")
        # Attackers remain in the Cave; the rest left for the Village.
        self._cave_count = attackers
```