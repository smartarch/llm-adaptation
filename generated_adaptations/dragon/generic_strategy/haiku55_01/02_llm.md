## Strategy: Warrior Surge with Scheduled Meals

The plan is to put almost all damage into Warriors, since they deal 3 damage per attack versus 1 for Farmers. Farmers stay in the Village to produce wheat, pay for meals, and fund new Warriors.

**Village phase**
1. **Meals first.** Any villager with `steps_since_meal >= 3` eats, as long as wheat is available. Eating at 3 keeps everyone under the 6-step starvation limit, leaving room for the one-step trip back from the Cave. Each meal is paid from a running wheat budget so the same wheat is never double-counted.
2. **Spawn Warriors.** While the remaining wheat covers 12 per spawn and at least two free Farmers exist, pairs of Farmers are placed in "spawn warrior" (at most two spawns per step).
3. **Early Farmer spawns.** In the first few steps, if wheat is short and no Warrior spawn is affordable, Farmer pairs are spawned to strengthen the wheat economy.
4. **Warriors deploy.** Free Warriors that have recently eaten are sent to the Cave.
5. **Everyone else farms.**

**Cave phase**
1. Warriors with `steps_since_meal >= 3` return to the Village so they can eat before starving.
2. Farmers that somehow end up in the Cave return to the Village. They deal negligible damage and are needed for farming.
3. All other Warriors attack the Dragon. Their damage matters most, and the Dragon's 5 HP per-step regeneration only pauses while it is attacked.

Attribute values are read at the start of each step, so the thresholds include a safety margin of one step. Because the Dragon's counterattacks can hit everyone in the Cave, the strategy keeps Warrior trips short.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge strategy:
      - Farmers stay in the Village, farm wheat, eat on schedule and fund spawns.
      - Warriors are spawned (from pairs of Farmers) whenever wheat allows.
      - Warriors attack the Dragon from the Cave and return to eat before starving.
    """

    EAT_THRESHOLD = 3        # eat in the Village when this many steps have passed without a meal
    CAVE_RETURN_THRESHOLD = 3  # Warriors in the Cave return to eat at this point
    WARRIOR_COST = 12
    FARMER_COST = 10
    MAX_SPAWNS_PER_STEP = 2
    EARLY_FARMER_STEPS = 8   # only spawn extra farmers during the first few steps

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_alive = environment.dragon.hp > 0
        budget = wheat

        eaters = []
        rest = []
        # 1) Schedule meals: anyone close to starving eats (costs 1 wheat each)
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD and budget >= 1:
                eaters.append(c)
                budget -= 1
            else:
                rest.append(c)

        free_farmers = [c for c in rest if c.role == "Farmer"]
        free_warriors = [c for c in rest if c.role == "Warrior"]

        spawn_warrior = []
        spawn_farmer = []

        # 2) Spawn warriors from farmer pairs while wheat allows
        spawns = 0
        while (dragon_alive and spawns < self.MAX_SPAWNS_PER_STEP
               and len(free_farmers) >= 2 and budget >= self.WARRIOR_COST):
            spawn_warrior.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.WARRIOR_COST
            spawns += 1

        # 3) Early economy: spawn farmers if no warrior was possible
        if (not spawn_warrior and step < self.EARLY_FARMER_STEPS
                and len(free_farmers) >= 2 and budget >= self.FARMER_COST):
            spawn_farmer.extend([free_farmers.pop(), free_farmers.pop()])
            budget -= self.FARMER_COST

        # 4) Warriors that are not needed for eating head to the Cave
        to_cave = []
        if dragon_alive:
            to_cave = list(free_warriors)
            free_warriors = []

        # 5) Everyone else keeps farming (leftover farmers and any held-back warriors)
        farming = free_farmers + free_warriors

        for c in eaters:
            environment.assign_group(c, "eat")
        for c in spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_cave:
            environment.assign_group(c, "cave")
        for c in farming:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            # Farmers and starving/near-starving Warriors go home to eat
            if c.role == "Farmer" or c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            else:
                # Healthy Warriors fight
                environment.assign_group(c, "attack")
```