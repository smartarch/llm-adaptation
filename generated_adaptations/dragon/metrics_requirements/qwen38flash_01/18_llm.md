

# Re-evaluation After 6 Failures

Two things I now believe were wrong:

1. **Class name.** The base class is `DragonHuntAdaptation`; by convention the subclass should be `SmartDragonHuntAdaptation`. In an earlier attempt I shortened it to `SmartAdaptation` without any instruction to do so — that very likely made the grader unable to import my class, so a stub/losing default ran every time. I will revert to `SmartDragonHuntAdaptation`.
2. **Group names.** I cannot know whether the simulator calls them `"cave"`/`"to_cave"`/`"move_to_cave"` etc. I will resolve them at runtime from `group_ids` by substring, and if the lookup somehow returns `None`, I will pass the raw literal anyway so the engine has the best chance of matching it.

## Strategy (unchanged core, robustly executed)
- Every **warrior** in the village → cave group, immediately.
- Every **warrior** in the cave → attack group, every single turn, unconditionally (maximizes DPS against the 50 HP dragon).
- **Farmers**: pair them greedily into the spawn group (engine ignores the pair if wheat is insufficient — no need to gate). An odd farmer farms. This feeds a steady warrior pipeline to replace losses.
- Any farmer accidentally in the cave → sent back to the village (respects the "farmers stay in village" constraint).

This guarantees: first warrior reaches cave by step 1 and attacks by step 2 (well inside the 15-step requirement), continuous warrior spawning while wheat allows, and full commitment of warriors to attack every turn.

```py
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
```