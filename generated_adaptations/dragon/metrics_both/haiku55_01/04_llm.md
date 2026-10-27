## Revised strategy: Early Breeding Burst, Then Continuous Strikes

The 28-step win was slow because the Warrior count stayed low. The Dragon has 100 HP and each Warrior deals 3 damage per step, so the win depends on fielding many Warriors quickly and keeping them attacking. The changes below target that.

**Changes from the previous version:**

1. **Economic breeding first.** A new Farmer costs 10 wheat and produces 5 wheat per step, so it pays for itself in about two steps. The strategy spawns Farmers early while the Farmer count is below a small target (6). Spawning uses as many pairs of Farmers as wheat and the target allow, not just one pair per step.
2. **Warrior surge.** Once the Farmer base is established, every spare pair of Farmers goes to `spawn warrior` whenever wheat is at least 12. The Warrior cap is raised to 8, so the Dragon takes roughly 3 to 4 steps of full-strength attacks at the end.
3. **Warriors never idle in the Village.** Every Warrior that is not hungry goes straight to the Cave, including ones just spawned.
4. **Hunger handling.** Warriors eat when they reach 3 steps without a meal, which keeps them under the 6-step starvation limit. A hungry Warrior in the Cave returns to eat, then comes back. Warriors that just ate are not sent back to the Cave in the same step.
5. **Population tracking.** The Cave count is updated from both the Cave step and the Village assignments, so breeding targets stay accurate between steps.

**Expected effect:** More Warriors reach the Cave sooner, so the Dragon takes more damage per step and dies earlier. The 30-step limit and starvation rules are still respected by the existing hunger thresholds.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Eat when this many steps have passed without a meal (starvation at 6).
    EAT_THRESHOLD = 3
    # A Warrior in the Cave with at least this hunger goes back to eat.
    CAVE_RETURN_THRESHOLD = 3
    # Population targets.
    TARGET_FARMERS = 6
    TARGET_WARRIORS = 8
    # Wheat costs.
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Population estimate for villagers currently in the cave.
        self._cave_farmers = 0
        self._cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        # 1. Eat first: villagers close to starving eat now.
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

        # 2. Breeding. Spawn groups need pairs of villagers; Farmers are used so Warriors keep attacking.
        pool = list(village_farmers)

        # Build the Farmer base first (cheap, pays back quickly).
        if total_farmers < self.TARGET_FARMERS and wheat >= self.FARMER_COST and len(pool) >= 2:
            max_pairs = min(len(pool) // 2,
                            wheat // self.FARMER_COST,
                            self.TARGET_FARMERS - total_farmers)
            n = max_pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(c)
            pool = pool[n:]
            wheat -= max_pairs * self.FARMER_COST
            total_farmers += max_pairs

        # Then surge Warriors with any remaining Farmer pairs.
        if total_warriors < self.TARGET_WARRIORS and wheat >= self.WARRIOR_COST and len(pool) >= 2:
            max_pairs = min(len(pool) // 2,
                            wheat // self.WARRIOR_COST,
                            self.TARGET_WARRIORS - total_warriors)
            n = max_pairs * 2
            for c in pool[:n]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(c)
            pool = pool[n:]
            wheat -= max_pairs * self.WARRIOR_COST
            total_warriors += max_pairs

        # 3. Warriors that are not hungry go to the Cave to attack.
        cave_sent_warriors = 0
        for c in village_warriors:
            if c in assigned:
                continue
            environment.assign_group(c, "cave")
            assigned.add(c)
            cave_sent_warriors += 1

        # 4. Everyone else (remaining Farmers) farms.
        for c in components:
            if c in assigned:
                continue
            environment.assign_group(c, "farm")
            assigned.add(c)

        # Keep the population estimate in step with what was just assigned.
        self._cave_warriors += cave_sent_warriors

    def assign_in_cave(self, components, environment, group_ids, step: int):
        farmers = 0
        warriors = 0
        for c in components:
            if c.role == "Farmer":
                # Farmers never fight; they return to the Village.
                environment.assign_group(c, "village")
                farmers += 1
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Hungry Warriors go back to eat before attacking again.
                environment.assign_group(c, "village")
                warriors += 1
            else:
                # Healthy Warriors keep attacking the Dragon every step.
                environment.assign_group(c, "attack")
                warriors += 1
        self._cave_farmers = farmers
        self._cave_warriors = warriors
```