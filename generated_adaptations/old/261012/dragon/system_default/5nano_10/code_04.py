from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all warriors to the cave (to attack the Dragon)
        for w in warriors:
            environment.assign_group(w, "cave")

        nf = len(farmers)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 2) Aggressive, resource-aware spawning
        # How many Farmers can we spawn this turn?
        s_f_spawn = min(nf // 2, wheat // 10)

        # Wheat left after Farmer spawns
        wheat_left = wheat - s_f_spawn * 10

        # Remaining farmers after allocating for Farmer spawns
        nf_remaining = nf - s_f_spawn * 2

        # How many Warriors can we spawn with the remaining resources
        s_w_spawn = 0
        if nf_remaining >= 2:
            s_w_spawn = min(nf_remaining // 2, wheat_left // 12)

        # Assign farming/spawn groups based on the computed spawn counts
        idx = 0
        # Spawn Farmers: 2 farmers per spawn unit in "spawn farmer"
        for _ in range(s_f_spawn):
            environment.assign_group(farmers[idx], "spawn farmer")
            environment.assign_group(farmers[idx + 1], "spawn farmer")
            idx += 2

        # Spawn Warriors: 2 farmers per spawn unit in "spawn warrior"
        for _ in range(s_w_spawn):
            environment.assign_group(farmers[idx], "spawn warrior")
            environment.assign_group(farmers[idx + 1], "spawn warrior")
            idx += 2

        # Remaining farmers (not used in spawns) go to farming
        while idx < nf:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack; Farmers should head back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")