from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Early, small, deterministic push of Warriors into the Cave (up to 3) to start attacking.
        # - Farmers stay in Village (farm) by default, but we spawn conservatively when wheat allows.
        # - Spawns use disjoint donors to keep progression predictable.
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        assigned = set()

        # 1) Early push: move up to 3 Warri ors to the Cave for early DPS
        if len(warriors) >= 3:
            for w in warriors[:3]:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 2) Default allocations for the rest
        for f in farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")
        for w in warriors:
            if w not in assigned:
                environment.assign_group(w, "cave")
                assigned.add(w)

        # 3) Spawning decisions (conservative and disjoint)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmer: at least 4 farmers and wheat >= 10
        if len(farmers) >= 4 and wheat >= 10:
            donors_farm = farmers[:2]  # two farmers become spawn donors
            for d in donors_farm:
                environment.assign_group(d, "spawn farmer")

        # Spawn warrior: use two villagers not used for farmer-spawn, if possible
        remaining_for_war_spawn = [v for v in components if v not in farmers[:2]]
        if len(remaining_for_war_spawn) >= 2 and wheat >= 12:
            donors_war = remaining_for_war_spawn[:2]
            for d in donors_war:
                environment.assign_group(d, "spawn warrior")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")