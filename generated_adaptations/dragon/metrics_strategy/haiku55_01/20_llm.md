## Revised strategy: Warrior-priority ramp to 4 before the second farmer

**What the last result tells us:** Letting farmers eat at hunger 5 saved wheat and cut the average win time from 20.3 to 19.7 steps, with the win rate still at 100%. Keeping farmer meals less frequent is the first change in several rounds that moved the result, so I'll keep it.

**The change:** The early-ramp threshold rises from 3 to 4. While the army has fewer than 4 warriors, a warrior spawn takes priority over the second base farmer. This puts more attackers in the Cave during steps 5 to 12, when the Dragon still has most of its HP.

**Unchanged:**
- Farmers eat at hunger 5, which produced the gain.
- Warriors eat at hunger 2, leave the Cave at hunger 4, and the Dragon is never left unattacked.
- The finishing override, population targets (8 warriors, 4 farmers max), and spawn pair preference stay the same.

**Trade-off:** Delaying the second base farmer reduces early wheat income. The meal rules still protect against starvation, but if wheat runs short, meals could be delayed. The effect on speed is an experiment, not a proven gain.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Steps without a meal before a villager is sent to eat.
    # Farmers wait until hunger 5 (starvation starts at 6), saving wheat.
    FARMER_EAT_AT = 5
    WARRIOR_EAT_AT = 2
    # A warrior in the Cave returns to the Village at this hunger level
    WARRIOR_RETURN_AT = 4
    # Hard limit: a warrior must not be in the Cave at this hunger
    WARRIOR_MAX_HUNGER_IN_CAVE = 4
    # Hunger at which a warrior would starve (6 consecutive missed meals)
    WARRIOR_STARVE_AT = 6
    # Warriors only raid when this fresh and at least this healthy
    WARRIOR_RAID_MAX_HUNGER = 1
    WARRIOR_MIN_HP = 3
    WARRIOR_MIN_HP_CAVE = 2
    WARRIOR_DAMAGE = 3
    # Population goals
    TARGET_FARMERS_BOOT = 2
    TARGET_WARRIORS = 8
    TARGET_FARMERS_MAX = 4
    # Early ramp: prefer warriors over the second base farmer while the army is small
    EARLY_WARRIOR_BELOW = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Number of warriors that stayed in the Cave at the last cave step
        self.cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        budget = wheat
        handled = set()

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        total_farmers = len(farmers)
        total_warriors = len(warriors) + self.cave_warriors

        # 1. Eating: most hungry first, limited by wheat
        needs_food = []
        for c in components:
            threshold = self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT
            if c.steps_since_meal >= threshold:
                needs_food.append(c)
        for c in sorted(needs_food, key=lambda x: -x.steps_since_meal):
            if budget >= 1:
                environment.assign_group(c, "eat")
                budget -= 1
                handled.add(id(c))

        remaining = [c for c in components if id(c) not in handled]

        # 2. Fed, healthy warriors raid the Cave
        spare_warriors = []
        for c in remaining:
            if c.role == "Warrior":
                if c.steps_since_meal <= self.WARRIOR_RAID_MAX_HUNGER and c.hp >= self.WARRIOR_MIN_HP:
                    environment.assign_group(c, "cave")
                    handled.add(id(c))
                else:
                    spare_warriors.append(c)

        # 3. Spawning: needs a pair in the spawn group
        pool = [c for c in remaining if id(c) not in handled and c.role == "Farmer"]
        pool += [c for c in spare_warriors if c.role == "Warrior"]

        spawn_group = None
        cost = 0
        if len(pool) >= 2:
            if total_farmers < 1 and budget >= 10:
                spawn_group, cost = "spawn farmer", 10
            elif total_warriors < self.EARLY_WARRIOR_BELOW and budget >= 12:
                spawn_group, cost = "spawn warrior", 12
            elif total_farmers < self.TARGET_FARMERS_BOOT and budget >= 10:
                spawn_group, cost = "spawn farmer", 10
            elif total_warriors < self.TARGET_WARRIORS and budget >= 12:
                spawn_group, cost = "spawn warrior", 12
            elif total_farmers < self.TARGET_FARMERS_MAX and budget >= 10:
                spawn_group, cost = "spawn farmer", 10

        if spawn_group is not None:
            # Prefer farmers as the spawning pair so warriors keep fighting
            pool.sort(key=lambda c: 0 if c.role == "Farmer" else 1)
            for c in pool[:2]:
                environment.assign_group(c, spawn_group)
                handled.add(id(c))
            budget -= cost

        # 4. Everyone else stays in the Village and farms
        for c in components:
            if id(c) not in handled:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        stay, leave = [], []
        for c in components:
            if c.role != "Warrior":
                # Farmers never fight and would only take area damage
                environment.assign_group(c, "village")
                continue
            if c.steps_since_meal >= self.WARRIOR_RETURN_AT or c.hp < self.WARRIOR_MIN_HP_CAVE:
                leave.append(c)
            else:
                stay.append(c)

        # Finishing-blow override: if the warriors that can still deal damage
        # this step are enough to kill the Dragon, keep them all attacking.
        finishers = [
            c for c in components
            if c.role == "Warrior"
            and c.steps_since_meal < self.WARRIOR_STARVE_AT - 1
            and c.hp >= self.WARRIOR_MIN_HP_CAVE
        ]
        if finishers and environment.dragon.hp <= self.WARRIOR_DAMAGE * len(finishers):
            stay = finishers
            leave = [c for c in leave if c not in finishers]

        # Never leave the Dragon unattacked: keep the least hungry warrior
        # if everyone would otherwise leave this step
        if not stay and leave:
            leave.sort(key=lambda c: c.steps_since_meal)
            best = leave[0]
            if best.steps_since_meal < self.WARRIOR_MAX_HUNGER_IN_CAVE:
                leave.pop(0)
                stay.append(best)

        for c in stay:
            environment.assign_group(c, "attack")
        for c in leave:
            environment.assign_group(c, "village")

        self.cave_warriors = len(stay)
```