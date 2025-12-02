from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Step-aware escalation with budgeted spawning
        if not components:
            return

        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Gradually move Warriors to the Cave
        # Increase the number moved per step as steps progress
        if len(warriors) > 0:
            move_cap = min(max(1, step // 2 + 1), len(warriors))  # 1,1,2,2,3,3,... growth
            for i in range(move_cap):
                environment.assign_group(warriors[i], "cave")

        # 2) Keep Farmers in Village (farm by default)
        for c in farmers:
            environment.assign_group(c, "farm")

        # 3) Aggressive, budgeted spawning (per step)
        wheat = getattr(environment.farm, "wheat", 0)

        # Farmer spawns: need 2 farmers and 10 wheat per spawn
        n_farm_spawns = min(len(farmers) // 2, wheat // 10)
        # Cap per-step spawns to avoid over-spawning in one step
        n_farm_spawns = min(n_farm_spawns, 3)

        # Trigger farmer spawns using disjoint farmer pairs
        for i in range(n_farm_spawns):
            c1 = farmers[2 * i]
            c2 = farmers[2 * i + 1]
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")

        # Update wheat budget after farmer spawns
        wheat_after_farm = wheat - n_farm_spawns * 10
        idx_after_farm = 2 * n_farm_spawns

        remaining_farmers_for_war = len(farmers) - idx_after_farm

        # Warrior spawns: need 2 farmers and 12 wheat per spawn
        n_war_spawns = min(remaining_farmers_for_war // 2, wheat_after_farm // 12)
        n_war_spawns = min(n_war_spawns, 2)  # cap per-step to avoid over-spawning

        # Trigger warrior spawns using disjoint farmer pairs after farmers for farmer-spawns
        for i in range(n_war_spawns):
            c1 = farmers[idx_after_farm + 2 * i]
            c2 = farmers[idx_after_farm + 2 * i + 1]
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave:
        # - All Warriors should attack (group "attack").
        # - All Farmers should go back to the Village (group "village").
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")