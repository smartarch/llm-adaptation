## Fixes

The 12 failures came from three problems in the village logic:

1. **Invalid meal orders.** The strategy put every villager with `steps_since_meal >= 3` into "eat", even when the farm had less wheat than the number of meals. The environment rejected those orders with "Not enough wheat for a meal", and the rejected villagers were left unassigned. This is why the `test_all_assigned` failures appeared with the same seeds. The fix caps the eat list at the available wheat and gives priority to the most hungry villagers.

2. **Unassigned villagers.** Villagers who could not be fed were never placed in a group, so the "each component must be assigned exactly once" check failed. Every villager now gets exactly one group in every step. Warriors who cannot eat stay in the Village on "farm" so they can eat on a later step, instead of leaving for the Cave while hungry.

3. **Missing farmer spawn.** With 15 starting wheat, the old code spent the wheat on a Warrior spawn first, so no Farmer was ever spawned. The required minimum is one new Farmer and two new Warriors. The spawn logic now tracks how many spawns it has issued. It spawns a Farmer first if none has been spawned yet, and afterwards prefers Warriors whenever wheat allows.

The Cave logic is unchanged. Warriors with 4 or more steps without food return to the Village, and everyone else in the Cave attacks or stays.

The spawn counters assume a spawn order succeeds. A failed spawn would make the counter overcount, but the logic still spawns Farmers whenever Warriors are unaffordable, so the cave-side behavior is unaffected.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Priority-based strategy:
      - In the Village, the most hungry villagers eat first, limited by available wheat.
      - Every villager not eating (or spawning) farms in the Village; unfed warriors stay
        in the Village so they can eat later.
      - Farmers are paired up to spawn one Farmer early (required) and Warriors when
        wheat allows (required: at least two).
      - In the Cave, healthy Warriors attack the Dragon; hungry Warriors and any Farmers
        return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 3
    EAT_THRESHOLD_CAVE = 4
    WARRIOR_SPAWN_COST = 12
    FARMER_SPAWN_COST = 10
    LAST_SPAWN_STEP = 20
    MIN_FARMER_SPAWNS = 1
    MIN_WARRIOR_SPAWNS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmers_spawned = 0
        self.warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # Most hungry villagers first.
        ordered = sorted(components, key=lambda c: c.steps_since_meal, reverse=True)

        # Feed only as many hungry villagers as there is wheat for.
        hungry = [c for c in ordered if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE]
        eat_list = hungry[:max(wheat, 0)]
        eat_ids = {id(c) for c in eat_list}
        budget = wheat - len(eat_list)

        # Everyone not eating is a candidate for farming or spawning.
        not_eating = [c for c in ordered if id(c) not in eat_ids]
        farmers = [c for c in not_eating if c.role == "Farmer"]
        warriors = [c for c in not_eating if c.role != "Farmer"]

        spawn_group = None  # (group name, members)
        if step <= self.LAST_SPAWN_STEP and len(farmers) >= 2:
            want_farmer_first = self.farmers_spawned < self.MIN_FARMER_SPAWNS
            if want_farmer_first and budget >= self.FARMER_SPAWN_COST:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1
            elif budget >= self.WARRIOR_SPAWN_COST:
                spawn_group = ("spawn warrior", farmers[:2])
                budget -= self.WARRIOR_SPAWN_COST
                self.warriors_spawned += 1
            elif budget >= self.FARMER_SPAWN_COST:
                spawn_group = ("spawn farmer", farmers[:2])
                budget -= self.FARMER_SPAWN_COST
                self.farmers_spawned += 1

        spawn_ids = {id(c) for c in spawn_group[1]} if spawn_group else set()

        # Assign every villager to exactly one group.
        for c in ordered:
            cid = id(c)
            if cid in eat_ids:
                environment.assign_group(c, "eat")
            elif cid in spawn_ids:
                environment.assign_group(c, spawn_group[0])
            elif c.role == "Farmer":
                environment.assign_group(c, "farm")
            else:
                # Warriors that were not fed this step stay to farm and eat later.
                # Fed-enough warriors may go to the Cave.
                if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_CAVE:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```