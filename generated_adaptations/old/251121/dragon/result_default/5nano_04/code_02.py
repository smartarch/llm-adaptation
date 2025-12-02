from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in village and farm
        - cave: go to cave (for Warriors, to attack)
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy:
        - All Warriors go to cave.
        - Farmers are allocated to spawn groups first based on available wheat, then the rest farm.
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        total_farmers = len(farmers)
        # Current wheat in the Farm
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many pairs we can use for spawning farmers
        pairs_farm = min(total_farmers // 2, wheat // 10)
        spawn_farm_count = 2 * pairs_farm

        remaining_farmers_after_farm_spawns = total_farmers - spawn_farm_count
        wheat_after_farm_spawns = wheat - (pairs_farm * 10)

        # Determine how many pairs we can use for spawning warriors from remaining farmers
        pairs_war = min(remaining_farmers_after_farm_spawns // 2, wheat_after_farm_spawns // 12)
        spawn_war_count = 2 * pairs_war

        # The rest of the farmers will farm
        farm_count = remaining_farmers_after_farm_spawns - spawn_war_count

        # Assign farmers to groups
        # 1) Spawn farmer
        for i in range(spawn_farm_count):
            environment.assign_group(farmers[i], "spawn farmer")

        # 2) Spawn warrior (these farmers will help spawn warriors)
        for i in range(spawn_farm_count, spawn_farm_count + spawn_war_count):
            environment.assign_group(farmers[i], "spawn warrior")

        # 3) Farm (remaining farmers)
        for i in range(spawn_farm_count + spawn_war_count, total_farmers):
            environment.assign_group(farmers[i], "farm")

        # Warriors go to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village

        Strategy:
        - All Warriors should attack the Dragon (group "attack").
        - Farmers should stay in the Village (group "village") to continue farming/spawning.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")