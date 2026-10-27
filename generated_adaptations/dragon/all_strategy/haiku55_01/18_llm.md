## Fixes

The Dragon was left unattacked at steps 6-7 in three seeds. The cave logic had two gaps:

1. **Empty cave after a forced departure.** When the only remaining warrior was forced to leave at hunger 4, nobody attacked. The least hungry departing warrior now stays and attacks instead.
2. **Overlapping departures across steps.** The "one at a time" rule only applied within a single step, so a second warrior could leave while the first was still away. A non-forced departure now waits 3 steps after the previous one, which covers the round trip (leave, eat, return).

Forced departures at hunger 4 still go ahead, since starvation is a loss condition. The village logic is unchanged.

I could not run the simulator, so the spacing and thresholds are a reasoned estimate. If the Dragon-gap check still fails, adjust `DEPARTURE_SPACING` or `CAVE_LEAVE`.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, spawn).
    Warriors rotate between the Cave (attack) and the Village (eat).
    Non-urgent departures are spaced out so that the Dragon keeps being
    attacked, and a warrior is forced to eat before it starves.
    """

    WARRIOR_VILLAGE_EAT = 1      # warriors eat as soon as they are hungry in the Village
    FARMER_EAT = 2               # farmers eat early to keep a safety margin
    CAVE_LEAVE = 2               # warriors at/above this hunger may leave for food...
    FORCE_LEAVE = 4              # ...and must leave at this hunger, regardless of the Dragon
    DEPARTURE_SPACING = 3        # steps between non-forced departures (round trip length)
    TARGET_FARMERS = 4
    TARGET_WARRIORS = 4
    FARMER_SPAWN_COST = 10
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_departure_step = None

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

        hungry = sorted(
            [c for c in warriors if c.steps_since_meal >= self.CAVE_LEAVE],
            key=lambda c: -c.steps_since_meal,
        )
        fed = [c for c in warriors if c.steps_since_meal < self.CAVE_LEAVE]

        # Decide who leaves for food.
        spacing_ok = (
            self._last_departure_step is None
            or step - self._last_departure_step >= self.DEPARTURE_SPACING
        )
        leaving = []
        for c in hungry:
            if c.steps_since_meal >= self.FORCE_LEAVE:
                leaving.append(c)  # starvation is a loss: must go now
            elif spacing_ok and not leaving and len(fed) >= 1:
                leaving.append(c)  # one non-urgent departure at a time, others keep attacking
                spacing_ok = False

        attackers = fed + [c for c in hungry if c not in leaving]

        # Never leave the cave empty: the least hungry departing warrior stays.
        if not attackers and leaving:
            keep = min(leaving, key=lambda c: c.steps_since_meal)
            leaving.remove(keep)
            attackers.append(keep)

        if any(c.steps_since_meal >= self.CAVE_LEAVE and c in leaving for c in warriors):
            self._last_departure_step = step

        for c in leaving:
            assignments[c] = "village"
        for c in attackers:
            assignments[c] = "attack"

        for c in components:
            environment.assign_group(c, assignments.get(c, "cave"))
```