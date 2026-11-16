The failures come from the village logic. Hungry villagers were all sent to `eat` without checking the wheat supply, and the environment rejects an `eat` assignment when there is no wheat. Those rejected villagers then never received a second assignment, which caused the "not assigned" failures. The Daniel failure has the same cause: a hungry warrior was never sent to the Cave.

The fix:
1. **Budget the meals.** Hungry villagers are sorted by hunger (highest first, warriors first on ties) and only as many as the available wheat can feed are sent to `eat`.
2. **Assign every villager.** Villagers who cannot eat get a fallback group: warriors go to `cave` so they can still fight, and farmers go to `farm`. Every component is assigned exactly once.
3. **Spawn only from leftover wheat.** Spawning uses the wheat that remains after the meal budget.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Village: feed the hungriest villagers as far as wheat allows (warriors first on
      ties), spawn reinforcements with leftover wheat, send fed warriors to the Cave,
      and farm with the rest. Every villager receives exactly one assignment.
    - Cave: attack with well-fed warriors, send hungry villagers and all farmers
      back to the Village, keep the rest in the Cave.
    """

    HUNGER_EAT_THRESHOLD = 3     # village: eat when steps_since_meal >= 3
    HUNGER_RETURN_THRESHOLD = 3  # cave: go back to village when steps_since_meal >= 3
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _hunger(self, c):
        return getattr(c, "steps_since_meal", 0)

    def _role(self, c):
        return getattr(c, "role", "")

    def assign_in_village(self, components, environment, group_ids, step: int):
        comps = list(components)
        wheat = getattr(environment.farm, "wheat", 0)
        assigned = set()

        # 1. Feed hungry villagers, hungriest first (warriors first on ties),
        #    but only as many as the available wheat can pay for.
        hungry = [c for c in comps if self._hunger(c) >= self.HUNGER_EAT_THRESHOLD]
        hungry.sort(key=lambda c: (-self._hunger(c), 0 if self._role(c) == "Warrior" else 1))

        meals_affordable = max(0, wheat)
        for c in hungry:
            if meals_affordable > 0:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                meals_affordable -= 1

        # Hungry villagers that could not be fed: warriors head to the Cave,
        # farmers keep farming (they cannot be sent to the Cave).
        for c in hungry:
            if id(c) in assigned:
                continue
            if self._role(c) == "Warrior":
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")
            assigned.add(id(c))

        wheat_left = meals_affordable  # wheat not needed for meals this step

        remaining = [c for c in comps if id(c) not in assigned]
        farmers = [c for c in remaining if self._role(c) == "Farmer"]
        warriors = [c for c in remaining if self._role(c) == "Warrior"]

        # 2. Spawn with leftover wheat (spawners are farmers so warriors stay free).
        if len(farmers) >= 2 and wheat_left >= self.WARRIOR_COST:
            for c in farmers[:2]:
                environment.assign_group(c, "spawn warrior")
                assigned.add(id(c))
            wheat_left -= self.WARRIOR_COST
        elif len(farmers) >= 2 and wheat_left >= self.FARMER_COST:
            for c in farmers[:2]:
                environment.assign_group(c, "spawn farmer")
                assigned.add(id(c))
            wheat_left -= self.FARMER_COST

        # 3. Fed warriors go to the Cave.
        for c in warriors:
            if id(c) in assigned:
                continue
            environment.assign_group(c, "cave")
            assigned.add(id(c))

        # 4. Every other remaining villager (farmers) farms.
        for c in comps:
            if id(c) in assigned:
                continue
            environment.assign_group(c, "farm")
            assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hunger = self._hunger(c)
            role = self._role(c)

            if role == "Farmer":
                # Farmers must stay in the Village.
                environment.assign_group(c, "village")
            elif hunger >= self.HUNGER_RETURN_THRESHOLD:
                # Hungry warrior: return to eat before it starves.
                environment.assign_group(c, "village")
            else:
                # Healthy warrior: attack the Dragon.
                environment.assign_group(c, "attack")
```