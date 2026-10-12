from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Villagers in the Village:
        - Move all Warriors to the Cave (cave) for attack
        - Spawn Warriors as soon as possible: 2 farmers + 12 wheat -> 1 Warrior
        - Then spawn Farmers with remaining wheat: 2 farmers + 10 wheat -> 1 Farmer
        - All other Farmers stay in the Village and farm
        Groups:
        - "farm": Stay in the Village and farm
        - "cave": Go to the Cave
        - "spawn farmer": For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - "spawn warrior": For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned
        """
        # Classify villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat in the farm
        wheat = 0
        if hasattr(environment, "farm") and environment.farm is not None:
            wheat = getattr(environment.farm, "wheat", 0)

        # Compute maximal spawns in this step
        # Spawn warriors first (higher DPS)
        war_spawns = min(len(farmers) // 2, wheat // 12) if farmers else 0

        to_spawn_war = []
        if war_spawns > 0:
            to_spawn_war = farmers[:2 * war_spawns]

        remaining_farmers = [f for f in farmers if f not in to_spawn_war]
        remaining_wheat = wheat - (12 * war_spawns)

        # Then spawn farmers with remaining wheat
        farm_spawns = min(len(remaining_farmers) // 2, max(remaining_wheat // 10, 0)) if remaining_farmers else 0

        to_spawn_farm = []
        if farm_spawns > 0:
            to_spawn_farm = remaining_farmers[:2 * farm_spawns]

        # Remaining farmers will farm
        set_war = set(to_spawn_war)
        set_farm_spawn = set(to_spawn_farm)

        # Assign groups
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "cave")
            elif c in set_farm_spawn:
                environment.assign_group(c, "spawn farmer")
            elif c in set_war:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Villagers in the Cave:
        - Warriors -> attack the Dragon
        - Farmers -> go back to Village (stay in Village)
        """
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")