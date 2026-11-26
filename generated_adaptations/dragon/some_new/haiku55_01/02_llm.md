## Strategy: Rotating Warriors with Eating Cycles

**Goal:** Kill the 100 HP Dragon within 30 steps while keeping every villager fed.

**Key observations:**
- Warriors deal 3 damage per attack and farmers deal 1. Warriors are the main damage source.
- The Dragon regenerates 5 HP per step once it has been attacked, so attacks should be continuous to avoid regeneration.
- Villagers starve after 6 steps without eating, and food exists only in the Village. Every villager must cycle back to the Village regularly.
- Spawning a warrior costs 12 wheat and two villagers in the "spawn" group.

**Village logic (`assign_in_village`):**
1. **Eat:** Any villager with `steps_since_meal >= 2` goes to "eat". The margin keeps them well below the 6-step starvation limit.
2. **Spawn:** If there is enough wheat for a spawn plus the meals needed this step, and at least two healthy farmers are free, a pair of farmers goes to "spawn warrior". Spawning adds damage capacity early.
3. **Cave:** Remaining healthy warriors go to "cave" to attack.
4. **Farm:** Remaining farmers stay on "farm" to produce wheat for meals and spawns.

**Cave logic (`assign_in_cave`):**
1. **Retreat to Village:** Villagers with `steps_since_meal >= 3` must return to eat. Villagers with `hp <= 1` also retreat, since a 40% Dragon attack would kill them.
2. **Attack:** All other villagers attack, which keeps the Dragon from regenerating.

**Trade-offs:** The cycle means each warrior attacks for roughly two of every three steps. This is less than perfect uptime, but it protects villagers from starvation and from Dragon attacks. The spawn logic is conservative so that wheat for meals is not exhausted.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
      - Village: villagers that have not eaten for >= 2 steps go to 'eat'.
        Spawn a warrior (pair of farmers in 'spawn warrior') when wheat allows.
        Healthy warriors go to the 'cave' to attack; farmers keep farming.
      - Cave: villagers that have not eaten for >= 3 steps or are almost dead
        return to the 'village'; all others attack the Dragon.
    The cycle keeps the Dragon under continuous attack (no regeneration)
    while ensuring that nobody reaches the 6-step starvation limit.
    """

    EAT_THRESHOLD_VILLAGE = 2
    RETURN_THRESHOLD_CAVE = 3
    MIN_HP_TO_STAY = 2
    WARRIOR_SPAWN_COST = 12

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        to_eat = []
        ready = []
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                to_eat.append(c)
            else:
                ready.append(c)

        # Wheat budget after reserving wheat for this step's meals
        budget = wheat - len(to_eat)

        ready_farmers = [c for c in ready if c.role == "Farmer"]
        ready_warriors = [c for c in ready if c.role == "Warrior"]

        spawn_group = []
        if budget >= self.WARRIOR_SPAWN_COST and len(ready_farmers) >= 2:
            spawn_group = ready_farmers[:2]
            budget -= self.WARRIOR_SPAWN_COST
        spawn_ids = {id(c) for c in spawn_group}

        for c in components:
            if c in to_eat:
                environment.assign_group(c, "eat")
            elif id(c) in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            elif c.role == "Warrior" and c.hp >= self.MIN_HP_TO_STAY:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if (c.steps_since_meal >= self.RETURN_THRESHOLD_CAVE
                    or c.hp <= 1):
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```