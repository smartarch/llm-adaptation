import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warriors_spawned = 0
        self._farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # All warriors go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers strategy: farm or spawn
        # Need at least 2 farmers to remain farming for wheat production
        MIN_FARMERS_FARMING = 2

        if step <= 1:
            # Early game: build up wheat, all farmers farm
            for f in farmers:
                environment.assign_group(f, "farm")
            return

        # Decide whether to spawn or farm
        spawn_done = False

        # Priority 1: Spawn a warrior (costs 12 wheat, needs 2 villagers)
        # Ensure we spawn at least a few warriors
        if (len(farmers) >= MIN_FARMERS_FARMING + 2 and
                wheat >= 12 and
                self._warriors_spawned < 5):
            spawn1 = farmers[0]
            spawn2 = farmers[1]
            environment.assign_group(spawn1, "spawn warrior")
            environment.assign_group(spawn2, "spawn warrior")
            self._warriors_spawned += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            spawn_done = True

        # Priority 2: Spawn a farmer (costs 10 wheat, needs 2 villagers)
        # Ensure we spawn at least a few farmers for production
        elif (len(farmers) >= MIN_FARMERS_FARMING + 2 and
              wheat >= 10 and
              self._farmers_spawned < 4 and
              self._warriors_spawned >= 2):
            spawn1 = farmers[0]
            spawn2 = farmers[1]
            environment.assign_group(spawn1, "spawn farmer")
            environment.assign_group(spawn2, "spawn farmer")
            self._farmers_spawned += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            spawn_done = True

        # Priority 3: If dragon is getting low, spawn more warriors aggressively
        elif (dragon_hp <= 15 and
              len(farmers) >= MIN_FARMERS_FARMING + 2 and
              wheat >= 12):
            spawn1 = farmers[0]
            spawn2 = farmers[1]
            environment.assign_group(spawn1, "spawn warrior")
            environment.assign_group(spawn2, "spawn warrior")
            self._warriors_spawned += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            spawn_done = True

        # Default: all farmers farm
        if not spawn_done:
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # All warriors attack the Dragon (they deal 3 damage)
        # Even low HP warriors are worth it - deal damage before dying
        # Farmers in cave (edge case) also attack
        for c in components:
            environment.assign_group(c, "attack")