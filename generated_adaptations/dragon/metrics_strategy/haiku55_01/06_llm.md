## Revised strategy: Longer warrior shifts and no unattacked gaps

**What the last result tells us:** A 67% win rate in about 25 steps means the Dragon usually dies, but slowly and not always in time. The main limits are:
- Warriors leave the Cave after only 3 hungry steps, so each warrior attacks in short bursts with long trips between them.
- If every warrior leaves in the same step, the Dragon goes unattacked and regenerates 5 HP.
- Warriors with HP ≤ 2 are never replaced, and nothing heals them.

**Changes:**

1. **Longer shifts.** A warrior stays in the Cave until its hunger reaches 4 instead of 3. Its trip to the Village (one step) brings it to hunger 5, and it eats on arrival, so the 6-step starvation limit is still respected. This gives each warrior more attack steps per cycle.
2. **Never leave the Dragon unattacked.** If the rule would send every warrior home in the same step, the least-hungry warrior that still has HP and food margin stays to attack. This keeps the Dragon from regenerating.
3. **Staggered departures.** Warriors that are about to starve leave first. Warriors that are still fed stay, so departures are spread out over time.
4. **Earlier warrior production.** Farmers boot the economy first (3 farmers), then the strategy builds warriors up to 6. Spawn pairs still come from farmers first to keep the attack force intact.
5. **Trade-off:** Longer shifts raise the risk of a starved warrior and of the Dragon's area damage, so the 4-step limit is a balance. The strategy remains a heuristic and does not guarantee a win within 30 steps.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Steps without a meal before a villager is sent to eat
    FARMER_EAT_AT = 3
    WARRIOR_EAT_AT = 2
    # A warrior in the Cave returns to the Village at this hunger level
    WARRIOR_RETURN_AT = 4
    # Hard limit: a warrior must not be in the Cave at this hunger
    WARRIOR_MAX_HUNGER_IN_CAVE = 4
    # Warriors only raid when this fresh and at least this healthy
    WARRIOR_RAID_MAX_HUNGER = 1
    WARRIOR_MIN_HP = 3
    WARRIOR_MIN_HP_CAVE = 2
    # Population goals
    TARGET_FARMERS_BOOT = 3
    TARGET_WARRIORS = 6
    TARGET_FARMERS_MAX = 4

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

        # 1. Eating has priority: most hungry first, limited by wheat
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
            if total_farmers < self.TARGET_FARMERS_BOOT and budget >= 10:
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