from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to a single final group per component:
        - Warriors -> cave
        - Farmers -> either farm, spawn farmer, or spawn warrior
        Spawning is maximized given current wheat to increase population.
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Prepare final group mapping (one group per component)
        final_group = {}

        # 1) Warriors always go to cave now
        for w in warriors:
            final_group[w] = "cave"

        # 2) Farmers decide whether to farm or spawn
        N = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Initialize all farmers to spawn logic
        S = min(N // 2, wheat // 10)  # number of farmer-spawns
        wheat_after_farm_spawns = wheat - 10 * S
        remaining_farmers_after_f = N - 2 * S
        W = min(remaining_farmers_after_f // 2, wheat_after_farm_spawns // 12)  # number of warrior-spawns

        # Pick farmers for spawns
        idx = 0
        # First 2*S farmers to "spawn farmer"
        for i in range(2 * S):
            final_group[farmers[idx]] = "spawn farmer"
            idx += 1
        # Next 2*W farmers to "spawn warrior"
        for i in range(2 * W):
            final_group[farmers[idx]] = "spawn warrior"
            idx += 1
        # Remaining farmers to "farm"
        while idx < N:
            final_group[farmers[idx]] = "farm"
            idx += 1

        # Apply final groups, ensuring exactly one assignment per component
        for comp in components:
            grp = final_group.get(comp, None)
            if grp is None:
                # Fallback: keep in village farming
                grp = "farm"
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, move Warriors to attack and Farmers back to village.
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            elif role == "Farmer":
                environment.assign_group(comp, "village")
            else:
                environment.assign_group(comp, "village")