from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers currently in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Rule: All warriors should go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farm wheat resource
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Spawn strategy for farmers
        f_count = len(farmers)

        # Number of pairs of farmers to assign to "spawn farmer"
        # Each pair yields 1 new Farmer, costs 10 wheat
        s_farm_spawns = min(f_count // 2, max(0, wheat // 10))
        s_farmers_assigned_to_spawn = s_farm_spawns * 2

        # Remaining wheat after farmer spawns
        wheat_rem_after_farm = max(0, wheat - s_farm_spawns * 10)

        # Remaining farmers after assigning to farmer-spawn
        remaining_farmers = f_count - s_farmers_assigned_to_spawn

        # Number of pairs of farmers to assign to "spawn warrior"
        # Each pair yields 1 new Warrior, costs 12 wheat
        s_war_spawns = min(remaining_farmers // 2, max(0, wheat_rem_after_farm // 12))
        s_warriors_assigned_to_spawn = s_war_spawns * 2

        # Build groups for farmers
        alloc = {
            "farm": [],
            "spawn farmer": [],
            "spawn warrior": [],
        }

        idx = 0
        # Assign to spawn farmer first
        for i in range(s_farmers_assigned_to_spawn):
            alloc["spawn farmer"].append(farmers[idx])
            idx += 1

        # Assign to spawn warrior next
        for i in range(s_warriors_assigned_to_spawn):
            alloc["spawn warrior"].append(farmers[idx])
            idx += 1

        # Remaining farmers go to farm
        for i in range(idx, f_count):
            alloc["farm"].append(farmers[i])

        # Now apply the assignments
        for c in alloc["farm"]:
            environment.assign_group(c, "farm")
        for c in alloc["spawn farmer"]:
            environment.assign_group(c, "spawn farmer")
        for c in alloc["spawn warrior"]:
            environment.assign_group(c, "spawn warrior")

        # If there are any other components (e.g., non-Farmer), we do not reassign them here.
        # The Warriors have already been moved to the cave above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Divide villagers currently in the Cave
        farmers_in_cave = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors_in_cave = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Farmers should go to the Village
        for f in farmers_in_cave:
            environment.assign_group(f, "village")

        # For warriors in the cave, ensure sufficient attackers
        w_count = len(warriors_in_cave)
        if w_count > 0:
            # Ensure at least one attacker and try to have about half attack
            attack_count = max(1, w_count // 2)
            attack_count = min(attack_count, w_count)

            for i, w in enumerate(warriors_in_cave):
                if i < attack_count:
                    environment.assign_group(w, "attack")
                else:
                    environment.assign_group(w, "cave")
        # If there are no warriors in cave, nothing to assign to attack this step