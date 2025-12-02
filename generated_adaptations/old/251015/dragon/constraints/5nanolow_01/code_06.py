import abc

# The base class is assumed to be importable as described
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - "farm": Farmers who will farm
        - "cave": Warriors who will go to cave (to attack)
        - "spawn farmer": Farmers grouped here to spawn new Farmers
        - "spawn warrior": Warriors grouped here to spawn new Warriors
        The assignment is done in a single pass to ensure every component is assigned exactly once.
        """
        # Classify counts while preserving input order
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Wheat available for spawning
        wheat_available = getattr(environment.farm, "wheat", 0)

        max_spawns_farm_by_villagers = len(farmers) // 2
        max_spawns_farm_by_wheat = wheat_available // 10
        max_spawns_farm = min(max_spawns_farm_by_villagers, max_spawns_farm_by_wheat)

        remaining_wheat_after_farm_spawns = wheat_available - max_spawns_farm * 10

        max_spawns_war_by_villagers = len(warriors) // 2
        max_spawns_war_by_wheat = remaining_wheat_after_farm_spawns // 12
        max_spawns_war = min(max_spawns_war_by_villagers, max_spawns_war_by_wheat)

        # Counters to decide group for each component in the original order
        farmers_seen = 0
        warriors_seen = 0

        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Farmer":
                if farmers_seen < 2 * max_spawns_farm:
                    environment.assign_group(comp, "spawn farmer")
                else:
                    environment.assign_group(comp, "farm")
                farmers_seen += 1
            elif role == "Warrior":
                if warriors_seen < 2 * max_spawns_war:
                    environment.assign_group(comp, "spawn warrior")
                else:
                    environment.assign_group(comp, "cave")  # Warriors go to cave to attack
                warriors_seen += 1
            else:
                # Fallback: keep in farm (shouldn't happen with given roles)
                environment.assign_group(comp, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - "attack": Attack the Dragon (Warriors)
        - "cave": Stay in the Cave
        - "village": Go to the Village (Farmers should go to Village)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Safety fallback
                environment.assign_group(c, "cave")