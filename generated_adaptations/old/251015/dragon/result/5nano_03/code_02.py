from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in the Village to farm or spawn
        # Use a simple spawning plan:
        # - If we have >= 2 farmers and at least 10 wheat, assign 2 to "spawn farmer" to enable spawning.
        # - The remaining farmers go to "farm".
        # - If we have fewer than 2 farmers, all go to "farm".
        if len(farmers) >= 2:
            # Try to spawn: allocate first two farmers to the spawn group
            spawn_candidates = farmers[:2]
            for f in spawn_candidates:
                environment.assign_group(f, "spawn farmer")
            # Remaining farmers go to farming
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
        else:
            # Not enough farmers to spawn, all farm
            for f in farmers:
                environment.assign_group(f, "farm")

        # Note: We intentionally do not assign anyone to "spawn warrior" to keep the strategy simple.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors should attack, Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")