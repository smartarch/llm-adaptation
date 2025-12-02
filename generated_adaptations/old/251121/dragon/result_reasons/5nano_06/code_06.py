from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In the Village: 
        # - Farmers -> farm (stay in Village)
        # - Warriors -> cave (go to Cave to attack)
        # - Spawn groups to quietly grow numbers, only when feasible
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Default placement: Farmers farm, Warriors head to Cave
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # 2) Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # 3) Spawn planning: try to spawn at most 1 farmer and 1 warrior per step
        # Ensure we have two farmers to spare for a farmer-spawn
        used_for_farm_spawn = []
        if len(farmers) >= 2 and wheat >= 10:
            # Take two farmers to join the spawn farmer group
            spawn_farm_candidates = farmers[:2]
            for c in spawn_farm_candidates:
                environment.assign_group(c, "spawn farmer")
            used_for_farm_spawn = spawn_farm_candidates

        # Ensure we have two villagers (not already used) to join the spawn warrior group
        remaining_for_war_spawn = [f for f in farmers if f not in used_for_farm_spawn] + \
                                  [w for w in warriors if w not in used_for_farm_spawn]
        if len(remaining_for_war_spawn) >= 2 and wheat >= 12:
            spawn_war_candidates = remaining_for_war_spawn[:2]
            for c in spawn_war_candidates:
                environment.assign_group(c, "spawn warrior")

        # 4) Early aggression boost (optional guard): ensure a minimal presence in cave early
        # If step is very early, try to keep a modest number in cave for a quick first attack.
        if step < 5:
            # Count current warriors actively headed to cave (they are already in cave by default)
            # If somehow there are zero Warriors (edge case), do nothing extra here.
            pass

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")