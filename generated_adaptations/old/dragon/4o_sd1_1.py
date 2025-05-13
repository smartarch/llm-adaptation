from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy parameters
        min_wheat_to_spawn = 12  # Minimum wheat required to spawn a warrior
        min_farmers = 4  # Ensure at least 4 farmers for wheat production
        warrior_ratio = 0.6  # Target ratio of warriors in the population

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Ensure enough farmers stay on the farm
        num_farmers_farming = max(min_farmers, len(farmers) // 2)
        for i, farmer in enumerate(farmers):
            if i < num_farmers_farming:
                environment.assign_group(farmer, "farm")
            else:
                environment.assign_group(farmer, "cave")  # Send extra farmers to help

        # Warriors are prioritized for cave attacks
        for warrior in warriors:
            environment.assign_group(warrior, "cave")

        # Spawning logic
        if environment.wheat >= min_wheat_to_spawn and len(components) > 2:
            if len(warriors) / len(components) < warrior_ratio:
                environment.assign_group(components[0], "spawn warrior")
                environment.assign_group(components[1], "spawn warrior")
            else:
                environment.assign_group(components[0], "spawn farmer")
                environment.assign_group(components[1], "spawn farmer")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Strategy parameters
        retreat_threshold = 2  # Health threshold for retreating villagers

        for villager in components:
            if villager.hp <= retreat_threshold:
                environment.assign_group(villager, "village")  # Send weak villagers back
            else:
                environment.assign_group(villager, "attack")  # Strong villagers keep attacking
