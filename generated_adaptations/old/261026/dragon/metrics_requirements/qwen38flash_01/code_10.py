import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers  = [c for c in components if c.role == "Farmer"]

        # 1. Every warrior must head to the cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        if not farmers:
            return

        # 2. Reserve at least 2 farmers for farming (wheat engine).
        min_farmers = 2
        farm_pool   = farmers[:min_farmers]
        excess      = farmers[min_farmers:]

        # 3. Pair excess farmers into "spawn warrior" (priority: damage).
        #    Only pairs work (need exactly 2 per spawn).
        num_pairs = len(excess) // 2
        spawn_pool = excess[:num_pairs * 2]
        leftover   = excess[num_pairs * 2:]

        # 4. Assign: farming first.
        for f in farm_pool:
            environment.assign_group(f, "farm")
        # Odd leftover also farms so it doesn't sit idle.
        for f in leftover:
            environment.assign_group(f, "farm")

        # 5. Spawn pairs – always attempt, no wheat gate.
        for f in spawn_pool:
            environment.assign_group(f, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")