import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Wheat available in the Farm
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 1) Spawn Farmers if possible: need 2 farmers and 10 wheat per spawn
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        # Assign 2 * max_farm_spawns farmers to spawn farmer
        spawn_farmers = farmers[:2 * max_farm_spawns]
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")

        # Remaining wheat after farmer spawns
        wheat_after_farm_spawns = wheat - 10 * max_farm_spawns

        # 2) Spawn Warriors if possible: need 2 farmers and 12 wheat per spawn
        remaining_farmers_after_farm = farmers[2 * max_farm_spawns:]
        max_war_spawns = min(len(remaining_farmers_after_farm) // 2,
                              wheat_after_farm_spawns // 12)

        spawn_warriors = remaining_farmers_after_farm[:2 * max_war_spawns]
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # Wheat after warrior spawns
        wheat_after_war_spawns = wheat_after_farm_spawns - 12 * max_war_spawns

        # 3) Remaining Farmers (not spawning) stay to farm in Village
        remaining_farmers_final = remaining_farmers_after_farm[2 * max_war_spawns:]
        for c in remaining_farmers_final:
            environment.assign_group(c, "farm")

        # 4) All Warriors should go to Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

        # Note: Farmers spawned by "spawn farmer" or "spawn warrior" will be
        # instantiated by the environment as new villagers; current farmers
        # assigned to non-spawn groups continue farming or spawning in later steps.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: keep Warriors attacking; Farmers return to Village for farming
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")