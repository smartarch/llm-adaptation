## Revised strategy: Faster warrior build-up and a larger attack force

**What the last result tells us:** The strategy now wins every game, but it averages 20.7 steps. The Dragon has 100 HP and regenerates 5 HP per unattacked step, so the win time is set mostly by how much damage the warriors deal per step. At 3 damage per warrior attack, about 34 attacks are needed. Two things slow this down:
- The warrior count builds slowly, because 3 farmers are spawned before any warrior, and the warrior target of 6 is reached late.
- Early steps have only 1 to 2 attackers, so the Dragon takes little damage while the army is still small.

**Changes:**

1. **Earlier warriors.** The farmer boot target drops from 3 to 2. Once two farmers exist, warrior spawns take priority over further farmers. Warriors are produced as soon as 12 wheat is available after meals.
2. **Larger army.** The warrior target rises from 6 to 8, so more warriors attack in parallel. Each attacker adds 3 damage per step, which shortens the fight.
3. **Farmers remain the spawn pair when possible.** This keeps the warriors fighting, and farmers are the cheapest to lose from the wheat economy.
4. **Warriors in the Cave count correctly.** The population count now includes every warrior that stayed in the Cave, so spawn decisions reflect the actual army.
5. **Safety rules kept.** Warriors still eat at hunger 2, leave the Cave at hunger 4, and the Dragon is never left unattacked. These rules produced the 100% win rate, so they stay unchanged.

Trade-off: a larger army eats more wheat, so the farm may run short when meals are due. The meal priority in the Village still protects against starvation. This remains a heuristic, and the improvement in speed is not guaranteed.

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
    # Population goals (larger army, earlier warriors)
    TARGET_FARMERS_BOOT = 2
    TARGET_WARRIORS = 8
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
            # Warriors first once the farmer base exists, since they drive the damage
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