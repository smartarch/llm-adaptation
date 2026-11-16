## Strategy: Warrior-Focused Strike with Farmer-Funded Spawning

**Village phase:**
- **Eat first:** Any villager with `steps_since_meal >= 2` goes to "eat". This keeps everyone well inside the 6-step starvation limit and gives a margin for the return trip from the Cave.
- **Spawn next:** Non-eating farmers act as spawners, since they add the least combat value.
  - Up to two warrior spawns (two farmers in "spawn warrior" and at least 12 wheat remaining after eating costs).
  - Up to one farmer spawn (two farmers in "spawn farmer" and at least 10 wheat).
  - Spawns are skipped when there are fewer than two free farmers, so no villager is wasted.
- **Warriors:** Non-eating warriors (`steps_since_meal < 2`) go to the Cave immediately. This keeps the Dragon attacked early, within the first 15 steps.
- **Farmers:** All remaining farmers stay on the "farm".

**Cave phase:**
- **Warriors:** Attack while they are fed (`steps_since_meal < 3`) and healthy (`hp > 2`). Otherwise they return to the Village to eat or recover. Keeping the Dragon attacked every step prevents its 5 HP/step regeneration.
- **Farmers:** Immediately sent back to the Village. They have only 4 HP and deal negligible damage, and the Dragon's area attacks would kill them.

**Design notes:**
- Spawn counters are incremented per attempt, so the strategy requests at most two warriors and one farmer.
- Wheat is tracked locally during the step so eating and spawning do not overspend.
- Every component is assigned in every call, because groups must be re-assigned explicitly each step.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: eat when steps_since_meal reaches this value (safe margin before 6)
    VILLAGE_EAT_STEPS = 2
    # Cave: warriors that have not eaten this long must return to the Village
    CAVE_MAX_STEPS_UNFED = 3
    # Cave: warriors at or below this HP retreat to the Village
    CAVE_MIN_HP = 2
    # Spawn limits (attempts)
    MAX_WARRIOR_SPAWNS = 2
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_attempts = 0
        self.farmer_spawn_attempts = 0

    def _assign(self, environment, component, group_id, assigned):
        environment.assign_group(component, group_id)
        assigned.add(id(component))

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()
        wheat = environment.farm.wheat

        # 1) Eat: villagers that are close to starving (most hungry first)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_STEPS],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat >= 1:
                self._assign(environment, c, "eat", assigned)
                wheat -= 1
            else:
                # No wheat to eat: keep them in the village (they cannot do anything else useful)
                self._assign(environment, c, "farm", assigned)

        # Free farmers (not eating) are the preferred spawners
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]

        # 2) Spawn warriors (priority: stronger units)
        if (self.warrior_spawn_attempts < self.MAX_WARRIOR_SPAWNS
                and wheat >= 12 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn warrior", assigned)
            wheat -= 12
            self.warrior_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 3) Spawn farmer (one extra farmer for farming)
        if (self.farmer_spawn_attempts < self.MAX_FARMER_SPAWNS
                and wheat >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn farmer", assigned)
            wheat -= 10
            self.farmer_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 4) Remaining units
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                # Fed warriors (steps_since_meal < 2) go to fight
                self._assign(environment, c, "cave", assigned)
            else:
                # Farmers keep working the farm
                self._assign(environment, c, "farm", assigned)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.CAVE_MAX_STEPS_UNFED or c.hp <= self.CAVE_MIN_HP:
                    # Hungry or badly hurt: go eat / recover
                    environment.assign_group(c, "village")
                else:
                    # Fed and healthy: keep hitting the Dragon
                    environment.assign_group(c, "attack")
            else:
                # Farmers are too weak for the Cave: go back to the Village
                environment.assign_group(c, "village")
```