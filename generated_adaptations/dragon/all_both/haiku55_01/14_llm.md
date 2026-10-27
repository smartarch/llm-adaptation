## What was wrong

The remaining failures are all Dragon gaps. The last cave rule required a "fresh" warrior (hunger ≤ 2) to stay behind. That condition was often false when warriors were out of step, so warriors left when they shouldn't have, and the Dragon went unattacked for three or more steps.

A single warrior cannot avoid gaps entirely. A round trip (leave, eat in the Village, return) takes about three steps with no attack, so a second warrior must cover those steps. That is why the rule has to be "never leave unless another warrior stays in the Cave."

## Fix

**Cave phase**
- Warriors are decided from most hungry to least hungry.
- A warrior at hunger 3 leaves only if at least one other warrior remains in the Cave to attack. The count of remaining attackers is updated after each decision.
- A warrior at hunger 4 is forced out regardless. This keeps it below the 6-step starvation limit, and it is the one case where a gap cannot be avoided.
- If every warrior would leave, the least hungry one stays, as long as it is below the forced threshold.
- The "fresh warrior" requirement is removed, since it blocked legitimate departures.

**Village phase**
- Unchanged. Hungry villagers eat first, fed warriors return to the Cave immediately, and spawning uses only a wheat surplus.

I have not run the test suite, so this is a reasoned fix. The unit tests remain the reference.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Villagers with steps_since_meal >= HUNGER_THRESHOLD eat first (most hungry first),
        as long as wheat is available for the meal.
      - Hungry warriors that cannot be fed stay in the village (never sent to the cave).
      - Fed warriors go back to the cave to attack the dragon.
      - Free farmers spawn warriors, then farmers, only from a wheat surplus that also
        covers the next round of meals. Other farmers keep farming so wheat is produced.
    Cave:
      - Farmers go back to the village.
      - Warriors are decided from most hungry to least hungry. A warrior at
        LEAVE_THRESHOLD leaves for food only if another warrior stays in the cave
        to keep attacking. A warrior at FORCE_LEAVE_THRESHOLD leaves regardless,
        so it never starves.
    Every component is assigned exactly once per call.
    """

    HUNGER_THRESHOLD = 3        # village: eat when this many steps have passed without a meal
    LEAVE_THRESHOLD = 3         # cave: a warrior may leave for food at this hunger
    FORCE_LEAVE_THRESHOLD = 4   # cave: a warrior must leave for food at this hunger
    MIN_SPAWNS = 2              # at least this many of each role should be spawned
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    # ------------------------------------------------------------------ village
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = int(environment.farm.wheat)
        plan = {}  # id(component) -> group

        # 1) Hungry villagers eat first, most hungry first, limited by wheat
        budget = max(0, wheat)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.HUNGER_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if budget > 0:
                plan[id(c)] = "eat"
                budget -= 1
            else:
                # cannot be fed: never send a hungry warrior to the cave
                plan[id(c)] = "farm"
        wheat_after_meals = budget

        # 2) Fed villagers
        free_farmers = []
        for c in components:
            if id(c) in plan:
                continue
            if c.role == "Warrior":
                plan[id(c)] = "cave"        # fed warriors attack the dragon
            else:
                free_farmers.append(c)

        # 3) Spawning, only from a surplus that still covers the next round of meals
        reserve = len(components)           # about one meal per villager
        remaining = wheat_after_meals

        if (self.spawned_warriors < self.MIN_SPAWNS
                and len(free_farmers) >= 2
                and remaining - self.WARRIOR_COST >= reserve):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn warrior"
            free_farmers = free_farmers[2:]
            remaining -= self.WARRIOR_COST
            self.spawned_warriors += 1

        if (self.spawned_farmers < self.MIN_SPAWNS
                and len(free_farmers) >= 2
                and remaining - self.FARMER_COST >= reserve):
            for c in free_farmers[:2]:
                plan[id(c)] = "spawn farmer"
            free_farmers = free_farmers[2:]
            remaining -= self.FARMER_COST
            self.spawned_farmers += 1

        # Remaining farmers keep farming so wheat keeps coming in
        for c in free_farmers:
            plan[id(c)] = "farm"

        # 4) Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])

    # --------------------------------------------------------------------- cave
    def assign_in_cave(self, components, environment, group_ids, step: int):
        plan = {}
        warriors = []
        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                plan[id(c)] = "village"     # farmers must not stay in the cave

        # Most hungry warriors are decided first
        ordered = sorted(warriors, key=lambda c: c.steps_since_meal, reverse=True)
        remaining = len(warriors)
        leaving = set()

        for w in ordered:
            s = w.steps_since_meal
            if s >= self.FORCE_LEAVE_THRESHOLD:
                leaving.add(id(w))          # about to starve: must go eat
                remaining -= 1
            elif s >= self.LEAVE_THRESHOLD and remaining - 1 >= 1:
                # leave only if another warrior stays in the cave to attack
                leaving.add(id(w))
                remaining -= 1

        # Never leave the cave empty unless someone is forced to eat
        if warriors and remaining == 0:
            least = min(warriors, key=lambda c: c.steps_since_meal)
            if least.steps_since_meal < self.FORCE_LEAVE_THRESHOLD:
                leaving.discard(id(least))

        for w in warriors:
            plan[id(w)] = "village" if id(w) in leaving else "attack"

        # Apply exactly once per component
        for c in components:
            environment.assign_group(c, plan[id(c)])
```