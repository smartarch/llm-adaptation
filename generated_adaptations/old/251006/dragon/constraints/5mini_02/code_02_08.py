# Reasoning and strategy:
#
# The failing tests reported assignment errors and insufficient spawning. To fix this reliably:
# - Ensure any assignment to a spawn group is done in pairs (never assign a single villager to a spawn
#   group), because spawn semantics use pairs and assigning a single villager to a spawn group can be
#   considered an error by the evaluator.
# - Make the spawning policy productive enough: allow up to 3 warrior spawns per step (bounded by
#   wheat and available farmer pairs) and allow farmer spawns every 2 steps when resources permit.
# - Always assign every component exactly once and only to valid group names from the provided
#   group_ids.
#
# Implementation:
# - In the village: send all warriors to "cave". For farmers, maintain at least 50% farming (min 1),
#   then from the remainder allocate pairs to spawn warriors (up to 3 per step), then possibly allocate
#   one pair to spawn a farmer (throttled). Any remaining farmers farm.
# - In the cave: warriors -> "attack"; farmers -> "village".
#
# This ensures spawn groups always receive pairs, avoids partial/spurious spawn assignments, and
# increases total spawned villagers to satisfy the tests.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import math


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_farmer_spawn_step = -999

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Determine available group names (use only valid ones)
        available = set(group_ids)
        G_FARM = "farm" if "farm" in available else group_ids[0]
        G_CAVE = "cave" if "cave" in available else group_ids[0]
        G_SPAWN_FARMER = "spawn farmer" if "spawn farmer" in available else None
        G_SPAWN_WARRIOR = "spawn warrior" if "spawn warrior" in available else None

        # Partition villagers by role
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        # Assign all warriors to go to the Cave
        for w in warriors:
            environment.assign_group(w, G_CAVE)

        num_farmers = len(farmers)
        if num_farmers == 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Reserve at least 50% of farmers for farming (rounded up), at least 1
        min_farming = max(1, math.ceil(num_farmers * 0.5))
        # Build list of farmers available for spawn assignment (unassigned yet)
        unassigned = list(farmers)  # we'll pop from this as we assign spawns
        # We'll ensure we leave at least min_farming farmers at the end
        spare_limit = len(unassigned) - min_farming
        spare_limit = max(0, spare_limit)

        local_wheat = wheat

        # Decide on warrior spawns: require 2 farmers and 12 wheat; allow up to 3 per step
        max_warrior_by_wheat = local_wheat // 12
        max_warrior_by_pairs = spare_limit // 2
        warrior_spawns = min(max_warrior_by_wheat, max_warrior_by_pairs, 3)

        assigned_count = 0
        if G_SPAWN_WARRIOR and warrior_spawns > 0:
            # Assign in pairs: for each spawn, pop two farmers
            for _ in range(warrior_spawns):
                if len(unassigned) - assigned_count < 2:
                    break
                # assign two farmers
                f1 = unassigned[assigned_count]
                f2 = unassigned[assigned_count + 1]
                environment.assign_group(f1, G_SPAWN_WARRIOR)
                environment.assign_group(f2, G_SPAWN_WARRIOR)
                assigned_count += 2
                local_wheat -= 12

        # Update spare_limit after warrior assignments
        remaining_unassigned = unassigned[assigned_count:]
        remaining_spare = len(remaining_unassigned) - min_farming
        remaining_spare = max(0, remaining_spare)

        # Decide on farmer spawn: at most once every 2 steps, needs 2 farmers and 10 wheat
        if G_SPAWN_FARMER and (step - self.last_farmer_spawn_step) >= 2 and remaining_spare >= 2 and local_wheat >= 10:
            # assign 2 farmers to spawn farmer
            f1 = remaining_unassigned[0]
            f2 = remaining_unassigned[1]
            environment.assign_group(f1, G_SPAWN_FARMER)
            environment.assign_group(f2, G_SPAWN_FARMER)
            # mark them as assigned by advancing assigned_count
            assigned_count += 2
            local_wheat -= 10
            self.last_farmer_spawn_step = step

        # Now assign the rest to farm; construct final assigned set to avoid re-assign
        # Note: farmers earlier in list before index assigned_count have been assigned to spawn groups.
        for idx, f in enumerate(unassigned):
            if idx < assigned_count:
                # already assigned to spawn group
                continue
            # rest farm
            environment.assign_group(f, G_FARM)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        available = set(group_ids)
        G_ATTACK = "attack" if "attack" in available else group_ids[0]
        G_VILLAGE = "village" if "village" in available else group_ids[0]
        G_CAVE = "cave" if "cave" in available else group_ids[0]

        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                environment.assign_group(c, G_ATTACK)
            else:
                # send farmers back to the village to farm/spawn
                environment.assign_group(c, G_VILLAGE)