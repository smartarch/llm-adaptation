## Diagnosis

The remaining failures have two causes:

1. **The Dragon is not killed within 30 steps.** The "must be killed" test fails, so damage arrives too slowly. Warriors spend too many steps in the Village, and the attack pauses whenever they rotate out.
2. **Warriors are kept out of the fight too long.** A warrior that returns to the Village waits for its hunger counter to reset before it is sent back. The previous rule (`steps_since_meal < 2` for launch) left gaps in the attack, so the Dragon regenerated.
3. **Some spawn and retreat timings are off by one step.** This causes the minor optional-test failures.

## Revised strategy

**Village**
- **Eat first:** any villager with `steps_since_meal >= 2` eats, most hungry first, while wheat lasts. This keeps everyone well inside the 6-step starvation limit.
- **Keep a meal reserve:** one wheat per villager stays in reserve for next step's meals. Spare wheat is the only budget for spawning.
- **Spawn warriors:** pairs of idle farmers become a new warrior whenever the spare wheat covers 12 wheat.
- **Launch warriors continuously:** every warrior that is healthy (hp ≥ 3) and has `steps_since_meal <= 1` goes to the Cave. Warriors that just ate are sent out right away, so the Cave always has attackers.
- **Farm:** everyone else farms, which produces the wheat for meals and spawning.

**Cave**
- Warriors attack every step while `steps_since_meal < 3` and `hp >= 2`.
- Warriors with `steps_since_meal >= 3` or low HP return to the Village. Returning at 3 leaves room to eat before the 6-step limit.
- Farmers never fight, so any farmer in the Cave returns to farming.

Rotating warriors in and out this way keeps at least one attacker in the Cave on almost every step, so the Dragon's regeneration rarely applies.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers with steps_since_meal >= 2 while keeping one
        wheat per villager in reserve for next step's meals. Spare wheat spawns
        new warriors from pairs of idle farmers. Healthy warriors that have
        just eaten (steps_since_meal <= 1) are sent to the Cave immediately, so
        attacks are nearly continuous. Everyone else farms.
      - Cave: warriors attack every step while fed and healthy. Warriors that
        get hungry (steps_since_meal >= 3) or badly wounded return to eat.
        Farmers never fight and go back to farming.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat early, well before the 6-step limit
    RETREAT_THRESHOLD = 3       # leave the Cave in time to eat
    MIN_WARRIOR_HP_LAUNCH = 3   # warriors below this stay home
    MIN_WARRIOR_HP_CAVE = 2     # warriors below this retreat from the Cave
    FRESH_STEPS = 1             # warriors this fresh are sent to attack
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0

        # 1. Eating: feed hungry villagers, most hungry first.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1
        wheat_after_meals = eat_budget

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Reserve one wheat per villager for next step's meals.
        spare = wheat_after_meals - len(components)

        # 3. Spawning: pairs of idle farmers become a new warrior.
        farmers_idle = [c for c in remaining if c.role == "Farmer"]
        if dragon_alive:
            while len(farmers_idle) >= 2 and spare >= self.WARRIOR_COST:
                assign(farmers_idle.pop(0), "spawn warrior")
                assign(farmers_idle.pop(0), "spawn warrior")
                spare -= self.WARRIOR_COST

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Launch: healthy warriors that are fresh go to the Cave.
        if dragon_alive:
            for c in remaining:
                if (c.role == "Warrior"
                        and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
                        and c.steps_since_meal <= self.FRESH_STEPS):
                    assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 5. Everyone else farms.
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if c.role == "Farmer":
                # Farmers do not fight; send them back to farm.
                environment.assign_group(c, "village")
            elif not dragon_alive:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal >= self.RETREAT_THRESHOLD or c.hp < self.MIN_WARRIOR_HP_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```