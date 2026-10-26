import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartDragonHuntAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _resolve(group_ids, keywords, fallback):
        """Return the first entry of group_ids whose string contains any keyword."""
        try:
            ids = list(group_ids) if group_ids is not None else []
        except TypeError:
            ids = []
        for kw in keywords:
            for g in ids:
                if kw.lower() in str(g).lower():
                    return g
        return fallback

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        cave_group  = self._resolve(group_ids, ("cave", "move"), "cave")
        farm_group  = self._resolve(group_ids, ("farm",),        "farm")
        spawn_group = self._resolve(group_ids, ("spawn",),       "spawn warrior")

        # 1) Every warrior in the village moves to the cave right now.
        for w in warriors:
            environment.assign_group(w, cave_group)

        if not farmers:
            return

        # 2) Pair farmers into the spawn group (engine ignores if unaffordable).
        num_pairs = len(farmers) // 2
        paired   = farmers[: num_pairs * 2]
        leftover = farmers[num_pairs * 2:]

        for f in paired:
            environment.assign_group(f, spawn_group)
        for f in leftover:
            environment.assign_group(f, farm_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        attack_group  = self._resolve(group_ids, ("attack", "fight"), "attack")
        village_group = self._resolve(group_ids, ("village", "home"), "village")

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                # Warriors always attack — no retreat, ever.
                environment.assign_group(c, attack_group)
            else:
                # A farmer stranded in the cave returns to the village.
                environment.assign_group(c, village_group)