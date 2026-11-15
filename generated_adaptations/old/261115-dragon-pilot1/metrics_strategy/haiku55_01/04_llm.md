## Revised strategy: Early warrior mass, sustained attacks, and hunger-safe rotation

**What went wrong before:** The previous version almost never built up enough warriors. It also sent warriors to the Cave with too little margin before they had to eat, and it spawned only after eating had consumed the wheat. With 3 damage per warrior attack and 5 HP regeneration per unattacked step, the Dragon needs about 34 warrior attacks. Each warrior can absorb only about 15 cave steps on average, since the Dragon's counterattack deals 1 damage to everyone in the Cave with 40% probability per attack. The old code never reached that level of force.

**New approach:**

1. **Bootstrap farmers, then mass warriors.** Farmers produce the wheat, so the first spawns are farmers until there are about 3. After that, the strategy spawns warriors whenever there are at least 12 wheat left after meals. The spawn pair is drawn from idle farmers first, and from non-raiding warriors only if needed.
2. **Eat first, with a budget.** Anyone at or past their hunger threshold eats before wheat is spent on spawning. Warriors eat at 2 steps and farmers at 3, which keeps everyone well below the 6-step starvation limit.
3. **Warriors raid immediately.** Fed warriors (hunger ≤ 1, HP ≥ 3) go to the Cave from the start, so attacks begin in the first steps and continue every step the Dragon is still alive.
4. **Hunger-safe rotation.** In the Cave, a warrior returns to the Village when its hunger reaches 3 or its HP drops to 2. Otherwise it keeps attacking. Returning early leaves margin for the one-step trip and the meal, and it keeps the Dragon attacked as long as at least one warrior remains in the Cave.
5. **Only attackers stay in the Cave.** Farmers never enter the Cave, so the Dragon's area attacks hit only warriors that are actually fighting.

Trade-off: this is still a heuristic. Its success depends on the starting population and the wheat income, and it does not guarantee a win within 30 steps. It is designed to maximize warrior-attacks per step and to avoid starvation and the Dragon's regeneration window.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Steps without a meal before a villager is sent to eat
    FARMER_EAT_AT = 3
    WARRIOR_EAT_AT = 2
    # A warrior in the Cave returns to the Village at this hunger level
    WARRIOR_RETURN_AT = 3
    # Warriors only raid when this fresh and at least this healthy
    WARRIOR_RAID_MAX_HUNGER = 1
    WARRIOR_MIN_HP = 3
    # Population goals
    TARGET_FARMERS_BOOT = 3
    TARGET_WARRIORS = 6
    TARGET_FARMERS_MAX = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Number of warriors currently in the Cave (from the last cave assignment)
        self.cave_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        budget = wheat
        handled = set()

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        total_farmers = len(farmers)
        total_warriors = len(warriors) + self.cave_warriors

        # 1. Eating has priority: most-hungry first, limited by wheat
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

        # 3. Spawning: needs a pair from the spawn group
        pool = [c for c in remaining if id(c) not in handled and c.role == "Farmer"]
        pool += [c for c in spare_warriors if c.role == "Warrior"]

        spawn_group = None
        if len(pool) >= 2:
            if total_farmers < self.TARGET_FARMERS_BOOT and budget >= 10:
                spawn_group = "spawn farmer"
                cost = 10
            elif total_warriors < self.TARGET_WARRIORS and budget >= 12:
                spawn_group = "spawn warrior"
                cost = 12
            elif total_farmers < self.TARGET_FARMERS_MAX and budget >= 10:
                spawn_group = "spawn farmer"
                cost = 10

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
        attackers = 0
        for c in components:
            if c.role == "Warrior":
                # Go home to eat before starving, or when badly wounded
                if c.steps_since_meal >= self.WARRIOR_RETURN_AT or c.hp <= 2:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
                    attackers += 1
            else:
                # Farmers never fight and would only take area damage
                environment.assign_group(c, "village")
        self.cave_warriors = sum(1 for c in components if c.role == "Warrior")
```