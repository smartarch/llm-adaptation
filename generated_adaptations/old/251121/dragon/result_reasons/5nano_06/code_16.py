from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In the Village: route all Farmers to farming and all Warriors to the Cave
        # Then perform conservative, disjoint spawning when wheat allows.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default placements
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmer: need at least 4 farmers and wheat >= 10
        spawn_farmer = []
        if len(farmers) >= 4 and wheat >= 10:
            # Choose two farmers to join the spawn farmer group
            spawn_farmer = farmers[:2]
            for c in spawn_farmer:
                environment.assign_group(c, "spawn farmer")

        # Spawn warrior: choose two from remaining villagers (excluding farmer spawn) if possible
        remaining_for_war = [c for c in components if c not in spawn_farmer]
        spawn_war = []
        if len(remaining_for_war) >= 2 and wheat >= 12:
            spawn_war = remaining_for_war[:2]
            for c in spawn_war:
                environment.assign_group(c, "spawn warrior")

        # End of village assignment; in-cave logic will handle actual attack later.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")