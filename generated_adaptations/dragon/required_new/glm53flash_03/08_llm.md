## Analysis

The Dragon never died because the army never grew: the spawn condition required **two warriors to be in the Village at the same time**, but warriors cycle to the Cave constantly, so spawning almost never fired. The initial warriors slowly died to the Dragon's attacks/eating and the Dragon out-regenerated the shrinking damage output.

Fixes:

1. **Spawn any two available villagers** in the Village (warriors or farmers) when wheat allows, with a modest buffer — so the warrior population actually grows to replace attrition. Farmers are converted only when there are enough of them to sustain wheat production; an emergency rule covers the "no warriors at all" case.
2. **Staggered attack shifts**: a persistent toggle delays half the warriors by one step in the Village, so the Dragon is attacked almost every step and its 5 HP/step regeneration barely triggers.
3. **Safe but tight eating schedule**: eat in the Village at `ssm >= 3`; in the Cave attack while `ssm <= 3`, retreat at 4, arrive home at 5 and eat — a 5-step cycle with 3 attacks per warrior and a full step of safety margin.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._toggle = False  # used to stagger warriors into two shifts

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_warriors = list(environment.warriors)
        all_farmers = list(environment.farmers)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]
        self._toggle = not self._toggle

        # Villagers that must eat this step take priority over everything else
        hungry = [c for c in components if c.steps_since_meal >= 3 or c.hp <= 1]
        meal_cost = len(hungry)

        spawn_group, spawn_pair = None, None
        if dragon_alive:
            # Spawn a warrior whenever affordable with a safety buffer
            if wheat >= 12 + 15 + meal_cost:
                candidates = [c for c in components if c not in hungry]
                if len(candidates) >= 2:
                    if len(all_farmers) >= 4 or not all_warriors:
                        # Prefer converting farmers (keeps warrior damage intact),
                        # or emergency conversion when there are no warriors at all
                        pool = [c for c in candidates if c.role == "Farmer"]
                        if len(pool) < 2:
                            pool = candidates
                        spawn_group, spawn_pair = "spawn warrior", pool[:2]
            # Keep the food economy alive
            if spawn_group is None and len(all_farmers) <= 2 \
                    and wheat >= 10 + 15 + meal_cost:
                pool = [c for c in components
                        if c not in hungry and c.role == "Farmer"]
                if len(pool) >= 2:
                    spawn_group, spawn_pair = "spawn farmer", pool[:2]

        spawned = set(id(c) for c in (spawn_pair or []))

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_group)
            elif c.steps_since_meal >= 3 or c.hp <= 1:
                # Eat with a safety margin before the 6-step limit
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                if c.steps_since_meal == 0 and self._toggle:
                    # Stagger: every other freshly-fed warrior waits one step,
                    # so the two shifts attack in alternating windows and the
                    # Dragon rarely gets a free regeneration step.
                    environment.assign_group(c, "farm")
                else:
                    environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Attack while ssm <= 3 (3 attacks per trip), then head home:
            # they arrive in the Village with ssm 5 and eat immediately,
            # still within the 6-step starvation limit.
            if c.steps_since_meal >= 4 or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```