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

        # Aggressive spawning: maximize Warrior spawns first, then Farmer spawns
        sw = 0
        if F >= 2 and W >= 12:
            sw = min(F // 2, W // 12)

        remaining_farmers = F - 2 * sw
        W_after_sw = W - 12 * sw

        sf = 0
        if remaining_farmers >= 2 and W_after_sw >= 10:
            sf = min(remaining_farmers // 2, W_after_sw // 10)

        # Assign farmers to the appropriate spawn groups or farming
        farmers_iter = iter(farmers)

        # First, assign 2*sw farmers to "spawn warrior"
        for _ in range(2 * sw):
            try:
                c = next(farmers_iter)
                environment.assign_group(c, "spawn warrior")
            except StopIteration:
                break

        # Then, assign 2*sf farmers to "spawn farmer"
        for _ in range(2 * sf):
            try:
                c = next(farmers_iter)
                environment.assign_group(c, "spawn farmer")
            except StopIteration:
                break

        # Remaining farmers go to "farm"
        for c in farmers_iter:
            environment.assign_group(c, "farm")

        # If there are no farmers, Warriors already assigned to "cave".
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