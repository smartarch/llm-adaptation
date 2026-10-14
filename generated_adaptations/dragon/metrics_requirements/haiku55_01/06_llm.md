## Diagnosis

The strategy still wins 0% of games, and the cause is almost certainly the same as before: **the spawn pipeline never runs**.

1. **Spawn gating was too strict.** Both spawn rules required at least 3 farmers left in the pool. If the game starts with only 2 or 3 farmers, nothing ever spawns, and the warrior count never grows.
2. **Damage was too low.** The Dragon has 50 HP, and a warrior deals 3 per hit, so about 17 warrior hits are needed. With only the starting warriors, the Dragon's 40% group hits and 20% eat chance make that unreachable within 30 steps.
3. **Farmers were wasted.** Farmers in the Cave were sent back to the Village even in the endgame, when every point of damage counts.

## Revised strategy

The game is split into phases based on the step count and the Dragon's remaining HP.

**Phase 1: Build (early steps)**
- Warriors go to the Cave right away, so the Dragon is attacked well before step 15.
- Farmers spawn warriors as soon as wheat reaches 12. Spawning is allowed with only 2 farmers available, so the pipeline starts even with a small starting population.
- One early farmer spawn is allowed to meet the farmer-growth requirement.
- Farmers that are not spawning keep farming, so wheat keeps coming in.

**Phase 2: Finish (when the Dragon is low or time is running out)**
- When the Dragon's HP is at or below the damage that the current warriors plus farmers can deal in about two steps, or after step 18, every farmer also goes to the Cave to attack. Farmers add 1 damage each, which matters at the end.
- Spawning stops in this phase, because a new villager cannot attack before the 30-step limit anyway.

**Cave**
- Warriors always attack.
- Farmers attack only in the finish phase, otherwise they return to the Village.

Every component is re-assigned on every step.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Build phase: warriors attack from the start, farmers spawn new warriors
    (and a few farmers) whenever wheat allows.
    Finish phase: when the Dragon is nearly dead or time is running out,
    farmers join the attack as well.
    """

    SPAWN_GROUP_SIZE = 2
    WARRIOR_WHEAT_COST = 12
    FARMER_WHEAT_COST = 10
    MAX_FARMER_SPAWNS = 2
    FINISH_STEP = 18
    FINISH_DRAGON_HP = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0

    def _finish_phase(self, environment, step):
        return step >= self.FINISH_STEP or environment.dragon.hp <= self.FINISH_DRAGON_HP

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Warriors always go to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        # In the finish phase farmers also go to attack; no more spawning.
        if self._finish_phase(environment, step):
            for f in farmers:
                environment.assign_group(f, "cave")
            return

        wheat = environment.farm.wheat
        pool = list(farmers)
        spawn_warrior_group = []
        spawn_farmer_group = []

        # Warrior spawn has priority: warriors do the damage.
        if wheat >= self.WARRIOR_WHEAT_COST and len(pool) >= self.SPAWN_GROUP_SIZE:
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_warrior_group.append(pool.pop())
            wheat -= self.WARRIOR_WHEAT_COST

        # A few farmer spawns to meet the farmer-growth requirement.
        if (self.farmers_spawned < self.MAX_FARMER_SPAWNS
                and wheat >= self.FARMER_WHEAT_COST
                and len(pool) >= self.SPAWN_GROUP_SIZE):
            for _ in range(self.SPAWN_GROUP_SIZE):
                spawn_farmer_group.append(pool.pop())
            wheat -= self.FARMER_WHEAT_COST
            self.farmers_spawned += 1

        for f in spawn_warrior_group:
            environment.assign_group(f, "spawn warrior")
        for f in spawn_farmer_group:
            environment.assign_group(f, "spawn farmer")
        for f in pool:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        finish = self._finish_phase(environment, step)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            elif finish:
                environment.assign_group(c, "attack")
            else:
                # Early on, farmers are kept out of the Cave to protect wheat income.
                environment.assign_group(c, "village")
```