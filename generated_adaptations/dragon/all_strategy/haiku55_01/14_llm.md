## Fixes

The last run had two failures:

1. **Richard starved at step 6 (most seeds).** Warriors left the Cave at hunger 3, so the trip home took too long to finish before the 6-step limit. Warriors now leave at hunger 2 whenever at least one other fed warrior is still attacking. Otherwise they stay in the Cave only while their hunger is at most 3.
2. **Dragon gap at step 6-7 (seed=3).** Making warriors leave earlier risks an empty Cave. To prevent that, the departure rule only applies when another fed warrior is still attacking. If no other warrior is left, the least hungry warrior keeps attacking. This keeps the Dragon attacked, but the lone warrior is capped at hunger 3 so it still has time to eat.

Spawning and farming are unchanged. Spawning still waits whenever a villager needs a meal, so the meal budget is never spent on spawning.

I could not run the simulator here, so these thresholds are a reasoned guess. If the test still fails, the next levers are the warrior target (`TARGET_WARRIORS`) and the lone-warrior cap (`MAX_FALLBACK_HUNGER`).

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Cave (attack) and the Village (eat).
    A warrior leaves the Cave early (hunger 2) only while another fed
    warrior keeps attacking, so the Dragon is not left unattacked.
    """

    WARRIOR_VILLAGE_EAT = 1      # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2               # farmers eat early to keep a safety margin
    CAVE_RETURN = 2              # warriors at/above this hunger leave the Cave...
    MAX_FALLBACK_HUNGER = 3      # ...but a lone warrior keeps attacking up to this hunger
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

        # 3. Fed, free warriors head back to the Cave.
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
        # hungry warrior stays while it is still safe to do so.
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