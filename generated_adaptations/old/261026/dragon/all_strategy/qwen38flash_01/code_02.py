from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors immediately head to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic: want at least 2 warriors and 2 farmers spawned
        # Each spawn of 1 villager requires 2 villagers in the spawn group + wheat cost
        farmer_idx = 0

        # Priority 1: Spawn warriors (for damage output) - up to 1 per step
        if self.spawned_warriors < 2 and farmer_idx + 2 <= len(farmers) and wheat >= 12:
            environment.assign_group(farmers[farmer_idx], "spawn warrior")
            environment.assign_group(farmers[farmer_idx + 1], "spawn warrior")
            farmer_idx += 2
            wheat -= 12
            self.spawned_warriors += 1

        # Priority 2: Spawn farmers (for wheat sustainability) - up to 1 per step
        elif self.spawned_farmers < 2 and farmer_idx + 2 <= len(farmers) and wheat >= 10:
            environment.assign_group(farmers[farmer_idx], "spawn farmer")
            environment.assign_group(farmers[farmer_idx + 1], "spawn farmer")
            farmer_idx += 2
            wheat -= 10
            self.spawned_farmers += 1

        # All remaining farmers work on the farm
        for i in range(farmer_idx, len(farmers)):
            environment.assign_group(farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                # Warriors always attack the dragon from the cave
                environment.assign_group(c, "attack")
            else:
                # Farmers should not be in the cave; send them back to village
                environment.assign_group(c, "village")