import abc

# Assuming the base class is available from the specified module
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave (they will attack from there)
        for w in Warriors:
            environment.assign_group(w, "cave")

        # 2) Distribute Farmers in village
        n_f = len(farmers)

        if n_f > 0:
            # Split strategy: ~60% farm, ~25% spawn farmer, ~15% spawn warrior
            n_farm = max(0, int(n_f * 0.60))
            n_spawn_farmer = max(0, int(n_f * 0.25))
            n_spawn_warrior = n_f - (n_farm + n_spawn_farmer)

            idx = 0
            for _ in range(n_farm):
                environment.assign_group(farmers[idx], "farm")
                idx += 1
            for _ in range(n_spawn_farmer):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1
            for _ in range(n_spawn_warrior):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

            # If there are no Warriors at all (to ensure early attack), try to seed one
            # by sending two Farmers to spawn Warrior, if possible and within step window
            if len(warriors) == 0 and step <= 15 and len(farmers) >= 2:
                # Reassign first two farmers to spawn warrior to kickstart early defense
                environment.assign_group(farmers[0], "spawn warrior")
                environment.assign_group(farmers[1], "spawn warrior")

        # If there are no farmers (edge case), nothing else to do here
        # The environment will handle spawning when there are members in the spawn groups

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, all Warriors should attack; Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")