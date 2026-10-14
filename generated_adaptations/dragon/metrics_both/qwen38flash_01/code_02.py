from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # No farmers means nothing to assign in village for farming/spawning
        if len(farmers) == 0:
            return

        wheat = environment.farm.wheat
        available_farmers = list(farmers)

        # Decide how many pairs to allocate to spawning
        spawn_warrior_count = 0
        spawn_farmer_count = 0
        max_pairs = len(available_farmers) // 2

        if step < 8:
            # Early game: aggressively spawn warriors for damage
            if wheat >= 12 and max_pairs >= 1:
                spawn_warrior_count = 1
            if step >= 4 and wheat >= 10 and (max_pairs - spawn_warrior_count) >= 1:
                spawn_farmer_count = 1
        elif step < 15:
            # Mid game: keep spawning warriors, start adding farmers
            if wheat >= 12 and max_pairs >= 1:
                spawn_warrior_count = 1
            if wheat >= 10 and (max_pairs - spawn_warrior_count) >= 1:
                spawn_farmer_count = 1
            # Try to get a second warrior spawned if wheat allows
            if wheat >= 24 and (max_pairs - spawn_warrior_count - spawn_farmer_count) >= 1:
                spawn_warrior_count += 1
        elif step < 22:
            # Late-mid: balanced spawning but ensure warriors keep coming
            if wheat >= 12 and max_pairs >= 1:
                spawn_warrior_count = 1
            if wheat >= 10 and (max_pairs - spawn_warrior_count) >= 1:
                spawn_farmer_count = 1
        else:
            # End game: reduce spawning, maximize farming for any remaining needs
            if wheat >= 12 and max_pairs >= 2:
                spawn_warrior_count = 1
            if wheat >= 10 and max_pairs >= 2:
                spawn_farmer_count = 1

        # Assign farmers to spawn warrior pairs
        idx = 0
        for _ in range(spawn_warrior_count):
            if idx + 1 < len(available_farmers):
                environment.assign_group(available_farmers[idx], "spawn warrior")
                environment.assign_group(available_farmers[idx + 1], "spawn warrior")
                idx += 2

        # Assign farmers to spawn farmer pairs
        for _ in range(spawn_farmer_count):
            if idx + 1 < len(available_farmers):
                environment.assign_group(available_farmers[idx], "spawn farmer")
                environment.assign_group(available_farmers[idx + 1], "spawn farmer")
                idx += 2

        # Remaining farmers produce wheat
        while idx < len(available_farmers):
            environment.assign_group(available_farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                # All warriors attack the Dragon
                environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers should not be in the cave; send them back to village
                environment.assign_group(c, "village")
            else:
                # Default: attack
                environment.assign_group(c, "attack")