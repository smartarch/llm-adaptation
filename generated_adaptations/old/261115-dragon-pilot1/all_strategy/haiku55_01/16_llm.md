## Fixes

The remaining failure is the Dragon gap at steps 6-7. Warriors leaving the Cave at the same time left it empty. The fix is to limit how many warriors are away at once:

1. **One warrior away at a time.** A warrior leaves the Cave for food only when no other warrior is in the Village and at least one other fed warrior is still attacking. With four warriors, three keep the Dragon under attack while one is away.
2. **Forced departure for starvation.** A warrior at hunger 4 or more must leave even if the rule above would block it. Starvation at 6 is a loss condition, so it takes priority over the Dragon-gap rule.
3. **Fast turnaround in the Village.** Warriors eat as soon as they arrive (hunger 1 or more), and fed warriors go straight back to the Cave.
4. **Spawning is unchanged in intent.** Only free farmers are used, and spawning waits whenever a villager needs a meal.

I could not run the simulator here, so these thresholds are a reasoned guess, not a verified schedule. If the Dragon-gap check still fails, the next lever is the forced-departure threshold or the warrior target.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Cave (attack) and the Village (eat).
    At most one warrior is away from the Cave at a time, so the Dragon
    keeps being attacked, and a warrior is forced to eat before it starves.
    """

    WARRIOR_VILLAGE_EAT = 1      # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2               # farmers eat early to keep a safety margin
    CAVE_LEAVE = 2               # warriors at/above this hunger may leave for food...
    FORCE_LEAVE = 4              # ...and must leave at this hunger, regardless of the Dragon
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

        # Warriors that are hungry enough to need a meal, most hungry first.
        hungry = sorted(
            [c for c in warriors if c.steps_since_meal >= self.CAVE_LEAVE],
            key=lambda c: -c.steps_since_meal,
        )
        fed = [c for c in warriors if c.steps_since_meal < self.CAVE_LEAVE]

        # Warriors already away in the Village (not visible here), so we
        # only allow one departure per step and only if others keep attacking.
        leaving = []
        for c in hungry:
            if c.steps_since_meal >= self.FORCE_LEAVE:
                leaving.append(c)  # starvation is a loss: must go
            elif not leaving and len(fed) >= 1:
                leaving.append(c)  # one warrior away at a time, others keep attacking

        # If nobody is attacking at all, keep the least hungry warrior fighting.
        if not fed and not leaving and hungry:
            leaving = [] 
            fed.append(min(hungry, key=lambda c: c.steps_since_meal))

        for c in leaving:
            assignments[c] = "village"
        for c in fed:
            assignments[c] = "attack"
        for c in hungry:
            if c not in assignments:
                assignments[c] = "attack"

        for c in components:
            environment.assign_group(c, assignments.get(c, "cave"))
```