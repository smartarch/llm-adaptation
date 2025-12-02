from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to:
        - farm: Farmers stay and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers in this group and 10 wheat, a new Farmer is spawned.
        - spawn warrior: For every two villagers in this group and 12 wheat, a new Warrior is spawned.
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Final assignment mapping (component -> group)
        final_group = {}

        # Base assignments
        for w in warriors:
            final_group[w] = "cave"   # Warriors go to the Cave
        for f in farmers:
            final_group[f] = "farm"   # Farmers stay in the Village by default

        # Wheat available in the Farm
        wheat = 0
        if hasattr(environment, "farm") and getattr(environment.farm, "wheat", None) is not None:
            wheat = environment.farm.wheat

        # Spawn decisions (single-pass, one assignment per component)
        if len(farmers) >= 4 and wheat >= 20:
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"
            final_group[farmers[2]] = "spawn warrior"
            final_group[farmers[3]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 12:
            final_group[farmers[0]] = "spawn warrior"
            final_group[farmers[1]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 10:
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"

        # Apply the final assignments (each component assigned exactly once)
        for comp, gid in final_group.items():
            environment.assign_group(comp, gid)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")