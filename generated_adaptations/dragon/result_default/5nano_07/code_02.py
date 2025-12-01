from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be handled in assign_in_cave)
        - spawn farmer: for every two villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Classify current farmers and warriors (use safe attribute access)
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Fetch current wheat available for spawning
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0  # If wheat info is unavailable, fall back to zero

        n_farmers = len(farmers)

        # Compute how many spawns we can trigger this step (deterministic and wheat-aware)
        spawn_farmer_pairs = min(n_farmers // 2, wheat // 10)
        spawn_farmer_size = spawn_farmer_pairs * 2  # number of farmers assigned to spawn farmer

        remaining_farmers = n_farmers - spawn_farmer_size
        wheat_after_farmer_spawns = max(0, wheat - spawn_farmer_pairs * 10)

        spawn_warrior_pairs = min(remaining_farmers // 2, wheat_after_farmer_spawns // 12)
        spawn_warrior_size = spawn_warrior_pairs * 2

        # Assign in the order of the input (to be deterministic)
        farmer_index = 0
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All Warriors go to the Cave
                environment.assign_group(c, "cave")
            else:
                # Farmers: send to one of the three spawn/farm groups
                if farmer_index < spawn_farmer_size:
                    environment.assign_group(c, "spawn farmer")
                elif farmer_index < spawn_farmer_size + spawn_warrior_size:
                    environment.assign_group(c, "spawn warrior")
                else:
                    environment.assign_group(c, "farm")
                farmer_index += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - attack: Warriors should attack the Dragon
        - cave: Stay in the Cave (not used for Warriors in this strategy)
        - village: Go to the Village (Farmers should return to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers should return to the Village to farm or spawn there
                environment.assign_group(c, "village")