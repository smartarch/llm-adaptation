from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the village by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning plan: prioritize Warrior spawns first, then Farmer spawns
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Warrior spawns possible: 2 farmers per spawn, 12 wheat per spawn
        k_w = min(len(farmers) // 2, int(wheat // 12))

        spawn_warrior_group = farmers[:2 * k_w]
        remaining_after_war = farmers[2 * k_w:]

        wheat_after_war = max(0, wheat - 12 * k_w)

        # Farmer spawns possible: 2 farmers per spawn, 10 wheat per spawn
        k_f = min(len(remaining_after_war) // 2, int(wheat_after_war // 10))

        spawn_farmer_group = remaining_after_war[:2 * k_f]
        farm_group = remaining_after_war[2 * k_f:]

        # 3) Assign groups to villagers
        for c in spawn_warrior_group:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer_group:
            environment.assign_group(c, "spawn farmer")
        for c in farm_group:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the cave by role
        cave_warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Warriors should attack the Dragon
        for w in cave_warriors:
            environment.assign_group(w, "attack")

        # 2) Farmers (if any) should go back to the Village
        cave_farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        for f in cave_farmers:
            environment.assign_group(f, "village")

        # If there are any other types (edge cases), send them to village as a safe default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "village")