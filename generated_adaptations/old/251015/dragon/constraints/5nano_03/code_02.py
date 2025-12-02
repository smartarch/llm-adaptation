import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate current villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Policy: all Warriors go to the Cave (attack later), Farmers stay in Village
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        # Wheat available in the Farm
        wheat = environment.farm.wheat

        spawn_farmer_group_count = 0
        spawn_warrior_group_count = 0

        # Compute possible spawns for farmers first
        if F >= 2 and wheat >= 10:
            max_spawns_by_villagers = F // 2
            max_spawns_by_wheat = wheat // 10
            X = min(max_spawns_by_villagers, max_spawns_by_wheat)
            spawn_farmer_group_count = 2 * X

            # Remaining farmers after reserving for farmer spawns
            F_remain_after_farmer_spawns = F - spawn_farmer_group_count

            # Now consider spawning warriors with remaining villagers
            if F_remain_after_farmer_spawns >= 2 and wheat >= 12:
                max_spawns_by_villagers2 = F_remain_after_farmer_spawns // 2
                max_spawns_by_wheat2 = wheat // 12
                Y = min(max_spawns_by_villagers2, max_spawns_by_wheat2)
                spawn_warrior_group_count = 2 * Y

        else:
            F_remain_after_farmer_spawns = F

        # Farmers left for farming after spawns
        if F >= 2:
            if spawn_farmer_group_count == 0 and spawn_warrior_group_count == 0:
                remaining_farmers_for_farm = F  # no spawns possible
            else:
                remaining_farmers_for_farm = F - (spawn_farmer_group_count + spawn_warrior_group_count)
        else:
            remaining_farmers_for_farm = F

        # Create a deterministic assignment plan for farmers
        group_assignments = []
        group_assignments.extend(["spawn farmer"] * spawn_farmer_group_count)
        group_assignments.extend(["spawn warrior"] * spawn_warrior_group_count)
        group_assignments.extend(["farm"] * remaining_farmers_for_farm)

        # In case of any discrepancy, fill the rest with farming
        if len(group_assignments) < F:
            group_assignments.extend(["farm"] * (F - len(group_assignments)))

        # Assign groups to farmers in their list order
        for farmer, g in zip(farmers, group_assignments):
            environment.assign_group(farmer, g)

        # Note: Warriors are already assigned to "cave" above

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, make Warriors attack and move Farmers back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")