from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Robust and consistent strategy:
        # - Move all Warriors to the cave (attack group in cave context).
        # - Farmers stay in village and are allocated to:
        #     spawn farmer (in pairs, costing 10 wheat),
        #     spawn warrior (in pairs, costing 12 wheat),
        #     or farm (default for any leftover).
        # - Ensure every farmer is assigned to exactly one group.
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All warriors go to the cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # 3) Spawn farmers first if possible
        spawn_farmers = min(len(farmers) // 2, wheat // 10)

        idx = 0
        for _ in range(spawn_farmers):
            a = farmers[idx]
            b = farmers[idx + 1]
            environment.assign_group(a, "spawn farmer")
            environment.assign_group(b, "spawn farmer")
            idx += 2

        remaining_farmers = farmers[idx:]
        remaining_wheat = wheat - spawn_farmers * 10

        # 4) Spawn warriors with remaining resources (2 farmers + 12 wheat)
        max_warrior_spawns = min(len(remaining_farmers) // 2, remaining_wheat // 12)

        idx2 = 0
        for _ in range(max_warrior_spawns):
            a = remaining_farmers[idx2]
            b = remaining_farmers[idx2 + 1]
            environment.assign_group(a, "spawn warrior")
            environment.assign_group(b, "spawn warrior")
            idx2 += 2

        # If we couldn't spawn any warrior but have enough resources and at least 2 farmers left, spawn one pair
        if max_warrior_spawns == 0 and len(remaining_farmers) - idx2 >= 2 and remaining_wheat >= 12:
            a = remaining_farmers[idx2]
            b = remaining_farmers[idx2 + 1]
            environment.assign_group(a, "spawn warrior")
            environment.assign_group(b, "spawn warrior")
            idx2 += 2
            remaining_wheat -= 12

        # 5) Remaining farmers go to farming
        for f in remaining_farmers[idx2:]:
            environment.assign_group(f, "farm")

        # All farmers are assigned exactly once; if there are no farmers, nothing else happens.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave:
        # - Warriors are assigned to attack.
        # - Farmers are assigned to cave (stay in cave or move back as needed).
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")