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

        # 2) Aggressive, resource-aware spawning (prioritize Warrior spawns first)
        # Warriors: need 2 farmers and 12 wheat per Warrior spawn
        s_w_spawn = min(nf // 2, wheat // 12)

        idx = 0
        # Spawn Warriors: 2 farmers per spawn unit
        for _ in range(s_w_spawn):
            if idx + 1 < nf:
                environment.assign_group(farmers[idx], "spawn warrior")
                environment.assign_group(farmers[idx + 1], "spawn warrior")
                idx += 2

        # Wheat and farmers left after Warrior spawns
        wheat_left = wheat - s_w_spawn * 12
        nf_remaining = nf - s_w_spawn * 2

        # Farmers: need 2 farmers and 10 wheat per Farmer spawn
        s_f_spawn = min(nf_remaining // 2, wheat_left // 10)

        # Spawn Farmers: 2 farmers per spawn unit
        for _ in range(s_f_spawn):
            if idx + 1 < nf:
                environment.assign_group(farmers[idx], "spawn farmer")
                environment.assign_group(farmers[idx + 1], "spawn farmer")
                idx += 2

        # Remaining farmers go to farming
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