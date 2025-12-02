from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to the Cave (for Warriors only, by policy)
        - "spawn farmer": for every two villagers assigned here and 10 wheat, a new Farmer is spawned
        - "spawn warrior": reserved for spawning Warriors (not actively used in this strategy)
        Strategy:
        - Warriors -> "cave"
        - Farmers -> default "farm"
        - Move a subset of Farmers into "spawn farmer" based on available Wheat
        """
        # Collect indices for farmers to decide spawning
        farmers_indices = [i for i, c in enumerate(components) if getattr(c, 'role', None) == "Farmer"]
        n_farmers = len(farmers_indices)

        # Wheat available for spawning farmers
        wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # How many farmers can we spawn this turn? Each spawn needs 2 farmers and 10 wheat
        max_spawn_farmers = min(n_farmers // 2, wheat // 10)
        # We will assign 2*max_spawn_farmers farmers to the "spawn farmer" group
        spawn_count = 2 * max_spawn_farmers
        spawn_indices = set(farmers_indices[:spawn_count])

        for idx, comp in enumerate(components):
            role = getattr(comp, 'role', None)
            if role == "Warrior":
                environment.assign_group(comp, "cave")
            elif role == "Farmer":
                if idx in spawn_indices:
                    environment.assign_group(comp, "spawn farmer")
                else:
                    environment.assign_group(comp, "farm")
            else:
                # Fallback: keep in farm if unknown role
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Warriors attack the Dragon
        - "cave": Stay in the Cave
        - "village": Farmers go back to the Village
        Policy:
        - All Warriors go to "attack"
        - All Farmers go to "village"
        """
        for comp in components:
            role = getattr(comp, 'role', None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            elif role == "Farmer":
                environment.assign_group(comp, "village")
            else:
                environment.assign_group(comp, "village")