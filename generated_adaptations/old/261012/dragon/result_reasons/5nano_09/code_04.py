from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors currently in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) All Warriors should go to the Cave (attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village by default, but we will opportunistically spawn
        #    new villagers using the available wheat.
        total_farmers = len(farmers)
        if total_farmers == 0:
            # No farmers to spawn from; nothing more to adjust
            return

        wheat = int(getattr(environment.farm, "wheat", 0))

        # Aggressive spawning: compute how many spawns we can attempt this step
        max_farm_spawns = min(total_farmers // 2, wheat // 10)
        spawn_farmers = min(max_farm_spawns, 3)  # cap to avoid over-spawning

        idx = 0
        # Spawn Farmer villagers: each spawn consumes 2 farmers and 10 wheat
        for _ in range(spawn_farmers):
            if idx >= total_farmers:
                break
            c1 = farmers[idx]
            environment.assign_group(c1, "spawn farmer")
            idx += 1
            if idx >= total_farmers:
                break
            c2 = farmers[idx]
            environment.assign_group(c2, "spawn farmer")
            idx += 1

        # Wheat remaining after farmer-spawns
        wheat -= spawn_farmers * 10

        remaining_farmers = total_farmers - idx

        # Warrior spawning: each spawn consumes 2 farmers and 12 wheat
        max_war_spawns = min(remaining_farmers // 2, wheat // 12)
        spawn_warriors = min(max_war_spawns, 3)  # cap to avoid excessive spawns

        for _ in range(spawn_warriors):
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1
            if idx >= total_farmers:
                break
            c = farmers[idx]
            environment.assign_group(c, "spawn warrior")
            idx += 1

        # The rest of the farmers (not used for spawning) stay farming
        while idx < total_farmers:
            c = farmers[idx]
            environment.assign_group(c, "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave: Warriors attack; Farmers go to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")