from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, step: int):
        # Get the current state
        num_farmers = sum(1 for c in components if c.role == "Farmer")
        num_warriors = sum(1 for c in components if c.role == "Warrior")

        # Assign roles based on strategy
        for component in components:
            if environment.wheat >= 12 and num_warriors / (num_farmers + 1) < 0.5:
                # If we have enough wheat and warriors are under 50% of population, spawn warriors
                environment.assign_group(component, "spawn warrior")
            elif environment.wheat >= 10 and num_farmers / (num_farmers + num_warriors + 1) < 0.4:
                # Ensure at least 40% of villagers are farmers
                environment.assign_group(component, "spawn farmer")
            elif num_warriors > num_farmers:
                # If we have a high warrior count, send some to fight
                environment.assign_group(component, "cave")
            else:
                # Default case: assign to farm
                environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, step: int):
        for component in components:
            if component.hp < 20:  # If low HP, send back to village
                environment.assign_group(component, "village")
            else:
                environment.assign_group(component, "attack")  # Otherwise, attack!
