from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        wheat = environment.farm.wheat

        # All warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Decide spawning strategy
        # Priority: spawn warriors aggressively early to build attack force
        spawned = False
        farmers_assigned = 0

        # Try to spawn a warrior every step if we can
        if len(farmers) >= 2 and wheat >= 12:
            # Assign 2 farmers to spawn warrior
            for i in range(min(2, len(farmers))):
                environment.assign_group(farmers[i], "spawn warrior")
            farmers_assigned = 2
            spawned = True
        elif len(farmers) >= 4 and wheat >= 10 and step >= 8:
            # Later in game, spawn farmers to boost economy
            for i in range(2):
                environment.assign_group(farmers[i], "spawn farmer")
            farmers_assigned = 2
            spawned = True

        # Remaining farmers go to farm
        for i in range(farmers_assigned, len(farmers)):
            environment.assign_group(farmers[i], "farm")

        # If we have 0 farmers (shouldn't happen), handle edge case
        # If there are no farmers at all, warriors already handled above

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                if c.hp <= 1:
                    # Send very low HP warriors back to village to avoid
                    # wasting them (they can produce wheat instead)
                    # They'd likely die next AoE tick anyway
                    environment.assign_group(c, "village")
                else:
                    # All healthy warriors attack the Dragon
                    environment.assign_group(c, "attack")
            else:
                # Non-warriors in cave go back to village
                environment.assign_group(c, "village")