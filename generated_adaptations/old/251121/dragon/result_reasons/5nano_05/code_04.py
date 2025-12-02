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
        farm_wheat = getattr(environment.farm, "wheat", 0)

        idx = 0
        # Prefer to spawn Warriors early (step <= 5) to ensure early attack
        spawns_warriors = 0
        if step <= 5 and len(farmers) >= 2 and farm_wheat >= 12:
            # Maximum number of warrior spawns limited by wheat and pairs of farmers
            spawns_warriors = min(len(farmers) // 2, farm_wheat // 12)

        for _ in range(spawns_warriors * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Recompute remaining wheat after potential warrior spawns
        remaining_wheat = farm_wheat - spawns_warriors * 12

        # Spawn farmers if wheat allows
        spawns_farmers = 0
        if remaining_wheat >= 10 and len(farmers) - idx >= 2:
            spawns_farmers = min((len(farmers) - idx) // 2, remaining_wheat // 10)

        for _ in range(spawns_farmers * 2):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers go to farming
        for f in farmers[idx:]:
            environment.assign_group(f, "farm")

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

        # All Warriors should attack
        for w in warriors_in_cave:
            environment.assign_group(w, "attack")

        # Farmers should go back to the Village (to keep farming)
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # No fallback: follow the explicit strategy and constraints.