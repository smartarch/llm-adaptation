import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors in Village to Cave to ensure early attack capability.
        # - Use current Farmers to spawn as many new Farmers and Warriors as possible,
        #   maximizing DPS growth with available wheat and villagers.
        # - Remaining Farmers stay to farm.

        # Separate by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all existing Warriors in Village to Cave (to guarantee attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # After this, in Village we effectively have only Farmers (if any)
        available_wheat = environment.farm.wheat

        F_spawns = 0
        W_spawns = 0

        # 2) Compute maximum spawns given current counts and wheat
        # Each spawn farmer uses 2 farmers and 10 wheat
        max_possible_f_spawns = min(len(farmers) // 2, available_wheat // 10)

        # Tentatively assign Farmer spawns
        F_spawns = max_possible_f_spawns
        wheat_after_f_spawns = available_wheat - (F_spawns * 10)

        # Remaining farmers after allocating farmer-spawns
        remaining_farmers = len(farmers) - (F_spawns * 2)

        # Each Warrior spawn uses 2 farmers and 12 wheat
        max_possible_w_spawns = min(remaining_farmers // 2, wheat_after_f_spawns // 12)

        W_spawns = max_possible_w_spawns

        # 3) Assign spawns from farmers
        idx = 0
        # Spawn Farmers
        for _ in range(F_spawns):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # Spawn Warriors
        for _ in range(W_spawns):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # 4) Remaining farmers go to farming
        for i in range(idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # Note: Any Warriors already moved to Cave at the start remain in the Cave
        # and will be handled in assign_in_cave.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy in Cave:
        # - All Warriors in Cave should attack Dragon (group "attack")
        # - All Farmers in Cave should go back to Village (group "village")

        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any non-Warrior) should return to Village
                environment.assign_group(c, "village")