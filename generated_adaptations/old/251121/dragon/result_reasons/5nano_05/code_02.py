from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in the Village and farm
        - cave: go to the Cave (for Warriors)
        - spawn farmer: to spawn new Farmers
        - spawn warrior: to spawn new Warriors
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmers stay in Village by default
        # We'll decide on spawning based on available wheat
        farm_wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawns we can attempt
        spawns_farmers = 0
        if len(farmers) >= 2 and farm_wheat >= 10:
            spawns_farmers = min(len(farmers) // 2, farm_wheat // 10)

        # Allocate farmers to spawn groups first, then remaining to farm
        idx = 0
        # Assign 2*spawns_farmers villagers to "spawn farmer"
        for _ in range(spawns_farmers * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers (not used for spawning) go to farming or next spawn group
        remaining_farmers = farmers[idx:]

        spawns_warriors = 0
        if len(remaining_farmers) >= 2 and farm_wheat >= 12:
            spawns_warriors = min(len(remaining_farmers) // 2, farm_wheat // 12)

        for _ in range(spawns_warriors * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # The rest of the farmers go to farming
        for f in farmers[idx:]:
            environment.assign_group(f, "farm")

        # Note: Warriors were already sent to the cave above. No explicit assignment to "cave" here.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        # Separate by role
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]

        # All Warriors should attack the Dragon
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Farmers should go back to the Village (to keep farming)
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # Fallback: if there are no Warriors in the Cave, ensure at least one attacker exists
        if len(warriors_in_cave) == 0 and len(farmers_in_cave) > 0:
            environment.assign_group(farmers_in_cave[0], "attack")
            for f in farmers_in_cave[1:]:
                environment.assign_group(f, "village")