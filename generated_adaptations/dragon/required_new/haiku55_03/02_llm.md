## Strategy: Rotating Warrior Strike with Farmer Support

**Goal:** Kill the 100 HP Dragon quickly while keeping every villager fed within the 6-step starvation limit.

**Key observations:**
- Warriors deal 3 damage per attack, versus 1 for farmers, so warriors do the killing.
- The Dragon regenerates 5 HP per step only when nobody attacks, so the strategy keeps attacks going on most steps.
- Villagers in the Cave cannot eat, so warriors must rotate back to the Village to eat before they starve.
- Farmers produce wheat, which funds meals and spawning, so they stay in the Village.

**Village rules:**
- **Warriors:** If a warrior has not eaten in at least 1 step, it goes to "eat". Otherwise it goes to "cave". This gives a short eat-then-strike rhythm.
- **Farmers:** If a farmer's `steps_since_meal` reaches 3, it goes to "eat" (with a safety margin below the 6-step limit). Otherwise it stays on "farm".
- **Wheat budget:** Meals are capped by available wheat, with the most-hungry villagers fed first.
- **Spawning:** When wheat is enough to cover meals plus a warrior spawn (12 wheat), two farmers that are not eating are placed in "spawn warrior". Warriors are preferred because they deal three times the damage.

**Cave rules:**
- **Warriors:** A warrior attacks ("attack") while `steps_since_meal <= 3`. Once it reaches 4, it returns to "village" to eat before the 6-step starvation threshold.
- **Anyone else in the Cave** (such as a farmer) is sent back to "village".

Every component is assigned in every call, so nothing carries over implicitly.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Rotating warrior strike:
      - Warriors attack in the Cave while they are well fed (steps_since_meal <= 3).
        When they get hungrier they return to the Village, eat, and go back.
      - Farmers stay in the Village, farm wheat, and eat when they reach 3 steps
        without a meal (well before the 6-step starvation limit).
      - When wheat allows, two non-eating farmers are used to spawn a new Warrior
        (the most damaging unit).
    """

    WARRIOR_EAT_THRESHOLD = 1      # warriors in the Village eat if hungry at all
    FARMER_EAT_THRESHOLD = 3       # farmers eat before reaching the 6-step limit
    CAVE_RETURN_THRESHOLD = 3      # warriors in the Cave leave when steps_since_meal >= 4
    SPAWN_WARRIOR_WHEAT = 12

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        hungry_warriors = []
        to_cave = []
        hungry_farmers = []
        farming = []

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD:
                    hungry_warriors.append(c)
                else:
                    to_cave.append(c)
            else:  # Farmer
                if c.steps_since_meal >= self.FARMER_EAT_THRESHOLD:
                    hungry_farmers.append(c)
                else:
                    farming.append(c)

        # Feed the most hungry villagers first, limited by available wheat.
        eaters = hungry_warriors + hungry_farmers
        eaters.sort(key=lambda c: c.steps_since_meal, reverse=True)
        fed = eaters[:max(0, wheat)]
        unfed = eaters[max(0, wheat):]

        # Unfed (no wheat) villagers cannot eat; keep them farming/in village.
        for c in unfed:
            if c.role == "Warrior":
                to_cave.append(c) if False else farming.append(c)
            else:
                farming.append(c)

        remaining_wheat = wheat - len(fed)

        # Spawn a warrior if enough wheat remains and two farmers are available.
        spawn_group = []
        if remaining_wheat >= self.SPAWN_WARRIOR_WHEAT:
            candidates = [c for c in farming if c.role == "Farmer"]
            if len(candidates) >= 2:
                spawn_group = candidates[:2]
                farming = [c for c in farming if c not in spawn_group]

        # Make sure every component is assigned exactly once.
        assigned = set()

        def give(c, group):
            if id(c) in assigned:
                return
            environment.assign_group(c, group)
            assigned.add(id(c))

        for c in fed:
            give(c, "eat")
        for c in spawn_group:
            give(c, "spawn warrior")
        for c in to_cave:
            give(c, "cave")
        for c in farming:
            give(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal <= self.CAVE_RETURN_THRESHOLD:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```