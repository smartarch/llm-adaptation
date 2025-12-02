from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", "") == "Warrior"]

        n_farmers = len(farmers)
        n_warriors = len(warriors)

        # Wheat available for spawning (read-only in the problem statement)
        available_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Determine how many spawn pairs we should allocate to maximize spawns
        best_f, best_w = 0, 0
        best_total = -1
        # f: number of spawn-farmer pairs
        for f in range(0, n_farmers // 2 + 1):
            # w: number of spawn-warrior pairs
            max_w_for_f = (n_farmers - 2 * f) // 2
            for w in range(0, max_w_for_f + 1):
                if 10 * f + 12 * w <= available_wheat:
                    total = f + w
                    if total > best_total:
                        best_total = total
                        best_f = f
                        best_w = w

        # Assign groups
        # Spawn groups require two farmers per pair
        to_spawn_f = 2 * best_f
        to_spawn_w = 2 * best_w

        # Assign farmers: first to spawn farmer, next to spawn warrior, rest to farm
        for idx, c in enumerate(farmers):
            if idx < to_spawn_f:
                environment.assign_group(c, "spawn farmer")
            elif idx < to_spawn_f + to_spawn_w:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

        # All Warriors go to the Cave (to be attacked later)
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave, Warriors should Attack; Farmers go back to Village
        for c in components:
            if getattr(c, "role", "") == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village
                environment.assign_group(c, "village")