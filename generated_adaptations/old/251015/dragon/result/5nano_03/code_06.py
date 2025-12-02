from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village context
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave (as required)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan for farmers (conservative: spawn at most 1 farmer per step)
        F = len(farmers)
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        spf = 0  # number of "spawn farmer" actions this step (0 or 1)
        if F >= 2 and wheat >= 10:
            # Allow at most 1 spawn farmer per step
            spf = min(1, F // 2, wheat // 10)

        spf2 = spf * 2  # number of farmers assigned to "spawn farmer"
        remaining_after_spf = F - spf2

        # Wheat remaining after potential farmer spawn
        wheat_after_spf = wheat - spf * 10

        # We intentionally avoid spawning warriors early to limit Cave population risk.
        swp = 0
        swp2 = 0

        # If there are farmers, ensure at least one farmer is farming when possible
        # If after assigning spawns there are no farmers left to farm, try to reallocate by reducing spf by 1 if possible
        if F > 0 and spf2 == F:
            if spf > 0:
                spf -= 1
                spf2 = spf * 2
                remaining_after_spf = F - spf2
                wheat_after_spf = wheat - spf * 10

        # Assign groups to farmers deterministically:
        # - First 2*spf go to "spawn farmer"
        # - Remaining (if any) go to "farm" (we keep swp = 0 for now)
        for idx, f in enumerate(farmers):
            if idx < spf2:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, send Warriors to attack, Farmers back to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")