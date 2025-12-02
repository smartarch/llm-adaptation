from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition farmers and Warriors based on their read-only role attribute
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_village = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)

        # Wheat available on the Farm (default to 0 if not present)
        wheat = 0
        farm_obj = getattr(environment, "farm", None)
        if farm_obj is not None:
            wheat = getattr(farm_obj, "wheat", 0)
        if wheat is None:
            wheat = 0

        # Determine how many spawns we can perform this step
        max_spawn_farmers = min(F // 2, wheat // 10)
        num_spawn_farmers = 2 * max_spawn_farmers

        remaining_wheat_after_farm_spawns = wheat - num_spawn_farmers * 10
        remaining_farmers = F - num_spawn_farmers

        max_spawn_warriors = min(remaining_farmers // 2, remaining_wheat_after_farm_spawns // 12)
        num_spawn_warriors = 2 * max_spawn_warriors

        # Slices for assignment
        farmers_list = farmers

        spawn_farmer_group_members = farmers_list[:num_spawn_farmers]
        spawn_warrior_group_members = farmers_list[num_spawn_farmers:num_spawn_farmers + num_spawn_warriors]
        remaining_farmers_for_farm = farmers_list[num_spawn_farmers + num_spawn_warriors:]

        # Assign groups for farmers
        for c in spawn_farmer_group_members:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_group_members:
            environment.assign_group(c, "spawn warrior")
        for c in remaining_farmers_for_farm:
            environment.assign_group(c, "farm")

        # Ensure all Warriors in village go to cave
        for w in warriors_in_village:
            environment.assign_group(w, "cave")

        # Note: Any other villagers (if present) would have been handled above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, move Warriors to attack and Farmers to go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")