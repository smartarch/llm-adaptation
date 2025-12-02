```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers in the village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        # Wheat available in the farm
        W = getattr(environment.farm, "wheat", 0)

        # Spawn strategy:
        # - Prioritize spawning Warriors (needs 2 farmers and 12 wheat)
        # - Then spawn Farmers (needs 2 farmers and 10 wheat)
        spawn_warrior_spawns = min(F // 2, W // 12)
        W_after_war = W - 12 * spawn_warrior_spawns
        F_after_war = F - 2 * spawn_warrior_spawns

        spawn_farm_spawns = min(F_after_war // 2, W_after_war // 10)

        # Remaining farmers will do farming
        remaining_farmers_for_farm = F - 2 * (spawn_warrior_spawns + spawn_farm_spawns)

        # Group sizes
        spawn_warrior_group_size = 2 * spawn_warrior_spawns
        spawn_farmer_group_size = 2 * spawn_farm_spawns
        farm_group_size = remaining_farmers_for_farm

        # Assign Farmers deterministically:
        # - First: spawn warriors (2 farmers per spawn)
        # - Then: spawn farmers (2 farmers per spawn)
        # - Finally: farming
        idx = 0
        for c in farmers:
            if idx < spawn_warrior_group_size:
                environment.assign_group(c, "spawn warrior")
            elif idx < spawn_warrior_group_size + spawn_farmer_group_size:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")
            idx += 1

        # All Warriors should go to the Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack the Dragon, Farmers return to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```