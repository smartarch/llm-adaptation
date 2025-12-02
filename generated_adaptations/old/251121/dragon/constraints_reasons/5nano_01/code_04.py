from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Rule: All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        f_count = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn policy:
        # - Allow at most 1 pair of Farmers per step (spawn Farmer) if possible
        # - After that, if wheat remains and we still have farmers left, allow 1 pair of Warriors (spawn Warrior)
        s_farm_spawns = 0
        if f_count >= 2 and wheat >= 10:
            s_farm_spawns = 1  # one pair -> two farmers spawned
        s_war_spawns = 0
        if s_farm_spawns:
            # Reserve 2 farmers for farmer-spawn; you need to ensure enough farmers left for war-spawn
            remaining_farmers_for_war = f_count - 2 * s_farm_spawns
            wheat_after_farm = wheat - s_farm_spawns * 10
        else:
            remaining_farmers_for_war = f_count
            wheat_after_farm = wheat

        if remaining_farmers_for_war >= 2 and wheat_after_farm >= 12:
            s_war_spawns = 1  # one pair -> two warriors spawned

        # Build allocations
        alloc = {
            "farm": [],
            "spawn farmer": [],
            "spawn warrior": [],
        }

        idx = 0
        # Assign two farmers to spawn farmer if possible
        for _ in range(s_farm_spawns * 2):
            alloc["spawn farmer"].append(farmers[idx])
            idx += 1

        # Assign two farmers to spawn warrior if possible
        if s_war_spawns:
            for _ in range(2):
                alloc["spawn warrior"].append(farmers[idx])
                idx += 1

        # Remaining farmers go to farm
        for i in range(idx, f_count):
            alloc["farm"].append(farmers[i])

        # Apply assignments
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

        # Ensure any non-Farmer/unknown villagers are assigned (default to farm)
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

        # Warriors: ensure some are attacking
        w_count = len(warriors_in_cave)
        if w_count > 0:
            attack_count = max(1, w_count // 2)
            for i, w in enumerate(warriors_in_cave):
                if i < attack_count:
                    environment.assign_group(w, "attack")
                else:
                    environment.assign_group(w, "cave")

        # Unknown-role villagers in cave: assign to cave as safe default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "cave")