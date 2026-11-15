## Fixes

The last run failed on the Dragon-gap check: the Cave often had no attacker for three steps. The previous version sent warriors home at hunger 2 without checking whether anyone else would be left to attack. The changes are:

1. **Cave always has an attacker.** A warrior at hunger 2 or more goes home only if another warrior is still attacking. If the Cave would otherwise be empty, the least hungry warrior stays and attacks while its hunger is at most 3. Its eat trip starts at hunger 3, which is still under the 6-step limit.
2. **Quick turnaround in the Village.** Warriors eat as soon as their hunger is 1 or more, so they are back to hunger 0 when they leave. A fed warrior in the Village goes straight back to the Cave.
3. **More warriors for DPS and rotation.** The warrior target is raised to 4, so enough warriors are always available to cover a trip home. Spawning still uses only free farmers and waits when someone needs a meal.
4. **Farmers still feed everyone.** Farmers eat at hunger 2, and they are never sent to the Cave.

I could not run the simulator here, so the thresholds are a reasoned heuristic, not a verified schedule. If the Dragon-gap test still fails, the next thing to tune is the warrior target count and the fallback hunger limit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Cave (attack) and the Village (eat),
    turning around quickly so the Dragon is attacked almost every step
    and no villager starves.
    """

    WARRIOR_VILLAGE_EAT = 1     # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2              # farmers eat early to keep a safety margin
    CAVE_RETURN = 2             # warriors at/above this hunger leave the Cave...
    MAX_FALLBACK_HUNGER = 3     # ...unless they are needed to keep the Dragon attacked
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 4
    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assignments = {}

        # 1. Meals first, most hungry first. Each meal costs 1 wheat.
        needing_meal = []
        for c in components:
            threshold = self.WARRIOR_VILLAGE_EAT if c.role == "Warrior" else self.FARMER_EAT
            if c.steps_since_meal >= threshold:
                needing_meal.append(c)
        needing_meal.sort(key=lambda c: -c.steps_since_meal)

        unfed = []
        for c in needing_meal:
            if wheat >= 1:
                assignments[c] = "eat"
                wheat -= 1
            else:
                unfed.append(c)

        # Anyone who needs food but cannot get it stays in the Village (never sent to the Cave).
        for c in unfed:
            assignments[c] = "farm"

        free = [c for c in components if c not in assignments]
        free_farmers = [c for c in free if c.role == "Farmer"]
        free_warriors = [c for c in free if c.role == "Warrior"]

        total_farmers = sum(1 for c in components if c.role == "Farmer")
        total_warriors = sum(1 for c in components if c.role == "Warrior")

        # 2. Spawn at most one pair per step, only from free farmers,
        #    and only when no hungry villager is still waiting for food.
        if len(free_farmers) >= 2 and not unfed:
            if total_farmers < self.TARGET_FARMERS and wheat >= self.FARMER_SPAWN_COST:
                for c in free_farmers[:2]:
                    assignments[c] = "spawn farmer"
                free_farmers = free_farmers[2:]
                wheat -= self.FARMER_SPAWN_COST
            elif total_warriors < self.TARGET_WARRIORS and wheat >= self.WARRIOR_SPAWN_COST:
                for c in free_farmers[:2]:
                    assignments[c] = "spawn warrior"
                free_farmers = free_farmers[2:]
                wheat -= self.WARRIOR_SPAWN_COST

        # 3. Fed, free warriors head straight back to the Cave.
        for c in free_warriors:
            assignments[c] = "cave"

        # 4. Everyone else farms.
        for c in free_farmers:
            assignments[c] = "farm"

        for c in components:
            environment.assign_group(c, assignments.get(c, "farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assignments = {}
        warriors = [c for c in components if c.role == "Warrior"]

        # Farmers never fight: send them home.
        for c in components:
            if c.role == "Farmer":
                assignments[c] = "village"

        fed = [c for c in warriors if c.steps_since_meal < self.CAVE_RETURN]
        hungry = [c for c in warriors if c.steps_since_meal >= self.CAVE_RETURN]

        # Keep the Dragon attacked every step: if no fed warrior is here,
        # the least hungry warrior stays while it is still safe to do so.
        if not fed and hungry:
            best = min(hungry, key=lambda c: c.steps_since_meal)
            if best.steps_since_meal <= self.MAX_FALLBACK_HUNGER:
                hungry.remove(best)
                fed.append(best)

        for c in fed:
            assignments[c] = "attack"
        for c in hungry:
            assignments[c] = "village"

        for c in components:
            environment.assign_group(c, assignments.get(c, "cave"))
```