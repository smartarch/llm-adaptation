from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Track assignments to prevent duplicates
        assigned = {}

        # Step 1: Warriors should head to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")
            assigned[c] = "cave"

        # Step 2: Farmers logic - spawn as much as possible while ensuring unique assignments
        wheat = getattr(environment.farm, "wheat", 0)

        # Build list of unassigned farmers
        unassigned_farmers = [f for f in farmers if f not in assigned]

        # Try to spawn at least one warrior if possible (needs 2 farmers and 12 wheat)
        if len(unassigned_farmers) >= 2 and wheat >= 12:
            c1 = unassigned_farmers[0]
            c2 = unassigned_farmers[1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            assigned[c1] = "spawn warrior"
            assigned[c2] = "spawn warrior"
            wheat -= 12
            # Update unassigned farmers
            unassigned_farmers = [f for f in unassigned_farmers if f not in (c1, c2)]

        # Now spawn farmers if possible with remaining wheat
        max_farm_spawns = min(len(unassigned_farmers) // 2, wheat // 10 if wheat >= 10 else 0)
        spawn_farmers_count = max_farm_spawns * 2
        for i in range(spawn_farmers_count):
            c = unassigned_farmers[i]
            environment.assign_group(c, "spawn farmer")
            assigned[c] = "spawn farmer"

        wheat -= max_farm_spawns * 10

        # Remaining farmers go to farming
        remaining_farmers = [f for f in unassigned_farmers if f not in assigned]
        for c in remaining_farmers:
            environment.assign_group(c, "farm")
            assigned[c] = "farm"

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, Warriors attack, Farmers go to village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")