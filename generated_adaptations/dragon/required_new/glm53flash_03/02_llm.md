## Strategy Description

The strategy is a wave-based dragon assault with a sustainable food economy:

**Warriors (damage dealers):** Warriors cycle between the Village and the Cave. In the Village, any villager with `steps_since_meal >= 3` eats (this leaves a safety margin: travel to the Cave costs 1 step, so they arrive with `steps_since_meal` ≈ 1 and can attack for ~3 steps). In the Cave, warriors attack while `steps_since_meal < 4`, then head back to the Village so they arrive hungry-but-alive (`steps_since_meal` 5) and eat before ever hitting the starvation threshold of 6. This yields ~3 attacks (9 damage) per warrior per 6-step cycle. Wounded warriors (HP ≤ 1) retreat early.

**Farmers (economy):** Farmers stay in the Village farming (at least one keeps producing wheat) and eat on the same `steps_since_meal >= 3` schedule.

**Spawning:** When wheat accumulates a comfortable surplus (> cost + 25 buffer), two villagers are put into the "spawn warrior" group — warriors are the priority since they scale damage. If the population gets dangerously small, a farmer pair is spawned instead to secure the food economy. Buffers ensure spawning never jeopardizes feeding everyone.

**Safety:** Nobody is ever allowed to reach `steps_since_meal >= 6` — the thresholds (eat at 3 in the Village, retreat at 4 in the Cave) guarantee everyone eats in time even accounting for the 1-step travel time.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        all_villagers = list(environment.farmers) + list(environment.warriors)

        farmers_here = [c for c in components if c.role == "Farmer"]
        warriors_here = [c for c in components if c.role == "Warrior"]

        # Decide on a spawn pair (consumes 2 villagers for this step)
        spawn_pair = None
        if dragon_alive:
            if wheat >= 12 + 25 and len(warriors_here) >= 2:
                spawn_pair = ("spawn warrior", warriors_here[:2])
            elif wheat >= 12 + 25 and wheat >= 10 + 25 and len(farmers_here) >= 4:
                # Not enough warriors in village: sacrifice two farmers for warriors
                spawn_pair = ("spawn warrior", farmers_here[:2])
        # If population is critically low, prioritize reproducing farmers (food security)
        if spawn_pair is None and len(all_villagers) <= 3 and len(farmers_here) >= 2 \
                and wheat >= 10 + 15:
            spawn_pair = ("spawn farmer", farmers_here[:2])

        spawned = set()
        if spawn_pair is not None:
            spawned = set(id(c) for c in spawn_pair[1])

        for c in components:
            if id(c) in spawned:
                environment.assign_group(c, spawn_pair[0])
                continue
            # Eat in time (margin of 3 covers the 1-step trip back from the Cave),
            # or if too weak to be useful
            if c.steps_since_meal >= 3 or c.hp <= 1:
                environment.assign_group(c, "eat")
            elif c.role == "Warrior" and dragon_alive:
                # Healthy warriors head out to attack the Dragon
                environment.assign_group(c, "cave")
            else:
                # Farmers keep the food economy running
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # Retreat before starvation (arrive in Village at ssm 5, eat there),
            # or if too wounded to fight safely
            if c.steps_since_meal >= 4 or c.hp <= 1:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```