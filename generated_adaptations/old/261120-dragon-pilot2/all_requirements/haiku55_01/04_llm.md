## Changes

The test report points to three problems, which I fixed as follows.

1. **Invalid meal assignments.** Eating consumes wheat, but the old code assigned every hungry villager to "eat" without checking the stock. Now meals are funded from the wheat available in that step, and the most-starved villagers are fed first. Villagers who cannot be fed are assigned to "farm" instead, so they are not left unassigned.

2. **Unassigned villagers.** The old code could skip a villager if a meal assignment was rejected. Now a single `assigned` set tracks every component, and a final pass assigns anyone still unassigned, so each component is assigned exactly once.

3. **Dragon not killed and regeneration.** The old code spawned only the minimum (2 warriors, 1 farmer) and used farmers as the only spawn pool, so there were too few attackers to finish 100 HP within 30 steps. The new version:
   - Spawns more warriors (up to 3 extra) whenever wheat and two non-hungry spawners are available, since warriors are the damage dealers.
   - Keeps every fed warrior in the Cave attacking each step, and sends back only warriors that have gone 4 or more steps without food. Returning warriors are replaced by the next fed warriors, so the Dragon is attacked more consistently and regenerates less.

Regeneration timing still depends on meal scheduling, so this is a heuristic rather than a guarantee.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: feed villagers that have gone this many steps without food.
    VILLAGE_EAT_THRESHOLD = 3
    # Cave: warriors return to the Village once they reach this many steps without food.
    CAVE_RETURN_THRESHOLD = 4
    WARRIOR_SPAWN_TARGET = 3   # total new warriors we aim to spawn
    FARMER_SPAWN_TARGET = 1    # total new farmers we aim to spawn
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.first_attack_step = None

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat_left = environment.farm.wheat
        assigned = set()

        def assign(c, group):
            environment.assign_group(c, group)
            assigned.add(id(c))

        # 1) Feeding has priority. Feed the most-starved villagers first,
        #    as far as the available wheat allows (each meal costs 1 wheat).
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat_left >= 1:
                assign(c, "eat")
                wheat_left -= 1
        # Hungry villagers who could not be fed still stay in the Village.
        for c in hungry:
            if id(c) not in assigned:
                assign(c, "farm")

        # 2) Spawning. Spawners must be non-hungry villagers who are still unassigned.
        #    Spawners remain in the Village, so they do not fight this step.
        candidates = [c for c in components if id(c) not in assigned]
        farmers = [c for c in candidates if c.role == "Farmer"]
        warriors = [c for c in candidates if c.role == "Warrior"]
        pool = farmers + warriors  # prefer farmers as spawners to keep warriors fighting

        def take_pair():
            free = [c for c in pool if id(c) not in assigned]
            return free[:2] if len(free) >= 2 else None

        # Spawn warriors first, as they are the damage dealers.
        while self.warriors_spawned < self.WARRIOR_SPAWN_TARGET and wheat_left >= self.WARRIOR_COST:
            pair = take_pair()
            if pair is None:
                break
            for c in pair:
                assign(c, "spawn warrior")
            self.warriors_spawned += 1
            wheat_left -= self.WARRIOR_COST

        # Then spawn the farmer(s).
        while self.farmers_spawned < self.FARMER_SPAWN_TARGET and wheat_left >= self.FARMER_COST:
            pair = take_pair()
            if pair is None:
                break
            for c in pair:
                assign(c, "spawn farmer")
            self.farmers_spawned += 1
            wheat_left -= self.FARMER_COST

        # 3) Everyone still unassigned.
        dragon_alive = environment.dragon.hp > 0
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior" and dragon_alive and c.steps_since_meal < self.VILLAGE_EAT_THRESHOLD:
                assign(c, "cave")
            else:
                assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attacked_any = False
        for c in components:
            # Farmers must not fight; starving/hungry warriors go back to eat.
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
                attacked_any = True

        if attacked_any and self.first_attack_step is None:
            self.first_attack_step = step
```