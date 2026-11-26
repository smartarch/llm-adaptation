All system and required mid-game tests pass; only the end condition (dragon dead) fails. The likely problems: not enough sustained damage (spawning too rare, farmers never helping), and possibly gaps where nobody attacks the dragon (letting it regenerate 5 HP/step). New plan:

- **Build & sustain warriors:** spawn a warrior pair whenever wheat allows (after reserving meals), whenever we have fewer than 6 warriors — warriors are the bottleneck for damage.
- **Gapless pressure:** all healthy village warriors go to the cave every step; cave villagers attack unless they must rotate home to eat (threshold 4) — with several warriors, meals are staggered so someone always attacks, preventing regeneration.
- **Finish fast:** when the dragon is low (< 40 HP), healthy farmers also join the attack for extra damage to end the game within the 30-step limit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        all_warriors = len(environment.warriors)
        total = all_warriors + len(environment.farmers)

        # reserve wheat for meals this step
        hungry = sum(1 for c in components if c.steps_since_meal >= 4)
        wheat_for_spawns = wheat - hungry

        # aggressive warrior production: always keep growing the attack force
        spawn_slots = 0
        if wheat_for_spawns >= 12:
            if all_warriors < 6:
                spawn_slots = min(4, (wheat_for_spawns // 12) * 2)
            elif dragon.hp < 100 and wheat_for_spawns >= 40:
                spawn_slots = min(4, (wheat_for_spawns // 12) * 2)

        finishing = 0 < dragon.hp <= 40  # farmers help finish the dragon

        for c in components:
            # 1) eating has top priority (travel takes a step, so eat at >= 4)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "eat")
                continue
            # 2) spawn warriors whenever possible (they are the main damage)
            if spawn_slots >= 2 and c.hp > 3 and c.steps_since_meal <= 2:
                environment.assign_group(c, "spawn warrior")
                spawn_slots -= 2
                continue
            # 3) warriors attack: go to the cave
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                continue
            # 4) farmers: help finish the dragon, or occasionally grow the village
            if finishing and c.hp > 2 and c.steps_since_meal <= 2:
                environment.assign_group(c, "cave")
                continue
            if (c.role == "Farmer" and total < 6
                    and wheat_for_spawns >= 10 + 12 and c.hp > 3
                    and c.steps_since_meal <= 2 and step % 4 == 0):
                environment.assign_group(c, "spawn farmer")
                continue
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            # starving -> go home to eat (travel takes one step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            # too weak -> retreat
            elif c.hp <= 1:
                environment.assign_group(c, "village")
            # otherwise attack (keep pressure so the dragon never regenerates)
            elif dragon.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```

Key changes:
- Warrior spawning is no longer gated by `step % 6` or a small budget — any spare wheat (after meal reserve) goes into new warriors, so the attack force grows quickly.
- All healthy warriors are sent to the cave every step, and cave villagers only leave to eat/retreat; with multiple warriors their meal rotations are staggered, so the dragon is attacked every step and never regenerates.
- When the dragon drops below 40 HP, farmers join the assault to finish it off quickly within the 30-step limit.