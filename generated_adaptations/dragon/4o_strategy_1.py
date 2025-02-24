from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Ensure all Warriors go to the Cave
        for warrior in warriors:
            environment.assign_group(warrior, "cave")

        # Determine the number of new villagers that can be spawned
        max_farmers_spawnable = environment.wheat // 10
        max_warriors_spawnable = environment.wheat // 12

        farmer_spawn_count = min(len(farmers) // 2, max_farmers_spawnable)
        warrior_spawn_count = min(len(farmers) // 2, max_warriors_spawnable)

        # Assign Farmers to spawning if possible
        farmers_assigned = 0
        for i in range(farmer_spawn_count * 2):
            environment.assign_group(farmers[i], "spawn farmer")
            farmers_assigned += 1

        for i in range(warrior_spawn_count * 2):
            if farmers_assigned < len(farmers):
                environment.assign_group(farmers[farmers_assigned], "spawn warrior")
                farmers_assigned += 1

        # Assign remaining Farmers to farming
        for i in range(farmers_assigned, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, step: int):
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")  # Send Farmers back to Village
