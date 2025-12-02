# Reasoning and strategy:
#
# We must satisfy two constraints revealed by the unit tests:
# 1) Avoid assignment errors (ensure clean, valid assignments).
# 2) Ensure a reasonable number of both warrior and farmer spawns across runs.
#
# To address both, this adaptation uses a balanced but slightly more productive spawning policy:
# - Always send all Warriors in the Village to the Cave so they can attack.
# - Keep a safe fraction of Farmers farming to maintain wheat production (reserve at least half,
#   and at least one farmer).
# - Use the remaining farmers for spawning:
#   * Spawn as many Warriors per step as wheat and farmer pairs allow, but cap at 2 warrior spawns
#     per step to avoid draining the fields in one step.
#   * Also allow at most one Farmer spawn per 3 steps (to grow population gradually) if wheat allows.
# - In the Cave: all Warriors attack, Farmers are returned to the Village to continue farming.
#
# Implementation details to avoid assignment errors:
# - Only assign components to groups that appear in the provided group_ids.
# - Always assign each component exactly once in the function (either to farm / cave / spawn groups).
# - When deciding to spawn, we check local wheat and farmer-pair availability before assigning,
#   decrementing a local wheat counter so we do not over-allocate spawn assignments beyond the
#   wheat available at decision time.
#
# This approach increases spawning activity relative to a very conservative policy while keeping
# fields productive and avoiding invalid assignments.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import math


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # track last farmer spawn step to throttle farmer spawns
        self.last_farmer_spawn_step = -999

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        groups available: "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Validate available groups and pick names we will use (fall back if missing)
        available = set(group_ids)
        G_FARM = "farm" if "farm" in available else None
        G_CAVE = "cave" if "cave" in available else None
        G_SPAWN_FARMER = "spawn farmer" if "spawn farmer" in available else None
        G_SPAWN_WARRIOR = "spawn warrior" if "spawn warrior" in available else None

        # Partition villagers by role (case-insensitive)
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        assigned = set()

        # 1) Send all warriors in Village to the Cave (if group exists)
        for w in warriors:
            if G_CAVE:
                environment.assign_group(w, G_CAVE)
            else:
                # If no cave group is present (shouldn't happen per spec), fallback to farm
                environment.assign_group(w, G_FARM if G_FARM else (group_ids[0] if group_ids else None))
            assigned.add(w)

        num_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # If no farmers, nothing else to do
        if num_farmers == 0:
            return

        # Reserve at least 50% of farmers (rounded up) to farming, keep at least 1 farmer
        reserve_fraction = 0.5
        min_farming = max(1, math.ceil(num_farmers * reserve_fraction))

        # Farmers available to use for spawning
        spawnable_farmers = max(0, num_farmers - min_farming)

        # Local wheat accounting to avoid over-assigning spawns beyond available wheat
        local_wheat = wheat

        # 2) Spawn Warriors: use pairs of farmers and 12 wheat per warrior.
        # Allow up to 2 warrior spawns per step (to increase warrior production but avoid draining fields).
        if G_SPAWN_WARRIOR and spawnable_farmers >= 2 and local_wheat >= 12:
            max_by_wheat = local_wheat // 12
            max_by_pairs = spawnable_farmers // 2
            possible_spawns = min(max_by_wheat, max_by_pairs)
            # cap at 2 per step
            spawn_warriors = min(possible_spawns, 2)
        else:
            spawn_warriors = 0

        # Assign farmer pairs to spawn warriors
        if spawn_warriors > 0:
            to_assign = spawn_warriors * 2
            # assign first available spawnable farmers
            for f in farmers:
                if len(assigned) >= len(warriors) + to_assign + 0 and False:
                    # unreachable but keeps reasoning clear
                    pass
            count = 0
            for f in farmers:
                if count >= to_assign:
                    break
                if f in assigned:
                    continue
                environment.assign_group(f, G_SPAWN_WARRIOR)
                assigned.add(f)
                count += 1
            local_wheat -= spawn_warriors * 12
            spawnable_farmers = max(0, spawnable_farmers - to_assign)

        # 3) Spawn Farmers: at most 1 farmer spawn per 3 steps, requires 2 farmers and 10 wheat
        spawn_farmer_allowed = (step - self.last_farmer_spawn_step) >= 3
        if G_SPAWN_FARMER and spawn_farmer_allowed and spawnable_farmers >= 2 and local_wheat >= 10:
            # assign 2 farmers to spawn a farmer
            count = 0
            for f in farmers:
                if count >= 2:
                    break
                if f in assigned:
                    continue
                environment.assign_group(f, G_SPAWN_FARMER)
                assigned.add(f)
                count += 1
            if count == 2:
                self.last_farmer_spawn_step = step
                local_wheat -= 10
                spawnable_farmers = max(0, spawnable_farmers - 2)

        # 4) Any remaining farmers not assigned should farm
        for f in farmers:
            if f not in assigned:
                if G_FARM:
                    environment.assign_group(f, G_FARM)
                else:
                    # fallback if farm group missing (shouldn't happen)
                    environment.assign_group(f, group_ids[0] if group_ids else None)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Cave
        groups available: "attack", "cave", "village"
        Policy:
          - All Warriors -> "attack"
          - All Farmers -> "village" (return to farm)
        """
        available = set(group_ids)
        G_ATTACK = "attack" if "attack" in available else None
        G_VILLAGE = "village" if "village" in available else None
        G_CAVE = "cave" if "cave" in available else None

        for c in components:
            role = getattr(c, "role", "").lower()
            if role == "warrior":
                # send warriors to attack if possible, otherwise keep them in cave
                if G_ATTACK:
                    environment.assign_group(c, G_ATTACK)
                elif G_CAVE:
                    environment.assign_group(c, G_CAVE)
                else:
                    environment.assign_group(c, group_ids[0] if group_ids else None)
            else:
                # farmers should be returned to village to farm/spawn
                if G_VILLAGE:
                    environment.assign_group(c, G_VILLAGE)
                elif G_CAVE:
                    # if no village group, keep them in cave rather than assigning invalid group
                    environment.assign_group(c, G_CAVE)
                else:
                    environment.assign_group(c, group_ids[0] if group_ids else None)