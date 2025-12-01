from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Spawn farmers as much as possible given 10 wheat per spawn (2 farmers per spawn).
        - With remaining farmers, spawn warriors if there is enough wheat (12 wheat per spawn, 2 villagers per spawn).
        - Remaining farmers go to the 'farm' group.
        - All Warriors go to the Cave (attack).
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # 1) Spawn farmers as much as possible
        max_farm_spawns = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = farmers[:2 * max_farm_spawns]
        remaining_farmers = farmers[2 * max_farm_spawns:]

        # Wheat after farming spawns
        wheat_after_farm = wheat - max_farm_spawns * 10

        # 2) Spawn warriors if possible with remaining farmers and wheat
        spawn_warriors = []
        max_war_spawns = min(len(remaining_farmers) // 2, wheat_after_farm // 12)
        spawn_warriors = remaining_farmers[:2 * max_war_spawns]
        remaining_farmers = remaining_farmers[2 * max_war_spawns:]

        # 3) Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in spawn_warriors:
            environment.assign_group(c, "spawn warrior")

        # All existing Warriors go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon.
        - Farmers go back to the Village.
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")