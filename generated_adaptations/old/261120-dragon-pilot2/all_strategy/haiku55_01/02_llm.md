## Adaptation strategy

The strategy has three goals: kill the Dragon fast, keep every villager fed within the 6-step starvation limit, and grow the army with spawns. It uses the following rules.

**In the Village**
1. **Meals first.** Any villager with `steps_since_meal >= 2` eats. That gives a safety margin before the 6-step limit. Eating is limited by the wheat available, and the most-starved villagers are fed first.
2. **Warriors cycle through meals.** A warrior that is in the Village and not yet due for a meal goes to the Cave. It attacks there and returns when hungry.
3. **Wheat reserve.** Each step, a reserve is kept for upcoming meals (about one wheat per villager, rounded up). Spawns only use wheat above this reserve.
4. **Spawning.** Idle farmers (not eating) are used as spawners, since they are the cheapest to keep in the Village. A Warrior is spawned when wheat exceeds 12 plus the reserve, because Warriors are the damage dealers. Otherwise a Farmer is spawned when wheat exceeds 10 plus the reserve. Each spawn uses a pair of idle farmers.
5. **Farming.** All remaining idle farmers stay in the Village and farm wheat.

**In the Cave**
1. Villagers with `steps_since_meal >= 3` return to the Village. This leaves time for the one-step trip back and the meal before the starvation limit is reached.
2. All other villagers attack the Dragon. Warriors do the most damage, and starving villagers are not used because they deal no damage.

The Cave group "cave" is not used, since staying in the Cave gives no benefit. Every component is explicitly assigned each step, as the rules require.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Villagers eat when steps_since_meal >= 2 (safety margin before the 6-step limit).
      - Warriors that are not hungry in the Village go to the Cave to attack.
      - Villagers in the Cave return to the Village when steps_since_meal >= 3 to eat.
      - Idle farmers farm wheat, and pairs of idle farmers are used to spawn
        Warriors (preferred, when wheat allows) or Farmers.
      - A wheat reserve is kept for upcoming meals before any spawning.
    """

    EAT_THRESHOLD = 2       # eat in village when steps_since_meal reaches this
    RETURN_THRESHOLD = 3    # leave the cave for food at this many steps without a meal
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        n_total = len(components)
        # Reserve wheat for upcoming meals (about one per villager).
        reserve = max(1, n_total)

        # 1) Feed the hungry villagers, most-starved first, as far as wheat allows.
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        eaters = []
        for c in hungry:
            if wheat >= 1:
                eaters.append(c)
                wheat -= 1
            # If wheat runs out, the remaining hungry villagers are handled
            # below and will be assigned to farm (they should be rare).

        eat_set = set(id(c) for c in eaters)
        for c in eaters:
            environment.assign_group(c, "eat")

        # Remaining villagers (not eating).
        idle = [c for c in components if id(c) not in eat_set]

        # 2) Warriors that are not hungry go to the Cave to attack.
        #    Farmers remain in the Village.
        idle_farmers = [c for c in idle if c.role == "Farmer"]
        idle_warriors = [c for c in idle if c.role == "Warrior"]

        # 3) Spawning, using idle farmers as spawners, only if wheat is above the reserve.
        spare = wheat - reserve
        spawn_set = set()
        if len(idle_farmers) >= 2:
            if spare >= self.WARRIOR_COST:
                pair = idle_farmers[:2]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawn_set.add(id(c))
                spare -= self.WARRIOR_COST
            elif spare >= self.FARMER_COST:
                pair = idle_farmers[:2]
                for c in pair:
                    environment.assign_group(c, "spawn farmer")
                    spawn_set.add(id(c))
                spare -= self.FARMER_COST

        # 4) Assign the rest.
        for c in idle:
            if id(c) in spawn_set:
                continue
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= self.RETURN_THRESHOLD:
                # Go back to the Village to eat before starving.
                environment.assign_group(c, "village")
            else:
                # Attack the Dragon.
                environment.assign_group(c, "attack")
```