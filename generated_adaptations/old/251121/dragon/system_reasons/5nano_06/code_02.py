from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Split villagers in village into farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave (they will attack later in assign_in_cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers: by default, keep in village and farm
        # If wheat is abundant and step allows, allocate some farmers to spawn
        # Strategy: try to spawn a small number of new villagers when possible
        # Determine wheat available
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # How many farmers to allocate to spawning
        spawn_farmer_count = 0
        spawn_warrior_count = 0

        # Heuristic: if we have enough farmers to spare and enough wheat, do small spawns
        # Spawn 2 new farmers by using 4 villagers in "spawn farmer" (needs 20 wheat total to guarantee 2 spawns)
        if step <= 8 and len(farmers) >= 4 and wheat >= 20:
            spawn_farmer_count = 4  # 4 farmers will yield floor(4/2)=2 farmers if wheat >= 20
            # After reserving for farmers, check if we can also spawn a warrior
            if len(farmers) >= 6 and wheat >= 32:
                spawn_warrior_count = 2  # 2 villagers in "spawn warrior" yield 1 warrior if wheat >= 12
        # If we couldn't meet the above, keep all remaining farmers farming
        idx = 0
        # Assign first spawn_farmer_count farmers to "spawn farmer"
        for i in range(spawn_farmer_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Assign next spawn_warrior_count farmers to "spawn warrior"
        for i in range(spawn_warrior_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers go to "farm" (stay in village and farm)
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # If there are any farmers not assigned yet (edge cases), ensure they are in farm
        # (Not strictly necessary due to the logic above, but safe.)
        # (No explicit action needed here since all farmers were assigned.)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack the Dragon.
        # Farmers should return to the Village (they should stay in the Village per strategy).
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to village
                environment.assign_group(c, "village")