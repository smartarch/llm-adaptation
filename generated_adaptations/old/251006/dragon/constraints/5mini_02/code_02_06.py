# Reasoning and strategy:
#
# Failures analysis:
# - The tests reported two assignment errors. Investigation showed a possible cause:
#   we sometimes started assigning villagers to a spawn group without first ensuring that
#   enough unassigned villagers remained to fulfill the required pair (2 villagers). That
#   could leave a spawn group with only a single assigned villager in a step, which the
#   simulator treats as an assignment error.
# - The tests also required that at least a few new farmers and warriors are spawned. The
#   previous policy was sometimes too conservative, producing too few spawns.
#
# Fixes implemented:
# - Before assigning to any spawn group, compute the list of currently unassigned farmers
#   and only proceed if there are enough unassigned farmers to form the required pairs.
# - Increase warrior spawn capacity to up to 3 warriors per step (still bounded by wheat
#   and available farmer pairs) to ensure a steady flow of warriors.
# - Allow farmer spawning at most once every 2 steps (instead of 3) to increase farmer growth.
# - Always assign every component exactly once to a valid group name from group_ids.
# - Use local wheat accounting to avoid over-committing spawn assignments.
#
# These adjustments aim to avoid assignment errors and to produce a healthier number of
# spawned warriors and farmers while still keeping enough farmers farming to sustain wheat.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
import math


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track last farmer spawn step to throttle farmer spawns
        self.last_farmer_spawn_step = -999

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        components: villagers currently in the Village
        groups available: "farm", "cave", "spawn farmer", "spawn warrior"
        """
        # Map available group names (use only if present)
        available = set(group_ids)
        G_FARM = "farm" if "farm" in available else None
        G_CAVE = "cave" if "cave" in available else None
        G_SPAWN_FARMER = "spawn farmer" if "spawn farmer" in available else None
        G_SPAWN_WARRIOR = "spawn warrior" if "spawn warrior" in available else None

        # Partition villagers by role (case-insensitive)
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]

        assigned = set()

        # 1) Send all warriors in Village to the Cave
        for w in warriors:
            # use cave group if available, otherwise fall back to a valid group
            if G_CAVE:
                environment.assign_group(w, G_CAVE)
            else:
                # fallback to farm if cave missing (spec guarantees cave exists)
                environment.assign_group(w, G_FARM if G_FARM else group_ids[0])
            assigned.add(w)

        num_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        if num_farmers == 0:
            return

        # Reserve at least 50% of farmers (rounded up) to farming, keep at least 1 farmer
        reserve_fraction = 0.5
        min_farming = max(1, math.ceil(num_farmers * reserve_fraction))

        # Farmers available to use for spawning (maximum theoretical before checking unassigned)
        spawnable_farmers = max(0, num_farmers - min_farming)

        # Local wheat accounting
        local_wheat = wheat

        # 2) Spawn Warriors: each requires 2 farmers and 12 wheat
        # Allow up to 3 warrior spawns per step (more aggressive to meet tests' spawn expectations)
        spawn_warriors = 0
        if G_SPAWN_WARRIOR and spawnable_farmers >= 2 and local_wheat >= 12:
            max_by_wheat = local_wheat // 12
            max_by_pairs = spawnable_farmers // 2
            possible_spawns = min(max_by_wheat, max_by_pairs)
            spawn_warriors = min(possible_spawns, 3)

        # Before assigning, ensure there are enough unassigned farmers to allocate
        if spawn_warriors > 0:
            to_assign = spawn_warriors * 2
            unassigned_farmers = [f for f in farmers if f not in assigned]
            if len(unassigned_farmers) >= to_assign:
                count = 0
                for f in unassigned_farmers[:to_assign]:
                    environment.assign_group(f, G_SPAWN_WARRIOR)
                    assigned.add(f)
                    count += 1
                local_wheat -= spawn_warriors * 12
                spawnable_farmers = max(0, spawnable_farmers - to_assign)
            else:
                # Not enough free farmers to fulfill warrior spawn pairs; skip warrior spawning this step
                spawn_warriors = 0

        # 3) Spawn Farmers: at most once every 2 steps, each requires 2 farmers and 10 wheat
        spawn_farmer_allowed = (step - self.last_farmer_spawn_step) >= 2
        if G_SPAWN_FARMER and spawn_farmer_allowed and spawnable_farmers >= 2 and local_wheat >= 10:
            unassigned_farmers = [f for f in farmers if f not in assigned]
            if len(unassigned_farmers) >= 2:
                # assign exactly 2 farmers to spawn a new farmer
                for f in unassigned_farmers[:2]:
                    environment.assign_group(f, G_SPAWN_FARMER)
                    assigned.add(f)
                self.last_farmer_spawn_step = step
                local_wheat -= 10
                spawnable_farmers = max(0, spawnable_farmers - 2)
            else:
                # not enough unassigned farmers to form a pair; skip
                pass

        # 4) Any remaining farmers not assigned should farm
        for f in farmers:
            if f not in assigned:
                if G_FARM:
                    environment.assign_group(f, G_FARM)
                else:
                    environment.assign_group(f, group_ids[0])

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
                if G_ATTACK:
                    environment.assign_group(c, G_ATTACK)
                elif G_CAVE:
                    environment.assign_group(c, G_CAVE)
                else:
                    environment.assign_group(c, group_ids[0])
            else:
                # Farmer in cave -> return to village
                if G_VILLAGE:
                    environment.assign_group(c, G_VILLAGE)
                elif G_CAVE:
                    environment.assign_group(c, G_CAVE)
                else:
                    environment.assign_group(c, group_ids[0])