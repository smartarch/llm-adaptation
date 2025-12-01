from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawning logic for Farmers in Village
        F = len(farmers)
        W = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            W = getattr(farm_env, "wheat", 0)

        best_sf, best_sw, best_S = 0, 0, -1  # sf: farmers to spawn, sw: warriors to spawn
        # Brute-force search for best combination (sf, sw)
        for sf in range(0, F // 2 + 1):
            if 10 * sf > W:
                continue
            rem_f = F - 2 * sf
            max_sw_by_farm = rem_f // 2
            max_sw_by_wheat = (W - 10 * sf) // 12
            sw = min(max_sw_by_farm, max_sw_by_wheat)
            if sw < 0:
                sw = 0
            S = sf + sw
            if S > best_S or (S == best_S and sf > best_sf):
                best_sf, best_sw, best_S = sf, sw, S

        sf = best_sf
        sw = best_sw

        # Assign farmers to the appropriate spawn groups or farming
        farmers_iter = iter(farmers)

        # First, assign 2*sf farmers to "spawn farmer"
        for _ in range(2 * sf):
            try:
                c = next(farmers_iter)
                environment.assign_group(c, "spawn farmer")
            except StopIteration:
                break

        # Then, assign 2*sw farmers to "spawn warrior"
        for _ in range(2 * sw):
            try:
                c = next(farmers_iter)
                environment.assign_group(c, "spawn warrior")
            except StopIteration:
                break

        # Remaining farmers go to "farm"
        for c in farmers_iter:
            environment.assign_group(c, "farm")

        # Note: If there are no farmers, Warriors already assigned to "cave".
        # If there are no warriors, all farmers are handled above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack; Farmers should go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers stay in the Village
                environment.assign_group(c, "village")