import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers currently in the Village into Farmers and Warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave for attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Decide spawning allocations for Farmers
        # Wheat available for potential spawns
        available_wheat = int(getattr(environment.farm, "wheat", 0))

        # Max spawns Farmer: each spawn requires 2 farmers and 10 wheat
        max_spawns_farmer = min(len(farmers) // 2, available_wheat // 10)
        s_ff = 2 * max_spawns_farmer  # number of farmers assigned to "spawn farmer"

        # Wheat left after farmer-spawns
        wheat_after_ff = available_wheat - (10 * max_spawns_farmer)

        # Remaining farmers that could be used for warrior-spawns
        remaining_farmers_for_warrior_spawns = max(0, len(farmers) - s_ff)

        # Max spawns Warrior: each spawn requires 2 farmers and 12 wheat
        max_spawns_warrior = min(remaining_farmers_for_warrior_spawns // 2, wheat_after_ff // 12)
        s_fw = 2 * max_spawns_warrior  # number of farmers assigned to "spawn warrior"

        # 3) Assign farmers to their respective groups
        for idx, f in enumerate(farmers):
            if idx < s_ff:
                environment.assign_group(f, "spawn farmer")
            elif idx < s_ff + s_fw:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # If there are any other components (e.g., none others in village), they are ignored.

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")

        return