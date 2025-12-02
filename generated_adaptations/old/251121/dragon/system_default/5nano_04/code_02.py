from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Cache to remember previous assignments across steps
        self._assignment_cache = {}

    def _set_group(self, environment, comp, group_id):
        environment.assign_group(comp, group_id)
        self._assignment_cache[id(comp)] = group_id

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Base assignment: Warriors go to the Cave; Farmers stay in Farm
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "cave"       # Go to the Cave (to eventually attack)
            else:
                grp = "farm"       # Stay in Village and farm
            self._set_group(environment, comp, grp)

        # Spawn logic (uses current Wheat in the Farm)
        remaining_wheat = environment.farm.wheat

        # List of Farmers that exist
        farmers = [c for c in components if getattr(c, "role", "") == "Farmer"]

        # Farmers currently considered in Farm (based on our cache or default to Farm)
        farmers_in_farm = [c for c in farmers if self._assignment_cache.get(id(c), None) in (None, "farm")]
        # Candidates to start a spawn farmer (avoid reusing those already in spawn farmer)
        sp_farm_candidates = [c for c in farmers_in_farm if self._assignment_cache.get(id(c), None) != "spawn farmer"]

        # Spawn Farmers: need two villagers in the group and 10 wheat
        while len(sp_farm_candidates) >= 2 and remaining_wheat >= 10:
            c1 = sp_farm_candidates.pop(0)
            c2 = sp_farm_candidates.pop(0)
            self._set_group(environment, c1, "spawn farmer")
            self._set_group(environment, c2, "spawn farmer")
            remaining_wheat -= 10
            # These two are now in the spawn farmer group; they won't be in sp_farm_candidates anymore

        # After handling Farmer spawns, attempt to spawn Warriors
        # Recompute available Farmers that can be used for spawning Warriors (not already in any spawn group)
        farmers_in_farm = [c for c in farmers if self._assignment_cache.get(id(c), None) in (None, "farm")]
        sp_war_candidates = [c for c in farmers_in_farm if self._assignment_cache.get(id(c), None) not in ("spawn warrior",)]

        # Spawn Warriors: need two villagers and 12 wheat
        while len(sp_war_candidates) >= 2 and remaining_wheat >= 12:
            c1 = sp_war_candidates.pop(0)
            c2 = sp_war_candidates.pop(0)
            self._set_group(environment, c1, "spawn warrior")
            self._set_group(environment, c2, "spawn warrior")
            remaining_wheat -= 12

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors should attack; Farmers should stay in Village
        for comp in components:
            if getattr(comp, "role", "") == "Warrior":
                grp = "attack"   # Attack the Dragon
            else:
                grp = "village"  # Stay in the Village
            self._set_group(environment, comp, grp)