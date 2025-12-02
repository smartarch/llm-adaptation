import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # We'll decide a single final group for each component
        final_group = {}

        # 1) Warriors go to the cave (single assignment)
        for w in warriors:
            final_group[w] = "cave"

        # 2) Farmers default to farming (single assignment)
        for f in farmers:
            final_group[f] = "farm"

        # 3) Spawning strategy (spawn groups in Village)
        # Read wheat available in the Farm
        farm = getattr(environment, "farm", None)
        wheat = getattr(farm, "wheat", 0)

        # Decide on spawn allocations (ensuring single assignment per farmer)
        # Priority: if we have enough farmers and wheat, spawn in bulk
        if len(farmers) >= 4 and wheat >= 22:
            # Use 4 farmers to spawn: 2 for spawn farmer, 2 for spawn warrior
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"
            final_group[farmers[2]] = "spawn warrior"
            final_group[farmers[3]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 12:
            # Use 2 farmers to spawn 1 warrior
            final_group[farmers[0]] = "spawn warrior"
            final_group[farmers[1]] = "spawn warrior"
        elif len(farmers) >= 2 and wheat >= 10:
            # Use 2 farmers to spawn 1 farmer
            final_group[farmers[0]] = "spawn farmer"
            final_group[farmers[1]] = "spawn farmer"
        # If none of the conditions match, farmers stay in "farm" (already set)

        # Apply the final group assignments (exactly one per component)
        for comp, grp in final_group.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")