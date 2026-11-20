## Fix: guarantee the spawn requirements early

The failures show that the required spawns (at least one farmer and at least two warriors) never happened, and the Dragon survived. My last version required three free farmers before any spawn, so with a small farmer population nothing was spawned. The fix is to lower that requirement to two free farmers and order the spawns so the farmer requirement is met first:

1. **Farmer spawn first.** The first spawn uses two free farmers and 10 wheat, which satisfies the "at least one new farmer" requirement as early as possible.
2. **Warrior spawns next.** Each spawn uses two free farmers and 12 wheat. Warriors are spawned whenever wheat and free farmers allow, which maximizes Dragon damage.
3. **Eating keeps priority.** Hungry villagers still eat before any spawn, so starvation is avoided even when wheat is spent on spawns.
4. **Dispatch unchanged.** Fresh warriors (`steps_since_meal <= 1`) go to the Cave. In the Cave, warriors attack until they become hungry or badly hurt, then return to eat.

Spawning only consumes the two spawner farmers' work for one step, so wheat income stays positive while the army grows. Every component is assigned on every call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: eat when steps_since_meal reaches this value
    VILLAGE_EAT_STEPS = 2
    # Village: only warriors this fresh are sent to the Cave (so they can attack on arrival)
    VILLAGE_DISPATCH_MAX_UNFED = 1
    # Cave: warriors return to the Village after this many unfed steps
    CAVE_MAX_STEPS_UNFED = 4
    # Cave: warriors at or below this HP return to the Village
    CAVE_MIN_HP = 1
    # Number of farmer spawns to attempt (requirement: at least one)
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.farmer_spawn_attempts = 0

    def _assign(self, environment, component, group_id, assigned):
        environment.assign_group(component, group_id)
        assigned.add(id(component))

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()
        wheat = environment.farm.wheat

        # 1) Eat: villagers close to starving, most hungry first
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
                # No wheat available: stay in the village
                self._assign(environment, c, "farm", assigned)

        # Free farmers (not eating) are the spawners
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]

        # 2) Spawn one farmer first to meet the farmer requirement
        if (self.farmer_spawn_attempts < self.MAX_FARMER_SPAWNS
                and wheat >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn farmer", assigned)
            wheat -= 10
            self.farmer_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 3) Spawn warriors as often as wheat and free farmers allow
        while wheat >= 12 and len(free_farmers) >= 2:
            pair = free_farmers[:2]
            for c in pair:
                self._assign(environment, c, "spawn warrior", assigned)
            wheat -= 12
            free_farmers = free_farmers[2:]

        # 4) Remaining villagers
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                if c.steps_since_meal <= self.VILLAGE_DISPATCH_MAX_UNFED:
                    # Fresh warrior: go to the Cave and attack
                    self._assign(environment, c, "cave", assigned)
                else:
                    self._assign(environment, c, "farm", assigned)
            else:
                # Farmers keep working the farm
                self._assign(environment, c, "farm", assigned)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.CAVE_MAX_STEPS_UNFED or c.hp <= self.CAVE_MIN_HP:
                    # Too hungry or too hurt: return to eat/recover
                    environment.assign_group(c, "village")
                else:
                    # Attack every step so the Dragon never regenerates
                    environment.assign_group(c, "attack")
            else:
                # Farmers are too weak for the Cave
                environment.assign_group(c, "village")
```