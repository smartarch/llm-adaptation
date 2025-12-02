from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in the Village to farm
        - cave: go to the Cave (for Warriors to attack later)
        - spawn farmer: for every two villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers in this group and 12 wheat, spawn a Warrior
        The final assignment is computed in one pass to avoid multiple assignments per component.
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        final_mapping = {}

        # All Warriors should go to the Cave (attack)
        for w in warriors:
            final_mapping[w] = "cave"

        # Farmers: decide spawn groups vs farm
        total_farmers = len(farmers)
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn farmers: require 2 farmers and 10 wheat per spawn
        max_farm_spawns = min(total_farmers // 2, wheat // 10) if total_farmers >= 2 else 0
        used_for_farm_spawns = max_farm_spawns * 2

        # After allocating for farmer spawns, compute remaining wheat and farmers
        remaining_farmers_after_farm_spawns = total_farmers - used_for_farm_spawns
        wheat_after_farm_spawns = wheat - max_farm_spawns * 10

        # Spawn warriors: require 2 farmers and 12 wheat per spawn
        max_warrior_spawns = 0
        if remaining_farmers_after_farm_spawns >= 2 and wheat_after_farm_spawns >= 12:
            max_warrior_spawns = min( remaining_farmers_after_farm_spawns // 2,
                                      wheat_after_farm_spawns // 12 )

        used_for_warrior_spawns = max_warrior_spawns * 2

        # Assign final groups for farmers in a deterministic order to avoid duplicates
        for idx, f in enumerate(farmers):
            if idx < used_for_farm_spawns:
                final_mapping[f] = "spawn farmer"
            elif idx < used_for_farm_spawns + used_for_warrior_spawns:
                final_mapping[f] = "spawn warrior"
            else:
                final_mapping[f] = "farm"

        # Apply the final mapping (one assignment per component)
        for comp, grp in final_mapping.items():
            environment.assign_group(comp, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        Strategy:
        - All Warriors go to attack to maximize damage
        - Farmers go to village to farm or spawn in the Village
        """
        final_mapping = {}
        for c in components:
            if c.role == "Warrior":
                final_mapping[c] = "attack"
            else:
                final_mapping[c] = "village"

        for comp, grp in final_mapping.items():
            environment.assign_group(comp, grp)