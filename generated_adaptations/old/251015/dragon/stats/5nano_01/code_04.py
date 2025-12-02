from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Group name constants
        FARM = "farm"
        CAVE = "cave"
        SPAWN_FARMER = "spawn farmer"
        SPAWN_WARRIOR = "spawn warrior"

        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Default assignment
        # Warriors go to cave (to move to cave); Farmers stay in farm by default.
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, CAVE)
            else:
                environment.assign_group(c, FARM)

        # Step 2: Spawn farmer if possible (need two farmers and at least 10 wheat)
        wheat = 0
        if getattr(environment, "farm", None) is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        if len(farmers) >= 2 and wheat >= 10:
            # Move the first two farmers into the spawn farmer group
            to_spawn_farmers = farmers[:2]
            for c in to_spawn_farmers:
                environment.assign_group(c, SPAWN_FARMER)

            # Step 3: Optionally spawn warriors if wheat allows and we have at least 2 remaining farmers
            remaining_farmers = farmers[2:]
            if len(remaining_farmers) >= 2 and wheat >= 22:
                to_spawn_warriors = remaining_farmers[:2]
                for c in to_spawn_warriors:
                    environment.assign_group(c, SPAWN_WARRIOR)
                # The rest (if any) stay farming
                for c in remaining_farmers[2:]:
                    environment.assign_group(c, FARM)

        # Note: If fewer than 2 farmers, or wheat is insufficient, all farmers stay in farming by default.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Group name constants
        ATTACK = "attack"
        CAVE = "cave"
        VILLAGE = "village"

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors in cave should attack
                environment.assign_group(c, ATTACK)
            else:
                # Farmers in cave should return to the village
                environment.assign_group(c, VILLAGE)

        # Note: If there are any Farmers in the cave due to edge cases, they are moved to village,
        # ensuring the policy "Farmers stay in Village" is respected.