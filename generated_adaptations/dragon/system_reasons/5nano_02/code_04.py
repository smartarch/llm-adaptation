from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers in Village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        farm_group = "farm"
        cave_group = "cave"
        spawn_farmer_group = "spawn farmer"
        spawn_warrior_group = "spawn warrior"

        # Move all current warriors to the Cave to attack
        for w in warriors:
            environment.assign_group(w, cave_group)

        # Wheat available for spawning (from the Farm)
        wheat_available = getattr(environment.farm, "wheat", 0)

        F = len(farmers)

        # Determine spawn counts with sane caps to push early DPS while preserving wheat
        # Pw: number of new Warriors to spawn this turn (requires 2*Pw farmers and 12*Pw wheat)
        max_by_wheat_warrior = wheat_available // 12
        max_by_farmers_warrior = F // 2
        Pw = min(max_by_wheat_warrior, max_by_farmers_warrior, 2)  # cap at 2 for a balanced ramp

        # After allocating for Warrior spawns, determine Farmer spawns
        wheat_after_warriors = wheat_available - Pw * 12
        farmers_after_warriors = F - Pw * 2

        max_by_wheat_farmer = wheat_after_warriors // 10
        max_by_farmers_farmer = farmers_after_warriors // 2
        Pf = min(max_by_wheat_farmer, max_by_farmers_farmer, 2)  # cap at 2

        # Allocate Farmer villagers to groups
        # First allocate 2*Pw to spawn warrior
        idx = 0
        for _ in range(Pw * 2):
            if idx < F:
                environment.assign_group(farmers[idx], spawn_warrior_group)
                idx += 1

        # Then allocate 2*Pf to spawn farmer
        for _ in range(Pf * 2):
            if idx < F:
                environment.assign_group(farmers[idx], spawn_farmer_group)
                idx += 1

        # Remaining farmers go to farming
        for i in range(idx, F):
            environment.assign_group(farmers[i], farm_group)

        # Any non-Farmer components should already be assigned (Warriors moved to cave above).
        # If there are no farmers, this loop is a no-op.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: send all Warriors to attack; Farmers stay in Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")