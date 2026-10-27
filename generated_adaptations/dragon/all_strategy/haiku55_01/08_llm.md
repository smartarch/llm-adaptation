## Fixes

The failures are starvation (Mark, Jason) and one Dragon gap (seed=3). The likely causes are:

1. **Starvation with no wheat.** A hungry villager that could not eat because wheat was 0 was still sent to the Cave (Jason). Villagers that need a meal now stay in the Village, and the Cave is only for fed warriors.
2. **Eat threshold too late for farmers.** Farmers ate at hunger 3, so a single step without wheat pushed them to 5. Farmers now eat at hunger 2.
3. **Warriors waited too long in the Cave.** The fallback let a lone warrior keep fighting up to hunger 4, which left no margin for the trip home. Warriors now leave at hunger 2, and the fallback only keeps a warrior at hunger 2 or less.
4. **Spawning is held back when someone is hungry.** Spawning is skipped on any step where a villager needs a meal and the wheat is not enough to cover it, so the meal budget is never spent on spawning.

I haven't run the simulator, so these thresholds are a heuristic. Warriors are still spawned up to 3 and farmers up to 4.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Village (eat) and the Cave (attack),
    leaving the Cave at a low hunger level so they never starve.
    """

    WARRIOR_VILLAGE_EAT = 1    # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2             # farmers eat early to keep a safety margin
    CAVE_RETURN = 2            # warriors at/above this hunger leave the Cave
    MAX_FALLBACK_HUNGER = 2    # a lone warrior keeps attacking only while this fresh
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 3
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

        # Anyone who needs food but cannot get it stays in the Village.
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

        # 3. Fed, free warriors head to the Cave.
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

        # Keep the Dragon attacked: if no fed warrior is here, the least
        # hungry warrior stays only while it is still safe to do so.
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