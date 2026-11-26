## Strategy: Warrior Strike Force with Rotating Meals

**Goal:** Kill the Dragon (100 HP) within 30 steps while keeping every villager fed at least once every 6 steps.

**Key observations:**
- Only warriors deal meaningful damage (3 per step vs. 1 for farmers), so warriors are the attackers.
- Farmers produce 5 wheat per step, which pays for meals and spawning, so they stay in the Village on the farm.
- The Dragon regenerates 5 HP per step once it has been hit, so attacks should be almost continuous. Every warrior in the Cave should attack on every step it is able to.
- Starvation is the main constraint. A villager that has not eaten for a few steps must go back to the Village. I use a hunger threshold of 3 steps, which leaves a margin before the 6-step limit even with the round-trip travel.

**Village logic (`assign_in_village`):**
1. Any villager with `steps_since_meal >= 3` goes to the "eat" group.
2. If wheat is sufficient (at least 12 after reserving for meals), there are fewer than 6 warriors total, and at least two healthy farmers are available, two such farmers go to "spawn warrior". This adds attack power. The spawn is only triggered when the farmers are not hungry.
3. Remaining fed warriors go to the "cave" group to attack while the Dragon is alive.
4. All remaining farmers go to the "farm" group to produce wheat.

**Cave logic (`assign_in_cave`):**
1. Warriors with `steps_since_meal < 3` go to "attack".
2. Warriors with `steps_since_meal >= 3` go to "village" to eat before they starve.
3. Farmers in the Cave (not normally present) return to the "village" group so they do not take damage from the Dragon's counterattacks.

Because each warrior returns to eat before reaching the hunger limit, the attacking force rotates. The number of warriors in the Cave determines the damage per step, and the spawn logic increases that number when wheat allows.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Warriors are the damage dealers (3 dmg/step); farmers produce wheat
      (5/step) that pays for meals and spawning.
    - Any villager that has not eaten for HUNGER_LIMIT steps is sent to eat
      in the Village, well before the 6-step starvation limit.
    - Fed warriors keep attacking in the Cave; farmers stay on the farm.
    - Extra warriors are spawned from pairs of healthy farmers while wheat
      is available and the warrior count is below MAX_WARRIORS.
    """

    HUNGER_LIMIT = 3       # go eat when steps_since_meal reaches this value
    MAX_WARRIORS = 6       # stop spawning warriors beyond this count
    WARRIOR_COST = 12      # wheat cost of spawning a warrior
    WHEAT_RESERVE = 2      # wheat kept aside for meals

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        hungry = [c for c in comps if c.steps_since_meal >= self.HUNGER_LIMIT]
        fed = [c for c in comps if c.steps_since_meal < self.HUNGER_LIMIT]

        # 1. Hungry villagers eat (each meal costs 1 wheat).
        for c in hungry:
            environment.assign_group(c, "eat")
        wheat_after_meals = wheat - len(hungry)

        # 2. Possibly spawn a new warrior from two fed farmers.
        spawn_candidates = [c for c in fed if c.role == "Farmer"]
        spawned = set()
        num_warriors = len(environment.warriors)
        if (dragon_alive
                and num_warriors < self.MAX_WARRIORS
                and wheat_after_meals - self.WHEAT_RESERVE >= self.WARRIOR_COST
                and len(spawn_candidates) >= 2):
            for c in spawn_candidates[:2]:
                environment.assign_group(c, "spawn warrior")
                spawned.add(id(c))

        # 3. Remaining fed villagers.
        for c in fed:
            if id(c) in spawned:
                continue
            if c.role == "Warrior" and dragon_alive:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.HUNGER_LIMIT:
                # Healthy warriors keep hitting the Dragon every step.
                environment.assign_group(c, "attack")
            else:
                # Hungry warriors and farmers return to eat/farm.
                environment.assign_group(c, "village")
```