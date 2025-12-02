import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village policy:
        - Farmers -> farm
        - Warriors -> cave (they will travel to Cave and then attack)
        - Opportunistic spawning:
          - If there are at least 2 Farmers in the Village and farm.wheat >= 10, move 2 Farmers to "spawn farmer"
          - If there are still at least 2 Farmers idle in Village and farm.wheat >= 22, move 2 more Farmers to "spawn warrior"
        - The spawn mechanics will create new villagers when the conditions are met.
        """
        farmers = []
        warriors = []
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Farmer":
                farmers.append(comp)
                self._assign_component(environment, comp, "farm")
            elif role == "Warrior":
                warriors.append(comp)
                self._assign_component(environment, comp, "cave")
            else:
                # Fallback: keep unknowns in farm
                self._assign_component(environment, comp, "farm")

        # Spawn farmer: require at least 2 farmers in village and wheat >= 10
        farm_wheat = getattr(getattr(environment, "farm", None), "wheat", 0)
        if len(farmers) >= 2 and farm_wheat >= 10:
            # Pick first two farmers to spawn farmer
            to_spawn = farmers[:2]
            for c in to_spawn:
                self._assign_component(environment, c, "spawn farmer")

        # Spawn warrior: require at least 2 farmers still in village and wheat >= 22
        # Recompute farmers in village (excluding those moved to spawn farmer)
        remaining_farmers = [f for f in farmers if getattr(f, "current_group", None) != "spawn farmer"]
        if len(remaining_farmers) >= 2 and farm_wheat >= 22:
            to_spawn_warrior = remaining_farmers[:2]
            for c in to_spawn_warrior:
                self._assign_component(environment, c, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave policy:
        - Warriors -> attack
        - Farmers -> village (return to Village)
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                self._assign_component(environment, comp, "attack")
            else:
                self._assign_component(environment, comp, "village")

    def _assign_component(self, environment, component, group_id):
        # Safely assign to a valid group
        environment.assign_group(component, group_id)