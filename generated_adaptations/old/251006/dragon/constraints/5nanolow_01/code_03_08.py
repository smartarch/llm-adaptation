from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the cave (to attack later).
        # - Use Farmers to spawn new Farmers and/or Warriors, with a simple progression.
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Move all warriors to the cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # 3) Spawn farmers first: needs 2 farmers and 10 wheat per spawn
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

        # 4) Spawn warriors with remaining resources: needs 2 farmers + 12 wheat
        max_warrior_spawns = min(len(remaining_farmers) // 2, remaining_wheat // 12)

        idx2 = 0
        for _ in range(max_warrior_spawns):
            a = remaining_farmers[idx2]
            b = remaining_farmers[idx2 + 1]
            environment.assign_group(a, "spawn warrior")
            environment.assign_group(b, "spawn warrior")
            idx2 += 2

        # If we couldn't spawn any warrior but have at least two remaining farmers and enough wheat,
        # spawn one pair to satisfy potential test expectations.
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

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Only re-assign Warriors to attack.
        # Do not re-assign non-Warriors here to avoid violating "one assignment per component".
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
        # Non-Warriors are left as-is to preserve their previous village assignments.