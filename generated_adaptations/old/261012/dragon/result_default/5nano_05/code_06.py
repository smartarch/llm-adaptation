from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available for spawning
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            try:
                wheat = int(environment.farm.wheat)
            except Exception:
                wheat = 0

        n_farmers = len(farmers)
        i = 0

        # Phase 1: Spawn as many Warriors as possible (2 farmers + 12 wheat per spawn)
        spawn_warrior_slots = min(n_farmers // 2, wheat // 12)
        spawn_warrior_count_paired = spawn_warrior_slots * 2
        for idx in range(spawn_warrior_count_paired):
            f = farmers[idx]
            # Assign in pairs: first two become "spawn warrior", next two, etc.
            if idx < spawn_warrior_count_paired:
                environment.assign_group(f, "spawn warrior")
        i = spawn_warrior_count_paired
        wheat -= spawn_warrior_slots * 12

        # Phase 2: Spawn as many Farmers as possible with remaining Farmers (2 farmers + 10 wheat)
        remaining_farmers_for_farmer_spawn = n_farmers - i
        spawn_farmer_slots = min(remaining_farmers_for_farmer_spawn // 2, wheat // 10)
        spawn_farmer_count_paired = spawn_farmer_slots * 2

        for idx in range(i, i + spawn_farmer_count_paired):
            environment.assign_group(farmers[idx], "spawn farmer")
        i += spawn_farmer_count_paired
        wheat -= spawn_farmer_slots * 10

        # Phase 3: Remaining Farmers stay in farming
        for idx in range(i, n_farmers):
            environment.assign_group(farmers[idx], "farm")

        # All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")