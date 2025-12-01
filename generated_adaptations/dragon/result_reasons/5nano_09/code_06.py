from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all Warriors to the Cave (to attack early)
        for w in warriors:
            environment.assign_group(w, "cave")

        total_farmers = len(farmers)
        if total_farmers == 0:
            # Nothing to spawn; all farmers absent
            return

        # Wheat available
        wheat = int(getattr(environment.farm, "wheat", 0))

        # 2) Aggressively spawn Warriors first (cap to avoid over-spawning)
        max_war_spawns = min(total_farmers // 2, wheat // 12)
        spawn_warriors = min(max_war_spawns, 4)  # cap per step for stability

        idx = 0
        for _ in range(spawn_warriors):
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1

        wheat -= spawn_warriors * 12
        remaining_farmers = total_farmers - idx

        # 3) Spawn Farmers with remaining resources (cap to avoid runaway)
        max_farm_spawns = min(remaining_farmers // 2, wheat // 10)
        spawn_farmers = min(max_farm_spawns, 3)  # cap per step

        for _ in range(spawn_farmers):
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            idx += 1
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn farmer")
            idx += 1

        wheat -= spawn_farmers * 10

        # 4) Remaining farmers stay farming
        while idx < total_farmers:
            c = farmers[idx]
            environment.assign_group(c, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack; Farmers go to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")