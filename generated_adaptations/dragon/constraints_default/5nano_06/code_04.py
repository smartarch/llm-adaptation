from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers currently in the Village into categories based on their role.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Move all Warriors to the Cave (attack later in assign_in_cave context)
        for w in warriors:
            environment.assign_group(w, "cave")  # send to cave to eventually attack

        total_farmers = len(farmers)

        if total_farmers == 0:
            return  # nothing else to assign

        # Wheat available for spawning
        wheat = int(getattr(environment.farm, "wheat", 0))

        # Spawn Warriors first (maximize early DPS)
        max_wspawn_pairs = min(total_farmers // 2, wheat // 12)
        spawn_warrior_count = 2 * max_wspawn_pairs
        farmers_after_warrior_spawns = total_farmers - spawn_warrior_count

        remaining_wheat_after_warriors = wheat - max_wspawn_pairs * 12

        # Then spawn Farmers if possible
        max_fspawn_pairs = min(farmers_after_warrior_spawns // 2, remaining_wheat_after_warriors // 10)
        spawn_farm_count = 2 * max_fspawn_pairs

        farmers_remaining_for_farm = total_farmers - (spawn_warrior_count + spawn_farm_count)

        # Now assign groups accordingly
        idx = 0

        # Assign spawn warrior farmers (first)
        for _ in range(spawn_warrior_count):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Assign spawn farmer farmers (second)
        for _ in range(spawn_farm_count):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Remaining farmers go to farming
        for _ in range(farmers_remaining_for_farm):
            if idx < len(farmers):
                environment.assign_group(farmers[idx], "farm")
                idx += 1

        # Any leftover farmers (edge cases) default to farming
        while idx < len(farmers):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Divide Cave villagers:
        # - Warriors should attack -> group "attack"
        # - Farmers should go back to Village -> group "village"
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")