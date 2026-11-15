## Fixes

The remaining failure is the Dragon gap: the Cave is sometimes empty for three steps in a row. A warrior's round trip (leave the Cave, travel, eat, travel back) takes about three steps, so a single warrior that leaves while no other is attacking creates a gap. The changes are:

1. **Two-deep rotation.** A warrior leaves the Cave only when at least one other fed warrior is still attacking. Its departure threshold is raised to hunger 3, so it spends more time fighting per trip.
2. **Lone-warrior fallback.** If one warrior is left in the Cave, it keeps attacking up to hunger 4. Its trip home starts there, which still leaves a short margin before the 6-step starvation limit.
3. **Fast return from the Village.** Warriors eat as soon as they arrive (hunger 1 or more), and fed warriors return to the Cave at once.
4. **More warriors.** Warrior spawning is kept at a target of 4 so there are enough warriors to rotate.

I could not run the simulator, so these thresholds are a reasoned guess. If the Dragon-gap check still fails, the next step is to lower the Cave departure threshold or to raise the warrior target.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Cave (attack) and the Village (eat).
    A warrior leaves the Cave only while another fed warrior is still
    attacking, so the Dragon is never left unattacked for long.
    """

    WARRIOR_VILLAGE_EAT = 1     # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2              # farmers eat early to keep a safety margin
    CAVE_RETURN = 3             # warriors at/above this hunger leave the Cave...
    MAX_FALLBACK_HUNGER = 4     # ...but a lone warrior keeps attacking up to this hunger
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

        # Keep the Dragon attacked every step.
        if not fed and hungry:
            # No fed warrior here: the least hungry one stays while it is still safe.
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