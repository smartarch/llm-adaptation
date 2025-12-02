import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Build a single, explicit plan keyed by id(component) to ensure exactly one assignment per component
        plan_by_id = {}
        id_to_comp = {}

        # Collect components and initialize default plan
        farmers = []
        for c in components:
            cid = id(c)
            id_to_comp[cid] = c
            role = getattr(c, "role", None)
            if role == "Farmer":
                farmers.append(c)
                plan_by_id[cid] = "farm"
            elif role == "Warrior":
                plan_by_id[cid] = "cave"
            else:
                plan_by_id[cid] = "farm"  # fallback

        # Spawn farmer if possible: need 2 villagers in spawn farmer and 10 wheat
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            f1, f2 = farmers[0], farmers[1]
            plan_by_id[id(f1)] = "spawn farmer"
            plan_by_id[id(f2)] = "spawn farmer"

        # Spawn warrior if possible: need 2 villagers in spawn warrior and 12 wheat
        # Exclude those already assigned to spawn farmer
        candidates = [c for c in components if plan_by_id.get(id(c)) != "spawn farmer"]
        if len(candidates) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            w1, w2 = candidates[0], candidates[1]
            plan_by_id[id(w1)] = "spawn warrior"
            plan_by_id[id(w2)] = "spawn warrior"

        # Apply the plan: assign each component exactly once
        for cid, comp in id_to_comp.items():
            target = plan_by_id.get(cid, "farm")
            environment.assign_group(comp, target)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack the Dragon; Farmers go to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                # Fallback for unknown roles
                environment.assign_group(c, "cave")