from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farm_group = "farm"
        cave_group = "cave"
        spawn_farmer = "spawn farmer"
        spawn_warrior = "spawn warrior"

        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Phased assault: send a small batch of Warriors to the Cave this step
        attack_batch = 0
        if len(warriors) > 0:
            if step < 3:
                attack_batch = 1
            elif step < 6:
                attack_batch = min(2, len(warriors))
            else:
                attack_batch = min(3, len(warriors))

        for i in range(attack_batch):
            environment.assign_group(warriors[i], cave_group)

        # Spawning logic using Wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmers available to spawn
        # Note: Warriors moved to cave are no longer in this village list for this step
        spawns_farm = min(len(farmers) // 2, wheat // 10)

        # Assign 2*spawns_farm farmers to the "spawn farmer" group
        for c in farmers[:2 * spawns_farm]:
            environment.assign_group(c, spawn_farmer)

        # Wheat left after farmer spawns
        wheat_after_farm = wheat - spawns_farm * 10
        remaining_after_farm = farmers[2 * spawns_farm:]

        # Spawn warriors from the remaining farmers if wheat allows
        spawns_warrior = min(len(remaining_after_farm) // 2, wheat_after_farm // 12)

        for c in remaining_after_farm[:2 * spawns_warrior]:
            environment.assign_group(c, spawn_warrior)

        remaining_after_warrior = remaining_after_farm[2 * spawns_warrior:]

        # The rest stay in Farm (Farmers continue farming)
        for c in remaining_after_warrior:
            environment.assign_group(c, farm_group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attack_group = "attack"
        cave_group = "cave"
        village_group = "village"

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, attack_group)
            else:
                # Farmers in the Cave should retreat to the Village to farm/spawn
                environment.assign_group(c, village_group)