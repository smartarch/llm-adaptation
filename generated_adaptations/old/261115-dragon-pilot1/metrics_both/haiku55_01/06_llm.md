## Revised strategy: Fewer Farmers, More Warriors, Accurate Population Tracking

The 21-step win is limited by Warrior count. The Dragon has 100 HP and each Warrior hit deals 3, so the win needs roughly 34 Warrior attacks in total. Two changes should speed this up:

1. **Smaller Farmer base, faster Warrior surge.** Four Farmers (about 20 wheat per step) are enough to cover eating and spawning. Once that base exists, every spare Farmer pair goes to `spawn warrior` whenever wheat allows, and the Warrior target rises to 10.
2. **Accurate population tracking.** The previous version counted Warriors that moved from the Cave to the Village twice, which blocked spawns. The population estimate is now computed as "villagers in the Village now" plus "Warriors that stayed in the Cave last step". Each villager is counted exactly once.

Other rules are unchanged. Villagers with 3 or more steps without a meal eat first, which keeps them under the 6-step starvation limit. Healthy Warriors attack every step, and hungry Warriors make a short trip to eat. The first attack still happens in the first few steps.

Expected effect: Warriors reach the target count sooner, so more attacks land per step and the Dragon dies earlier.

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
    TARGET_WARRIORS = 10
    # Wheat costs.
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warriors that stayed in the Cave (attacking) at the last cave step.
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
        warriors_in_village = [c for c in components if c not in assigned and c.role == "Warrior"]

        # Each villager is counted once: those in the Village now, plus
        # Warriors still attacking in the Cave from the last cave step.
        total_farmers = len([c for c in components if c.role == "Farmer"])
        total_warriors = len([c for c in components if c.role == "Warrior"]) + self._cave_attackers

        # 2. Build the small Farmer base first.
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

        # 3. Surge Warriors with spare Farmer pairs (Farmers are never sent to the Cave).
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