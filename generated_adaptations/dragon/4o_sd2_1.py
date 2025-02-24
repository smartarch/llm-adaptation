from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Ensure there's always a baseline of farmers producing wheat
        farmers_needed = max(5, len(farmers) // 2)  # At least 5 farmers or half of all farmers
        farmers_assigned = 0

        # Spawning logic: prioritize warriors but maintain farmers
        spawning_farmers = 0
        spawning_warriors = 0

        for c in components:
            if farmers_assigned < farmers_needed and c.role == "Farmer":
                environment.assign_group(c, "farm")
                farmers_assigned += 1
            elif environment.wheat >= 12 and spawning_warriors < 2:
                environment.assign_group(c, "spawn warrior")
                spawning_warriors += 1
            elif environment.wheat >= 10 and spawning_farmers < 2:
                environment.assign_group(c, "spawn farmer")
                spawning_farmers += 1
            else:
                environment.assign_group(c, "cave")  # Send the rest to attack

    def assign_in_cave(self, components, environment, step: int):
        # Keep track of who is weak and who is strong
        weak_villagers = [c for c in components if c.hp <= 2]  # Critically low HP
        healthy_villagers = [c for c in components if c.hp > 2]

        # If the Dragon is close to death, go all-in on attacks
        if environment.dragon.hp <= 10:
            for c in components:
                environment.assign_group(c, "attack")
            return

        # Send weak villagers back to the village to avoid death
        for c in weak_villagers:
            environment.assign_group(c, "village")

        # Attack with healthy villagers
        for c in healthy_villagers:
            environment.assign_group(c, "attack")
