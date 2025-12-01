from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": Stay in the Village and farm
        - "cave": Go to the Cave (for Warriors)
        - "spawn farmer": For every two villagers assigned to this group and 10 wheat, spawn a new Farmer
        - "spawn warrior": For every two villagers assigned to this group and 12 wheat, spawn a new Warrior
        """
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat budget for spawning
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine spawn groups from farmers
        to_spawn_farm = []
        to_spawn_war = []

        # Try to allocate up to 2 farmers to spawn farmer if possible
        remaining_farmers_after_farm_spawn = farmers
        if len(farmers) >= 2 and wheat >= 10:
            to_spawn_farm = farmers[:2]
            remaining_farmers_after_farm_spawn = farmers[2:]
        else:
            to_spawn_farm = []
            remaining_farmers_after_farm_spawn = farmers

        # Try to allocate up to 2 more farmers to spawn warrior if possible
        if len(remaining_farmers_after_farm_spawn) >= 2 and wheat >= 12:
            to_spawn_war = remaining_farmers_after_farm_spawn[:2]
        else:
            to_spawn_war = []

        # Assign groups
        for c in components:
            if c in warriors:
                # All Warriors go to the Cave (we'll drill them to attack)
                environment.assign_group(c, "cave")
            elif c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            elif c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")
            else:
                # Remaining farmers stay in the Village
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (for Warriors)
        - "cave": Stay in the Cave
        - "village": Go to the Village
        """
        for c in components:
            # Warriors should attack; Farmers should return to the Village
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")