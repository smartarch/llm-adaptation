## Revised strategy: front-loaded warrior spawning and staggered cave rotation

**What went wrong:** The Dragon ended at 94 HP and the warriors were all killed. Average attackers per step was only 0.5. The old rule sent every fed warrior to the Cave at once, then pulled them back together to eat, leaving most turns without an attack. Spawning also took villagers off the cave task too late, and farmers were spawned after the warriors were already exposed.

**Changes:**

1. **Spawn warriors early and keep spawning them.** Spawners are not consumed, so farmers serve as spawners while the warrior count is below a target of 5. Each spawn is only allowed if the wheat left over still covers feeding every villager that needs a meal. Farmers are spawned only after the warrior target is met.
2. **Feed before fighting.** Any villager with `steps_since_meal >= 2` eats in the Village. Warriors arriving in the Cave are always fed.
3. **Staggered cave rotation.** The Cave is kept with a target number of attackers (about half the warriors, minimum 2), so at least one warrior attacks almost every step and the Dragon rarely regenerates. Warriors that are fed and not needed in the Cave stay in the Village to eat and wait their turn.
4. **Retreat before starvation.** A warrior in the Cave with `steps_since_meal >= 3` returns to the Village, leaving a margin before the 6-step starvation limit.
5. **Farmers never enter the Cave.** They keep farming, which supplies the wheat for meals and spawns.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Village:
      - Feed anyone with steps_since_meal >= 2.
      - Spawn warriors early (farmers used as spawners, they are not consumed),
        keeping enough wheat to feed everyone. Spawn farmers only after the
        warrior target is reached.
      - Fed warriors go to the Cave until enough attackers are there;
        the rest wait in the Village (rotation keeps attacks almost every step).
      - Farmers keep farming.
    Cave:
      - Warriors with steps_since_meal < 3 attack (staggered by count target).
      - Hungrier warriors and all farmers return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 2
    CAVE_RETURN_HUNGER = 3
    WARRIOR_TARGET = 5
    FARMER_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10
    MIN_CAVE_ATTACKERS = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def _count(self, components, role):
        return sum(1 for c in components if c.role == role)

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first.
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        # 2) Spawning (one spawn group per step, leaving wheat for feeding).
        total_warriors = self.warriors_spawned + self._count(components, "Warrior")
        free = [c for c in components if c not in assigned]
        farmers_free = [c for c in free if c.role == "Farmer"]
        others_free = [c for c in free if c.role != "Farmer"]
        reserve = len(components)  # keep wheat for next step's meals

        if total_warriors < self.WARRIOR_TARGET and budget - reserve >= self.WARRIOR_COST:
            spawners = (farmers_free + others_free)[:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn warrior")
                    assigned.add(c)
                budget -= self.WARRIOR_COST
                self.warriors_spawned += 1
        elif (self.farmers_spawned < self.FARMER_TARGET
              and total_warriors >= self.WARRIOR_TARGET
              and budget - reserve >= self.FARMER_COST):
            spawners = [c for c in farmers_free if c not in assigned][:2]
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn farmer")
                    assigned.add(c)
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Everyone else.
        remaining = [c for c in components if c not in assigned]
        fed_warriors = [c for c in remaining
                        if c.role == "Warrior" and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE]
        cave_now = getattr(self, "_cave_count", 0)
        want_in_cave = max(self.MIN_CAVE_ATTACKERS, (len(fed_warriors) + cave_now + 1) // 2)
        slots = max(0, want_in_cave - cave_now)

        for c in remaining:
            if c in fed_warriors and slots > 0:
                environment.assign_group(c, "cave")
                slots -= 1
            else:
                environment.assign_group(c, "farm")

        self._cave_count = 0  # recomputed in the cave phase

    def assign_in_cave(self, components, environment, group_ids, step: int):
        attackers = 0
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_RETURN_HUNGER:
                environment.assign_group(c, "attack")
                attackers += 1
            elif c.role == "Warrior":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "village")
        self._cave_count = attackers
```