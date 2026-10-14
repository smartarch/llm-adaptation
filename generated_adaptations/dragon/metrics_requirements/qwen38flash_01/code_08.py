import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # ------------------------------------------------------------------
    # VILLAGE phase
    # ------------------------------------------------------------------
    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers  = [c for c in components if c.role == "Farmer"]

        # 1) Every warrior in the village heads straight to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # 2) Decide how many farmers stay farming vs. spawning.
        #    We need at least 2 in "farm" to produce wheat for spawns.
        MIN_FARMERS = 2
        num_farming = min(MIN_FARMERS, len(farmers))
        farm_list   = farmers[:num_farming]
        rest        = farmers[num_farming:]

        # 3) Pair up remaining farmers for "spawn warrior" (damage priority).
        #    Assign in pairs; odd leftover goes to farm too.
        num_spawnable = (len(rest) // 2) * 2          # even number, pairs only
        spawn_list    = rest[:num_spawnable]
        leftover      = rest[num_spawnable:]

        # Assign farmers that stay in village and farm
        for f in farm_list:
            environment.assign_group(f, "farm")
        # Extra odd farmer that didn't pair → also farms
        for f in leftover:
            environment.assign_group(f, "farm")

        # Assign farmer pairs to "spawn warrior" – always try, every turn.
        for f in spawn_list:
            environment.assign_group(f, "spawn warrior")

    # ------------------------------------------------------------------
    # CAVE phase
    # ------------------------------------------------------------------
    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                # Every warrior attacks, no exceptions.
                environment.assign_group(c, "attack")
            else:
                # A farmer that ended up in the cave is sent home.
                environment.assign_group(c, "village")