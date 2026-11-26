## Diagnosis

The last run won 0% of games, and the at-the-end tests fail because the Dragon was never killed. The previous strategy was too passive. Warriors only attacked for about 2 steps per cycle, and the Dragon regenerated 5 HP on every step with no attack. Spawning was also rare, so the damage output stayed too low to finish 100 HP within 30 steps.

## Revised strategy: sustained pressure

1. **Keep the Dragon under constant attack.** The Dragon only regenerates on steps with no attacks, so the goal is at least one attacker in the Cave every step. Warriors are dispatched from the Village until the Cave holds a target number of attackers (`TARGET_ATTACKERS = 4`). Attackers are counted with `environment.warriors`, using `location == "Cave"`.
2. **Longer attack stints.** A warrior attacks while `steps_since_meal <= 3` and returns when hunger reaches 4. It is therefore still below the 6-step starvation limit on arrival, and it eats in the same step it arrives.
3. **Aggressive warrior spawning.** Warriors are spawned early (before step 18) whenever the wheat left after this step's meals covers the 12-wheat cost plus a small reserve. At least one farmer always stays on the farm, so wheat production continues.
4. **Budgeted eating.** Hungry villagers eat in order of hunger, limited by the wheat stock, which avoids the "not enough wheat for a meal" error from before.
5. **Complete assignment.** Every component is assigned exactly once in each method.

The Dragon's counterattack can still kill villagers, so the strategy rotates warriors in and out of the Cave rather than keeping any one of them there for long.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: villagers at or above this hunger are sent to eat
    EAT_THRESHOLD = 2
    # Cave: warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Keep this many attackers in the cave every step (avoids Dragon regeneration)
    TARGET_ATTACKERS = 4
    # Warriors may be dispatched only when this fed and healthy
    DISPATCH_MAX_HUNGER = 1
    WARRIOR_MIN_HP = 3
    # Cave retreat thresholds
    WARRIOR_RETREAT_HP = 1
    FARMER_RETREAT_HP = 2
    # Wheat kept back for next step's meals
    WHEAT_RESERVE = 2
    WARRIOR_SPAWN_COST = 12
    # Spawning is worthwhile only early enough for new warriors to attack
    SPAWN_STEP_LIMIT = 18
    # Always keep at least this many farmers working the farm
    MIN_FARMERS_ON_FARM = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # 1) Feed the most hungry villagers first, limited by available wheat
        needy = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        eaters = needy[:wheat]
        eater_ids = set(id(c) for c in eaters)
        remaining_wheat = wheat - len(eaters)

        rest = [c for c in components if id(c) not in eater_ids]

        # 2) Dispatch fed, healthy warriors until the cave has enough attackers
        cave_attackers = sum(
            1 for w in environment.warriors
            if w.location == "Cave" and w.hp > 0 and w.steps_since_meal < self.CAVE_RETURN_THRESHOLD
        )
        needed = max(self.TARGET_ATTACKERS - cave_attackers, 0)

        candidates = [
            c for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        ]
        # Prefer the healthiest warriors for the cave
        candidates.sort(key=lambda c: -c.hp)
        cave_ids = set(id(c) for c in candidates[:needed])

        # 3) Spawn warriors from idle farmers, keeping some farmers on the farm
        idle_farmers = [c for c in rest if c.role == "Farmer"]
        spawn_ids = set()
        spare_farmers = len(idle_farmers) - self.MIN_FARMERS_ON_FARM
        if (
            step < self.SPAWN_STEP_LIMIT
            and spare_farmers >= 2
            and remaining_wheat >= self.WARRIOR_SPAWN_COST + self.WHEAT_RESERVE
        ):
            for c in idle_farmers[:2]:
                spawn_ids.add(id(c))

        # 4) Assign every component exactly once
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in cave_ids:
                environment.assign_group(c, "cave")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hungry = c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD
            if c.role == "Warrior":
                weak = c.hp <= self.WARRIOR_RETREAT_HP
            else:
                weak = c.hp <= self.FARMER_RETREAT_HP

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```