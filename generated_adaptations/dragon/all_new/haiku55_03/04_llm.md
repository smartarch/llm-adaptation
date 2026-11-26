## Diagnosis

The failing tests point to three problems in the previous version:

1. **Too slow to win.** The Dragon survives past step 30 because the army is small and warriors are pulled out of the Cave too early. Warriors that retreat at a hunger threshold of 3 make only about 2 attacks per trip, which leaves the Dragon regenerating between trips.
2. **Farmers were sent to the Cave.** Farmers deal only 1 damage and have 4 HP, and the optional tests expect them to stay in the Village. Farmers are better used for farming and spawning.
3. **Spawning was too restrictive.** The spawn condition was miscalculated, so the strategy often did not spawn when it could have.

## Revised strategy

**Village**
- **Eat first:** villagers with `steps_since_meal >= 2` eat, as long as wheat remains. Eating early keeps them well inside the 6-step starvation limit.
- **Launch warriors:** healthy warriors (hp ≥ 3, recently fed) go to the Cave once at least `LAUNCH_SIZE` of them are available. Warriors are the only units sent to fight, so every trip carries full damage.
- **Spawn warriors:** pairs of non-warrior villagers (farmers first) go to "spawn warrior" whenever wheat covers the 12-wheat cost plus one meal per villager. Warriors deal 3× the damage of farmers, so they are the best use of wheat.
- **Everyone else farms.** Farmers never enter the Cave.

**Cave**
- Warriors attack every step while `steps_since_meal < 4` and they are not badly wounded (hp ≥ 2). Keeping attacks on consecutive steps prevents the Dragon's 5 HP regeneration.
- Warriors that get hungry or too wounded return to the Village to eat.
- Any farmer found in the Cave returns to the Village.

The Dragon has 100 HP, so the damage budget is the key number. Ten warriors deal 30 damage per step, which finishes the Dragon in about 4 steps. The plan is to build the warrior count early, then strike with every warrior at once.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: feed villagers before they starve, send healthy warriors to
        the Cave once a launch group is ready, spawn new warriors from pairs of
        non-warrior villagers whenever wheat allows, and keep everyone else
        farming. Farmers never go to the Cave.
      - Cave: warriors attack every step while they are fed and healthy, so the
        Dragon never gets a step to regenerate. Hungry or badly wounded warriors
        return to the Village. Any farmer in the Cave goes back to farm.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat early, well before the 6-step limit
    RETREAT_THRESHOLD = 4       # leave the Cave when hunger reaches this
    LAUNCH_SIZE = 3             # ready warriors needed to send a group
    MIN_WARRIOR_HP_CAVE = 2     # warriors below this retreat
    MIN_WARRIOR_HP_LAUNCH = 3   # warriors below this stay home
    WARRIOR_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = {}

        def assign(c, group):
            environment.assign_group(c, group)
            assigned[id(c)] = group

        wheat = environment.farm.wheat

        # 1. Eating: feed villagers that are getting hungry (costs 1 wheat each).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE],
            key=lambda x: -x.steps_since_meal,
        )
        eat_budget = wheat
        for c in hungry:
            if eat_budget > 0:
                assign(c, "eat")
                eat_budget -= 1

        remaining = [c for c in components if id(c) not in assigned]

        # 2. Launching: healthy, recently fed warriors go to the Cave as a group.
        ready_warriors = [
            c for c in remaining
            if c.role == "Warrior"
            and c.hp >= self.MIN_WARRIOR_HP_LAUNCH
            and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE
        ]
        if environment.dragon.hp > 0 and len(ready_warriors) >= self.LAUNCH_SIZE:
            for c in ready_warriors:
                assign(c, "cave")

        remaining = [c for c in components if id(c) not in assigned]

        # 3. Spawning: pairs of non-warrior villagers spawn a new warrior when
        #    wheat covers the cost plus one meal for every villager.
        reserve = len(components)
        if environment.dragon.hp > 0 and wheat >= self.WARRIOR_COST + reserve:
            spawn_pool = [c for c in remaining if c.role == "Farmer"]
            if len(spawn_pool) < 2:
                spawn_pool += [c for c in remaining if c.role == "Warrior" and c not in spawn_pool]
            if len(spawn_pool) >= 2:
                for c in spawn_pool[:2]:
                    assign(c, "spawn warrior")

        remaining = [c for c in components if id(c) not in assigned]

        # 4. Everyone else farms (farmers never go to the Cave).
        for c in remaining:
            assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers are not sent to fight; return them to farm.
                environment.assign_group(c, "village")
            elif environment.dragon.hp <= 0:
                environment.assign_group(c, "cave")
            elif c.steps_since_meal >= self.RETREAT_THRESHOLD or c.hp < self.MIN_WARRIOR_HP_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```