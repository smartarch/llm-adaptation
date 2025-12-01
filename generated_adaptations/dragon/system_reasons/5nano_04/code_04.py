from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Groups:
        # - "farm": stay in Village and farm
        # - "cave": go to the Cave
        # - "spawn farmer": spawn new Farmer (needs 2 villagers + 10 wheat)
        # - "spawn warrior": spawn new Warrior (needs 2 villagers + 12 wheat)

        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        final_group = {}

        # Default: all farmers to farming in village
        for f in farmers:
            final_group[f] = "farm"

        # Wheat available on the Farm
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0) if farm is not None else 0

        # Spawn farmer: if at least 2 farmers and wheat >= 10
        if len(farmers) >= 2 and wheat >= 10:
            chosen = farmers[:2]
            for c in chosen:
                final_group[c] = "spawn farmer"
            wheat -= 10

        # Remaining farmers eligible for spawning warriors
        remaining = [f for f in farmers if final_group.get(f) != "spawn farmer"]

        # Spawn warrior: if at least 2 remaining and wheat >= 12
        if len(remaining) >= 2 and wheat >= 12:
            chosen2 = remaining[:2]
            for c in chosen2:
                final_group[c] = "spawn warrior"
            wheat -= 12

        # Warriors go to cave
        for w in warriors:
            final_group[w] = "cave"

        # Ensure every component is assigned exactly once
        for c in components:
            grp = final_group.get(c, "farm")
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave:
        # - Warriors attack the Dragon
        # - Farmers go back to Village (stay in Village)
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")