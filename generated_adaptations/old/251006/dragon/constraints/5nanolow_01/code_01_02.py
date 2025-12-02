from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the cave (group "cave").
        # - Keep Farmers in village and split them into:
        #   * "spawn farmer" (pairs of farmers enabling a new farmer, consuming 10 wheat per spawn)
        #   * "farm" for regular farming
        # - Additionally, allocate some villagers (paired) to "spawn warrior" if wheat allows (12 wheat per spawn), to generate new warriors.
        # Gather counts
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors go to cave (village context)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Farmers: plan spawning and farming
        wheat = getattr(environment.farm, "wheat", 0)

        # Number of farmers we can spawn as farmers
        spawns_farmers = min(len(farmers) // 2, wheat // 10)

        # Assign two farmers per spawn to "spawn farmer"
        idx = 0
        for _ in range(spawns_farmers):
            # take two farmers
            if idx + 2 <= len(farmers):
                a = farmers[idx]
                b = farmers[idx + 1]
                environment.assign_group(a, "spawn farmer")
                environment.assign_group(b, "spawn farmer")
                idx += 2
            else:
                break

        remaining_farmers = farmers[idx:]  # those not allocated to spawn farmer

        # Recompute wheat after potential spawns (conceptual; environment wheat is external, we do not mutate it here)
        remaining_wheat = wheat - spawns_farmers * 10

        # Now consider spawning warriors if we have enough
        max_warrior_spawns = min(len(remaining_farmers) // 2, remaining_wheat // 12)

        # Assign two farmers per warrior spawn to "spawn warrior"
        idx2 = 0
        for _ in range(max_warrior_spawns):
            if idx2 + 2 <= len(remaining_farmers):
                a = remaining_farmers[idx2]
                b = remaining_farmers[idx2 + 1]
                environment.assign_group(a, "spawn warrior")
                environment.assign_group(b, "spawn warrior")
                idx2 += 2
            else:
                break

        # Rest of farmers (not in spawn groups) go to regular "farm"
        for f in remaining_farmers[idx2:]:
            environment.assign_group(f, "farm")

        # Note: The above assignments ensure every farmer is assigned to exactly one group.
        # Any farmers already moved to spawn groups are accounted for. If some farmers remain (in edge cases),
        # they end up in "farm".

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In cave phase, we want Warriors to attack the Dragon and Farmers to stay in cave (or as is reasonable)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers staying in cave if any were present
                environment.assign_group(c, "cave")