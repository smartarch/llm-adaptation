## Strategy: Threshold-based feeding, scheduled spawning, and rotating warrior attacks

**Village phase**
- **Feeding first:** Any villager with `steps_since_meal >= 2` goes to "eat". This keeps everyone far below the 6-step starvation limit and lets warriors reach the Cave with a fresh meal.
- **Spawning:** Spawning uses leftover wheat after feeding. The strategy first tries to spawn two warriors (2 × 12 wheat), using two spare villagers, preferring farmers, in the "spawn warrior" group. Once two warriors have been spawned, it spawns one farmer (10 wheat) from two spare villagers in the "spawn farmer" group. Spawn counts are tracked internally, since component attributes don't update during assignment.
- **Warriors:** Any warrior that is not eating or spawning and has `steps_since_meal < 2` goes to the "cave". Warriors that have just eaten are therefore ready to fight.
- **Farmers:** All remaining farmers stay in the "farm" group.

**Cave phase**
- **Warriors:** Warriors with `steps_since_meal < 3` attack. This keeps them from starving and meets the recommendation not to fight while hungry. Warriors at 3 or more steps since their last meal go back to the "village" to eat.
- **Farmers:** Farmers never fight. Any farmer in the Cave returns to the "village".

**Design notes**
- Warriors rotate between Cave and Village, so several warriors are usually attacking while others eat. This keeps the Dragon from regenerating for long stretches.
- The strategy stays within the mandatory requirements: all warriors go to the Cave and attack, all farmers stay in the Village, two warriors and one farmer are spawned, and no villager goes 6 steps without eating.
- Because spawning competes with feeding for wheat, the feeding rule runs first so starvation is never traded for a spawn.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Village: feed anyone with steps_since_meal >= 2; spawn 2 warriors and then
      1 farmer when wheat allows (spawners are taken from non-eating villagers,
      preferring farmers); warriors that are fed and not spawning go to the Cave;
      farmers keep farming.
    - Cave: warriors with steps_since_meal < 3 attack; hungrier warriors and all
      farmers return to the Village.
    """

    EAT_THRESHOLD_VILLAGE = 2   # eat when this many steps have passed without a meal
    CAVE_ATTACK_LIMIT = 3       # warriors in the cave attack only if steps_since_meal < this
    WARRIOR_SPAWN_TARGET = 2
    FARMER_SPAWN_TARGET = 1
    WARRIOR_COST = 12
    FARMER_COST = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0
        self.farmers_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        budget = environment.farm.wheat
        assigned = set()

        # 1) Feed hungry villagers first (eating consumes 1 wheat each).
        for c in components:
            if c.steps_since_meal >= self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "eat")
                assigned.add(c)
                budget -= 1

        remaining = [c for c in components if c not in assigned]

        # Helper: pick spawners, preferring farmers so warriors stay available.
        def pick_spawners(n):
            farmers = [c for c in remaining if c.role == "Farmer" and c not in assigned]
            others = [c for c in remaining if c.role != "Farmer" and c not in assigned]
            return (farmers + others)[:n]

        # 2) Spawning: at most one spawn group per step.
        spawned_this_step = False
        if self.warriors_spawned < self.WARRIOR_SPAWN_TARGET and budget >= self.WARRIOR_COST:
            spawners = pick_spawners(2)
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn warrior")
                    assigned.add(c)
                budget -= self.WARRIOR_COST
                self.warriors_spawned += 1
                spawned_this_step = True

        if (not spawned_this_step
                and self.warriors_spawned >= self.WARRIOR_SPAWN_TARGET
                and self.farmers_spawned < self.FARMER_SPAWN_TARGET
                and budget >= self.FARMER_COST):
            spawners = pick_spawners(2)
            if len(spawners) == 2:
                for c in spawners:
                    environment.assign_group(c, "spawn farmer")
                    assigned.add(c)
                budget -= self.FARMER_COST
                self.farmers_spawned += 1

        # 3) Everyone else: fed warriors go to the Cave, farmers keep farming.
        for c in components:
            if c in assigned:
                continue
            if c.role == "Warrior" and c.hp > 0 and c.steps_since_meal < self.EAT_THRESHOLD_VILLAGE:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior" and c.steps_since_meal < self.CAVE_ATTACK_LIMIT:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```