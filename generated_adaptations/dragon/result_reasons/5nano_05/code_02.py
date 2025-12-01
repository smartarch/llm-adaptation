from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave (they will attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farm by default for all Farmers (stay in Village)
        remaining_farmers = list(farmers)

        # 3) Spawn opportunities (prefer some spawns if wheat available)
        # Spawn 1st: 2 farmers -> spawn farmer if wheat >= 10 and at least 4 farmers exist
        if len(remaining_farmers) >= 4 and getattr(environment.farm, "wheat", 0) >= 10:
            for _ in range(2):
                if remaining_farmers:
                    f = remaining_farmers.pop(0)
                    environment.assign_group(f, "spawn farmer")

        # 4) Spawn 2nd: 2 farmers left -> spawn warrior if wheat >= 12
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for _ in range(2):
                if remaining_farmers:
                    f = remaining_farmers.pop(0)
                    environment.assign_group(f, "spawn warrior")

        # 5) Assign any still remaining farmers to farming in village
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

        # If there are any other components (unexpected), default them to farm
        assigned = set()
        for g in ["cave", "farm", "spawn farmer", "spawn warrior"]:
            # mark as assigned by collecting components already assigned in previous loops
            pass  # assignments are done per component directly below

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack, Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:  # Farmer or any other role should return to Village
                environment.assign_group(c, "village")