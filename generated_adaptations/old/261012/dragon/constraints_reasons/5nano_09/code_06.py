from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Move all existing Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # Remaining farmers (still in village)
        remaining_farmers = [f for f in farmers]

        # Current wheat available
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 2) Fallback: ensure at least one Warrior early if none exist
        if len(warriors) == 0 and step <= 15 and len(remaining_farmers) >= 2 and wheat >= 12:
            a = remaining_farmers.pop(0)
            b = remaining_farmers.pop(0)
            environment.assign_group(a, "spawn warrior")
            environment.assign_group(b, "spawn warrior")
            wheat -= 12

        # 3) Step-aware spawning strategy
        if step <= 7:
            # Aggressively spawn Warriors first
            max_war_spawns = min(len(remaining_farmers) // 2, wheat // 12)
            for _ in range(max_war_spawns):
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                wheat -= 12

            # Then spawn Farmers if possible
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10)
            for _ in range(max_farm_spawns):
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                wheat -= 10
        else:
            # Later steps: balance spawns
            max_farm_spawns = min(len(remaining_farmers) // 2, wheat // 10)
            for _ in range(max_farm_spawns):
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                wheat -= 10

            max_war_spawns = min(len(remaining_farmers) // 2, wheat // 12)
            for _ in range(max_war_spawns):
                a = remaining_farmers.pop(0)
                b = remaining_farmers.pop(0)
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                wheat -= 12

        # 4) Remaining farmers stay in the village and farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")