import abc
from typing import List
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - "farm": stay in Village and farm
        - "cave": go to Cave (to be attacked later)
        - "spawn farmer": for every two villagers assigned here and 10 wheat, spawn a Farmer
        - "spawn warrior": for every two villagers assigned here and 12 wheat, spawn a Warrior
        """
        # Classify villagers by current role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available from farm resource
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Determine spawns using the pool of farmers only (no repeated assignments)
        max_possible_farm_spawns = wheat // 10
        s_f = min(len(farmers) // 2, max_possible_farm_spawns)

        # After allocating s_f spawns for farmers, reduce wheat
        remaining_wheat = wheat - s_f * 10

        # Determine spawns for warriors using remaining wheat and remaining farmers
        max_war_spawns_now = remaining_wheat // 12
        available_for_war_spawns = max(0, len(farmers) - 2 * s_f)
        s_w = min(available_for_war_spawns // 2, max_war_spawns_now)

        # Finalize assignments ensuring exactly one assignment per component
        # 1) Assign farmers to spawn groups or farm in a single pass
        if s_f > 0:
            for c in farmers[:2 * s_f]:
                environment.assign_group(c, "spawn farmer")
        if s_w > 0:
            for c in farmers[2 * s_f : 2 * s_f + 2 * s_w]:
                environment.assign_group(c, "spawn warrior")
        # Remaining farmers go to farm
        for c in farmers[2 * s_f + 2 * s_w:]:
            environment.assign_group(c, "farm")

        # 2) All warriors go to cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - "attack": Attack the Dragon
        - "cave": Stay in the Cave
        - "village": Go to the Village
        """
        # Warriors should attack; Farmers should go to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")