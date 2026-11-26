The reports show the economy collapses: spawning a warrior pair *every* step costs 24 wheat while 2 farmers only produce 10 — wheat hits 0, spawning stops, the squad dies to the dragon (20% eat chance per step), and no warriors ever come back. Fix: throttle spawning (only when wheat has a healthy buffer, ~1 pair per 2 steps), keep a slightly larger squad (4) so damage per step stays above the dragon's regeneration, and make warrior spawning the top priority whenever no warriors exist at all.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")

        hungry = sum(1 for c in components if c.steps_since_meal >= 5)
        wheat_for_spawns = wheat - hungry

        # sustainable spawn rate: at most one pair every 2 steps,
        # and only if a buffer remains after paying for it
        can_spawn = (wheat_for_spawns >= 24 and step % 2 == 0) or \
                    (wheat_for_spawns >= 12 and all_warriors == 0)
        spawn_slots = 2 if can_spawn else 0

        # rotating attack squad: enough damage to outpace regeneration,
        # small enough to limit attrition from the dragon's retaliation
        squad_size = 4
        to_send = max(0, squad_size - cave_warriors) if dragon.hp > 0 else 0

        for c in components:
            # 1) eating has top priority
            if c.steps_since_meal >= 5:
                environment.assign_group(c, "eat")
                continue
            # 2) spawning warriors is critical (no warriors = no damage)
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) reinforce the attack squad
            if c.role == "Warrior" and c.hp > 1 and to_send > 0:
                environment.assign_group(c, "cave")
                to_send -= 1
                continue
            # 4) everyone else farms to fund the war effort
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            # must leave now to eat in time (travel takes one step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            # too weak -> retreat
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            # otherwise attack (continuous pressure: no regeneration)
            elif dragon.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```

Key changes:
- **Sustainable spawning:** one warrior pair only every 2 steps and only when at least 24 wheat is available (or immediately if no warriors exist at all). Previously 24 wheat/step of spawning against ~10 wheat/step income bankrupted the village, after which warriors died with no replacements.
- **Squad of 4:** ~12 damage per attack step, comfortably above the dragon's 5 HP/step regeneration even accounting for meal rotations; large enough to finish 100 HP quickly, small enough to limit losses to the dragon's retaliation.
- **Emergency spawn path:** when the warrior count is zero (e.g. the dragon ate the whole squad), spawning happens immediately at just 12 wheat, so there is never a long warrior-less gap.