from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (to be handled in cave step as attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # If there are no farmers, nothing to spawn or farm
        n_farmers = len(farmers)
        if n_farmers == 0:
            return

        # Read current wheat from the farm environment
        wheat = 0
        try:
            wheat = int(environment.farm.wheat)
        except Exception:
            wheat = 0

        # Decide strategy based on the current step
        # Early steps (step <= 6) bias toward Warrior spawns to boost early DPS
        path_A = (step <= 6)

        if path_A:
            # Path A: spawn Warriors first, then Farmers
            max_war_spawns = min(n_farmers // 2, wheat // 12)
            remaining_farmers = n_farmers - max_war_spawns * 2
            wheat_after_war_spawns = wheat - max_war_spawns * 12
            max_farm_spawns = min(remaining_farmers // 2, wheat_after_war_spawns // 10)

            idx = 0
            # Assign 2*max_war_spawns farmers to "spawn warrior"
            for _ in range(max_war_spawns * 2):
                if idx < len(farmers):
                    environment.assign_group(farmers[idx], "spawn warrior")
                    idx += 1

            # Assign 2*max_farm_spawns farmers to "spawn farmer"
            for _ in range(max_farm_spawns * 2):
                if idx < len(farmers):
                    environment.assign_group(farmers[idx], "spawn farmer")
                    idx += 1

            # Remaining farmers go to farming
            for j in range(idx, len(farmers)):
                environment.assign_group(farmers[j], "farm")
        else:
            # Path B: spawn Farmers first, then Warriors
            max_farm_spawns = min(n_farmers // 2, wheat // 10)
            wheat_after_farm_spawns = wheat - max_farm_spawns * 10
            remaining_farmers = n_farmers - max_farm_spawns * 2
            max_war_spawns = min(remaining_farmers // 2, wheat_after_farm_spawns // 12)

            idx = 0
            # Assign 2*max_farm_spawns farmers to "spawn farmer"
            for _ in range(max_farm_spawns * 2):
                if idx < len(farmers):
                    environment.assign_group(farmers[idx], "spawn farmer")
                    idx += 1

            # Assign 2*max_war_spawns farmers to "spawn warrior"
            for _ in range(max_war_spawns * 2):
                if idx < len(farmers):
                    environment.assign_group(farmers[idx], "spawn warrior")
                    idx += 1

            # Remaining farmers go to farming
            for j in range(idx, len(farmers)):
                environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack; Farmers should go to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go to Village to farm or spawn
                environment.assign_group(c, "village")