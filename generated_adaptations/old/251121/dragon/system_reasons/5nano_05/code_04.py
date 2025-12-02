from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many farmer-spawns we can perform: need 2 farmers + 10 wheat per spawn
        f_spawns = min(len(farmers) // 2, wheat // 10)

        # Wheat left after farmer-spawns
        wheat_after_f_farm = wheat - f_spawns * 10

        # Remaining farmers after allocating to farmer-spawns
        remaining_farmers_after_f_farm = len(farmers) - (2 * f_spawns)

        # Determine how many warrior-spawns we can perform: need 2 farmers + 12 wheat per spawn
        w_spawns = min(remaining_farmers_after_f_farm // 2, wheat_after_f_farm // 12)

        # Build final assignment for each farmer in a single pass (no repeated assignments)
        idx = 0
        for f in farmers:
            if idx < 2 * f_spawns:
                group = "spawn farmer"
            elif idx < 2 * f_spawns + 2 * w_spawns:
                group = "spawn warrior"
            else:
                group = "farm"
            environment.assign_group(f, group)
            idx += 1

        # All warriors must go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, attack strategy:
        # Warriors -> attack the Dragon
        # Farmers  -> go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")