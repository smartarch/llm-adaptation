```py
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

        We assign each component exactly once, using a simple deterministic heuristic.
        We also bias toward spawning a small number of Warriors when wheat permits.
        """
        # Separate by role
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

        # Bias: ensure at least a small number of Warrior spawns if possible
        if max_spawns_war == 0 and len(warriors) >= 2 and remaining_wheat_after_farm_spawns >= 24:
            max_spawns_war = 2
        elif max_spawns_war == 0 and len(warriors) >= 2 and remaining_wheat_after_farm_spawns >= 12:
            max_spawns_war = 1

        # Assignments done per component to guarantee exactly one group per component
        for idx, f in enumerate(farmers):
            if idx < 2 * max_spawns_farm:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

        for idx, w in enumerate(warriors):
            if idx < 2 * max_spawns_war:
                environment.assign_group(w, "spawn warrior")
            else:
                environment.assign_group(w, "cave")

        # If there are any non-villager components (unexpected), put them in a sane default
        for comp in components:
            if getattr(comp, "role", None) not in {"Farmer", "Warrior"}:
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
                environment.assign_group(c, "cave")
```