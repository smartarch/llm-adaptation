from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # 1) Enforce rule: move all Warriors in Village to the Cave to Attack
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # 2) Collect Farmers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]

        # 3) Read current wheat in the Farm
        wheat = int(getattr(environment.farm, "wheat", 0))

        # 4) Cadence-based spawning decisions (conservative yet progressive)
        spawn_farmers_to_assign = 0
        spawn_warriors_to_assign = 0

        # Spawn 2 farmers every 3 steps if possible (requires 2 farmers and >=10 wheat)
        if step % 3 == 0 and len(farmers) >= 2 and wheat >= 10:
            spawn_farmers_to_assign = 2

        # After allocating for farm spawns, check if we can spawn 2 warriors
        remaining_farmers_after_farm_spawn = len(farmers) - spawn_farmers_to_assign
        if step % 5 == 0 and remaining_farmers_after_farm_spawn >= 2 and wheat >= 12:
            spawn_warriors_to_assign = 2

        # 5) Assign groups among Farmers
        # First 2 farmers -> spawn farmer
        # Next 2 farmers -> spawn warrior
        for idx, f in enumerate(farmers):
            if idx < spawn_farmers_to_assign:
                environment.assign_group(f, "spawn farmer")
            elif idx < spawn_farmers_to_assign + spawn_warriors_to_assign:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: keep Warriors in "attack"; Farmers go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")