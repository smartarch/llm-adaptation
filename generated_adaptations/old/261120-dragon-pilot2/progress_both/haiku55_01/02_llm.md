## Strategy: Threshold-based warrior rotation with farmer-funded spawning

**Core idea:** Farmers stay in the Village to farm, eat, and fund spawns. Warriors rotate between the Village (to eat) and the Cave (to attack), so no one goes more than a few steps without food.

**Village rules (`assign_in_village`):**
1. **Eating first.** Any villager whose `steps_since_meal` has reached its threshold goes to "eat" while wheat lasts. Farmers eat at 3 steps, and warriors eat at 2 steps. Eating is processed from the longest-unfed villager down, and each meal reduces a local wheat counter.
2. **Warrior dispatch.** Warriors that just ate (or are recently fed) and are not eating now go to "cave" to attack.
3. **Spawning with a reserve.** Remaining farmers are used as spawners in pairs. Warriors are preferred, since they deal 3 damage per attack, so the strategy spawns a Warrior when wheat covers 12 plus a meal reserve for all villagers. Otherwise it spawns a Farmer when wheat covers 10 plus the reserve. Spawning is limited to the early game (step ≤ 20) so that wheat is kept for meals.
4. **Default.** Everyone else farms.

**Cave rules (`assign_in_cave`):**
1. Farmers have no useful role in the Cave (they deal 1 damage and cannot be sustained there), so they return to the Village.
2. Warriors with `steps_since_meal ≥ 3` return to the Village to eat. This keeps them under the 6-step starvation limit, since the return trip takes one step and eating happens on arrival.
3. All other warriors attack the Dragon. Because warriors rotate, the Dragon is attacked nearly every step once there are several warriors, which avoids its regeneration.

**Requirement coverage:**
- All warriors go to the Cave and attack after arriving.
- All farmers stay in the Village.
- Farmers and warriors are spawned early (steps ≤ 20) when wheat allows.
- Meals are planned with thresholds so nobody reaches 6 unfed steps.
- Warriors with 3+ unfed steps are not sent to the Cave.
- Villagers in the Cave with 3+ unfed steps move back to the Village.

**Limitations:** The exact spawn and eating timing depends on how the engine counts `steps_since_meal`. The thresholds are chosen with a margin below the 6-step limit. The wheat reserve is a heuristic and may need tuning.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, and fund spawns).
    Warriors rotate between Village (eat) and Cave (attack) based on
    steps_since_meal so that nobody starves.
    """

    FARMER_EAT_THRESHOLD = 3
    WARRIOR_EAT_THRESHOLD = 2
    CAVE_RETURN_THRESHOLD = 3
    SPAWN_WINDOW = 20  # only spawn early, keep wheat for meals later

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Process the longest-unfed villagers first.
        ordered = sorted(components, key=lambda c: c.steps_since_meal, reverse=True)

        eaters = []
        warriors_ready = []
        free_farmers = []
        remaining = []

        # 1) Decide who eats (eating has priority, limited by available wheat).
        for c in ordered:
            s = c.steps_since_meal
            threshold = self.WARRIOR_EAT_THRESHOLD if c.role == "Warrior" else self.FARMER_EAT_THRESHOLD
            if s >= threshold and wheat > 0:
                eaters.append(c)
                wheat -= 1
            else:
                remaining.append(c)

        # 2) Split the rest into warriors (dispatch to cave) and farmers (spawn/farm).
        for c in remaining:
            if c.role == "Warrior":
                warriors_ready.append(c)
            else:
                free_farmers.append(c)

        # Reserve wheat for one meal per villager in the next step(s).
        reserve = len(components)

        spawn_warrior_groups = []
        spawn_farmer_groups = []
        spawn_members = set()

        # 3) Spawning (early game only). Farmers act as spawners in pairs.
        if step <= self.SPAWN_WINDOW:
            while len(free_farmers) - len(spawn_members) >= 2:
                available = [f for f in free_farmers if id(f) not in spawn_members]
                pair = available[:2]
                if wheat - reserve >= 12:
                    spawn_warrior_groups.append(pair)
                    wheat -= 12
                elif wheat - reserve >= 10:
                    spawn_farmer_groups.append(pair)
                    wheat -= 10
                else:
                    break
                for f in pair:
                    spawn_members.add(id(f))

        spawn_ids = set()
        for grp in spawn_warrior_groups + spawn_farmer_groups:
            for f in grp:
                spawn_ids.add(id(f))

        # Assign groups
        for c in eaters:
            environment.assign_group(c, "eat")

        for grp in spawn_warrior_groups:
            for f in grp:
                environment.assign_group(f, "spawn warrior")

        for grp in spawn_farmer_groups:
            for f in grp:
                environment.assign_group(f, "spawn farmer")

        for c in warriors_ready:
            if dragon_hp > 0 and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        for f in free_farmers:
            if id(f) in spawn_ids:
                continue
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers do not belong in the cave: send them home.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Warrior is getting hungry: go eat before it starves.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```