from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Aggressive spawning planning among farmers in the village
        remaining_farmers = [f for f in farmers]  # farmers still in village

        # Current wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Helpers to spawn groups (modify wheat via nonlocal)
        def do_spawn_farm(fr_list, count):
            nonlocal wheat
            spawned = []
            for _ in range(count):
                if len(fr_list) >= 2 and wheat >= 10:
                    a = fr_list.pop(0)
                    b = fr_list.pop(0)
                    environment.assign_group(a, "spawn farmer")
                    environment.assign_group(b, "spawn farmer")
                    spawned.extend([a, b])
                    wheat -= 10
                else:
                    break
            return spawned

        def do_spawn_war(fr_list, count):
            nonlocal wheat
            spawned = []
            for _ in range(count):
                if len(fr_list) >= 2 and wheat >= 12:
                    a = fr_list.pop(0)
                    b = fr_list.pop(0)
                    environment.assign_group(a, "spawn warrior")
                    environment.assign_group(b, "spawn warrior")
                    spawned.extend([a, b])
                    wheat -= 12
                else:
                    break
            return spawned

        # Step-aware spawning strategy
        if step <= 7:
            # Prioritize Warriors to maximize early DPS
            max_war_spawns = min(len(remaining_farmers) // 2, wheat // 12)
            if max_war_spawns > 0:
                do_spawn_war(remaining_farmers, max_war_spawns)

            # Then spawn farmers if wheat allows
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10)
            if max_farm_spawns > 0:
                do_spawn_farm(remaining_farmers, max_farm_spawns)
        else:
            # In later steps, balance spawns: prefer farmers if wheat is plentiful
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10)
            if max_farm_spawns > 0:
                do_spawn_farm(remaining_farmers, max_farm_spawns)

            # If still possible and wheat allows, spawn additional warriors
            max_war_spawns = min(len(remaining_farmers) // 2, wheat // 12)
            if max_war_spawns > 0:
                do_spawn_war(remaining_farmers, max_war_spawns)

        # 3) Remaining farmers stay in the village to farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")