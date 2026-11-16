## Fix

The remaining failure comes from warriors with low HP. In the previous version, `assign_in_village` sent every fed warrior to the Cave regardless of HP. The Cave logic then sent any warrior with `hp <= 2` straight back to the Village. A warrior that arrived with low HP therefore moved to the Cave and was immediately recalled without attacking, which violates "should attack after moving to the Cave."

**Changes**
- **Village:** A warrior is sent to the Cave only if `hp > RETREAT_HP` and it does not need a meal. Warriors that are too weak stay on the farm, where they keep producing wheat and avoid the pointless round trip. Warriors that need a meal still eat first.
- **Cave:** Warriors attack when they are healthy and fed, which covers the arrival step. Warriors that are wounded or hungry return to the Village. Farmers always return.
- Spawning, meal scheduling, and the one-group-per-villager rule are unchanged.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Warrior surge strategy (revised again):
      - Only healthy warriors are sent to the Cave, so every warrior that
        moves there is able to attack on arrival.
      - Fed warriors in the Cave keep attacking; hungry or wounded ones return.
      - Farmers stay in the Village, eat when needed and farm wheat.
      - One farmer is spawned early; surplus wheat then goes to warrior spawns.
    """

    WARRIOR_EAT_AFTER = 1     # warriors eat in the Village once they have been away
    FARMER_EAT_AFTER = 4      # farmers eat before reaching the 6-step starvation limit
    CAVE_MAX_STEPS = 3        # warriors in the Cave attack only while steps_since_meal <= this
    RETREAT_HP = 2            # warriors at or below this HP do not go to / stay in the Cave
    WHEAT_RESERVE = 2
    WARRIOR_COST = 12
    FARMER_COST = 10
    SPAWN_CUTOFF_STEP = 22    # stop spawning late in the fight

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmer_spawned = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        eat_group = []
        warriors = []
        farmers = []

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.WARRIOR_EAT_AFTER:
                    eat_group.append(c)
                else:
                    warriors.append(c)
            else:
                if c.steps_since_meal >= self.FARMER_EAT_AFTER:
                    eat_group.append(c)
                else:
                    farmers.append(c)

        # Each meal costs 1 wheat.
        spendable = wheat - len(eat_group) - self.WHEAT_RESERVE

        for c in eat_group:
            environment.assign_group(c, "eat")

        # Spawning uses non-eating farmers.
        spawn_pool = list(farmers)
        spawned = set()

        if step < self.SPAWN_CUTOFF_STEP:
            # Guarantee at least one farmer spawn when affordable.
            if not self._farmer_spawned and len(spawn_pool) >= 2 \
                    and spendable >= self.FARMER_COST:
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn farmer")
                    spawned.add(id(c))
                spendable -= self.FARMER_COST
                self._farmer_spawned = True

            # Warriors are the main damage source; spawn them whenever affordable.
            while len(spawn_pool) >= 2 and spendable >= self.WARRIOR_COST:
                pair = spawn_pool[:2]
                spawn_pool = spawn_pool[2:]
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawned.add(id(c))
                spendable -= self.WARRIOR_COST

        # Only healthy warriors go to the Cave; weak ones stay and farm.
        for c in warriors:
            if c.hp > self.RETREAT_HP:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        # Remaining farmers keep farming.
        for c in spawn_pool:
            if id(c) not in spawned:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if (c.role == "Warrior"
                    and c.hp > self.RETREAT_HP
                    and c.steps_since_meal <= self.CAVE_MAX_STEPS):
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```