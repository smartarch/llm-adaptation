from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0
        self.max_warr_spawn = 3
        self.max_farm_spawn = 3

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.wheat
        dragon_hp = environment.dragon.hp

        # All warriors go to the cave immediately to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # If dragon is very low HP, no point spawning—just farm to keep economy
        farmers_available = list(farmers)

        # Determine what to do with farmers:
        # Priority 1: Spawn warriors (they deal 3 dmg/turn, critical for killing 50 HP dragon)
        # Priority 2: Spawn farmers (more wheat production)
        # Priority 3: Farm
        # Need at least 2 farmers in the spawn group for a spawn action

        # Build a spawn schedule: alternate warrior/farmer spawns over early-mid game
        # Steps 0-1: pure farming to build wheat
        # Steps 2+: try to spawn
        should_spawn_warrior = (
            self.warriors_spawned < self.max_warr_spawn
            and step >= 1
            and wheat >= 12
            and len(farmers_available) >= 2
        )

        should_spawn_farmer = (
            self.farmers_spawned < self.max_farm_spawn
            and step >= 3
            and wheat >= 10
            and len(farmers_available) >= 2
            and not should_spawn_warrior  # warrior spawn takes priority
        )

        # Also spawn farmer if we already hit warrior cap
        if self.warriors_spawned >= self.max_warr_spawn:
            should_spawn_farmer = (
                self.farmers_spawned < self.max_farm_spawn
                and wheat >= 10
                and len(farmers_available) >= 2
            )

        if should_spawn_warrior:
            for i in range(2):
                environment.assign_group(farmers_available[i], "spawn warrior")
            farmers_available = farmers_available[2:]
            self.warriors_spawned += 1
        elif should_spawn_farmer:
            for i in range(2):
                environment.assign_group(farmers_available[i], "spawn farmer")
            farmers_available = farmers_available[2:]
            self.farmers_spawned += 1

        # All remaining farmers farm
        for f in farmers_available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Warriors attack the dragon every turn they are in the cave
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in the cave; send them back to village
                environment.assign_group(c, "village")