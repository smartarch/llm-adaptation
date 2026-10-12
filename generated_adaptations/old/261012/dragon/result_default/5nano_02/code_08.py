from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Phase-based spawning strategy:
          - Phase 1 (step < 4): Spawn up to 2 Farmer pairs if wheat allows.
          - Phase 2 (4 <= step < 7): Spawn up to 1 Farmer pair if possible, then consider spawning Warriors if wheat allows.
          - Phase 3 (step >= 7): Gradually spawn Warriors (up to 2 pairs) if wheat allows, else prioritize Farmers to sustain wheat production.
        - Remaining Farmers go to the 'farm' group.
        - All Warriors go to the Cave (attack) as required.
        """

        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Phase-based spawning logic
        spawn_farmers = []
        remaining_farmers = farmers[:]

        if step < 4:
            # Phase 1: up to 2 farmer spawns (4 farmers max) if wheat allows
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10, 2)
            if max_farm_spawns > 0:
                spawn_farmers = remaining_farmers[:2 * max_farm_spawns]
                remaining_farmers = remaining_farmers[2 * max_farm_spawns:]
        else:
            # Phase 2/3: try to spawn at most 1 farmer pair first
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10, 1)
            if max_farm_spawns > 0:
                spawn_farmers = remaining_farmers[:2 * max_farm_spawns]
                remaining_farmers = remaining_farmers[2 * max_farm_spawns:]
            # Then try to spawn warriors if wheat allows
            # Use any remaining farmers as potential parents for warrior spawns
            if len(remaining_farmers) >= 2:
                # Compute available wheat after potential farmer spawns
                wheat_after_farm = wheat - max_farm_spawns * 10
                max_war_spawns = min(len(remaining_farmers) // 2, wheat_after_farm // 12, 2)
                if max_war_spawns > 0:
                     spawn_warriors = remaining_farmers[:2 * max_war_spawns]
                     remaining_farmers = remaining_farmers[2 * max_war_spawns:]
                else:
                    spawn_warriors = []
            else:
                spawn_warriors = []

        # Assign groups
        for c in spawn_farmers:
            environment.assign_group(c, "spawn farmer")
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
        for c in locals().get("spawn_warriors", []):
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