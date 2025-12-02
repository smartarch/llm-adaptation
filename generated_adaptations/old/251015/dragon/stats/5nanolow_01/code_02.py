from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Default: farmers stay in village to farm or spawn; warriors move to cave
        farmers_in_village = []
        for comp in components:
            if getattr(comp, "role", None) == "Farmer":
                farmers_in_village.append(comp)
                # Stay in village by default
                self.environment.assign_group(comp, "farm")
            else:
                # Warriors go to cave to eventually attack
                self.environment.assign_group(comp, "cave")

        # Determine how many farmers can participate in spawning
        # We assume environment.farm.wheat reflects current wheat
        total_farm_wheat = int(getattr(environment, "farm").wheat)
        remaining_farmers = list(farmers_in_village)

        # Compute possible spawns with simple greedy allocation
        max_farm_spawns = min(len(remaining_farmers) // 2, total_farm_wheat // 10)
        # Allocate 2*max_farm_spawns farmers to "spawn farmer"
        spawn_farmer_count = 2 * max_farm_spawns
        for i in range(spawn_farmer_count):
            comp = remaining_farmers[i]
            self.environment.assign_group(comp, "spawn farmer")

        # Remaining farmers after assigning to spawn farmer
        remaining_after_farmer_spawns = remaining_farmers[spawn_farmer_count:]

        # Update wheat after allocating farmer spawns
        # (Note: we don't mutate environment state here, we just plan groupings.)
        wheat_after_farmer_spawns = total_farm_wheat - (10 * max_farm_spawns)

        max_warrior_spawns = min(len(remaining_after_farmer_spawns) // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_count = 2 * max_warrior_spawns
        for i in range(spawn_warrior_count):
            comp_index = spawn_farmer_count + i
            comp = remaining_farmers[i]  # from the remaining_after_farmer_spawns
            self.environment.assign_group(comp, "spawn warrior")

        # Any leftover farmers (not used for spawns) stay as farmers (already assigned to "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self.environment.assign_group(comp, "attack")
            else:
                # Farmers return to village
                self.environment.assign_group(comp, "village")