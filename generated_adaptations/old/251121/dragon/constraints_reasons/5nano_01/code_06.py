from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        f_count = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Aggressive spawning policy:
        # 1) Spawn as many farmer-pairs as possible given wheat and villagers
        max_farm_spawns = min(f_count // 2, wheat // 10)
        s_farm_spawns = max_farm_spawns

        # Wheat left after farmer spawns
        wheat_after_farm = wheat - s_farm_spawns * 10
        # Remaining farmers after allocating to farmer-spawns
        remaining_farmers_for_war = f_count - s_farm_spawns * 2

        # 2) Spawn as many warrior-pairs as possible with remaining resources
        max_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)
        s_war_spawns = max_war_spawns

        # Build allocations
        alloc = {
            "farm": [],
            "spawn farmer": [],
            "spawn warrior": [],
        }

        idx = 0
        # Allocate two farmers per farmer-spawn group
        for _ in range(s_farm_spawns * 2):
            alloc["spawn farmer"].append(farmers[idx])
            idx += 1

        # Allocate two farmers per warrior-spawn group
        for _ in range(s_war_spawns * 2):
            alloc["spawn warrior"].append(farmers[idx])
            idx += 1

        # Remaining farmers go to farming in the village
        for i in range(idx, f_count):
            alloc["farm"].append(farmers[i])

        # Apply the assignments
        for c in alloc["farm"]:
            environment.assign_group(c, "farm")
        for c in alloc["spawn farmer"]:
            environment.assign_group(c, "spawn farmer")
        for c in alloc["spawn warrior"]:
            environment.assign_group(c, "spawn warrior")

        # Safety: ensure every farmer not explicitly assigned is put in farm
        assigned_set = set(alloc["farm"] + alloc["spawn farmer"] + alloc["spawn warrior"])
        for f in farmers:
            if f not in assigned_set:
                environment.assign_group(f, "farm")

        # Ensure any non-Farmer/unknown components are assigned (default to farm)
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Classify villagers in the Cave
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Farmers should go to the Village
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # Warriors: maximize DPS by attacking with all warriors
        if len(warriors_in_cave) > 0:
            for w in warriors_in_cave:
                environment.assign_group(w, "attack")

        # Unknown-role villagers: default to cave
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "cave")