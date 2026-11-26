## Diagnosis

At step 28 the Village had 1 wheat left after this step's meals, spawns, and farming, but two villagers (George, Donna) needed to eat in the next step. Donna then starved at step 30. The reserve rule only looked one step ahead, so it missed two problems:

1. **Spawning cuts future income.** The two farmers used for a spawn do not farm that step, so their 5-wheat farming income is lost. The reserve did not account for that.
2. **Warriors returning from the Cave also need meals.** Those arriving in the Village soon were not counted in the reserve.

## Changes

1. **Two-step reserve:** The reserve now counts every villager who will need a meal within the next two steps (`steps_since_meal + 2 >= threshold`), including warriors heading back from the Cave. Wheat is held back for all of them before any spawn.
2. **Spawn safety margin:** A spawn happens only when the surplus covers the 12-wheat cost plus a 2-wheat margin. This accounts for the farming income that the spawned farmers no longer produce.
3. **Unchanged:** Attack window (hunger <= 3), finishing blow (hunger <= 3), return to the Village at hunger >= 4, farmers eating at 3, and warriors eating at 2.

The seed-3 kill-speed issue may still fail the 30-step deadline, since spawning is now more conservative. I can't see the simulation results, so the win-rate effect is unverified.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with staggered warriors, a two-step wheat reserve, and
    warrior spawning from safe surplus wheat.

    Village:
      - Warriors that just ate (steps 0) go to the Cave.
      - If no warrior is attacking in the Cave, a warrior with steps 1 also
        goes, so the Dragon does not get free regeneration steps.
      - Hungry villagers eat first (most hungry first, limited by wheat).
      - Wheat is reserved for every villager who will need a meal within the
        next two steps (including warriors coming back from the Cave).
      - Surplus wheat, beyond the reserve plus a safety margin, spawns
        Warriors from pairs of free farmers.
      - Everyone else farms.

    Cave:
      - Warriors attack while steps_since_meal <= 3.
      - Finishing blow: if the warriors still at steps <= 3 can kill the
        Dragon this step, they all attack.
      - Other warriors return to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 2     # a warrior in the Village eats at this hunger
    FARMER_EAT_THRESHOLD = 3      # farmers eat before the 6-step limit
    CAVE_ATTACK_MAX_STEPS = 3     # warriors in the Cave attack while steps <= 3
    FINISH_MAX_STEPS = 3          # finishing blow stays inside the safe window
    SPAWN_WARRIOR_WHEAT = 12
    SPAWN_MARGIN = 2              # covers farming income lost by spawning farmers
    RESERVE_HORIZON = 2           # plan meals this many steps ahead
    DAMAGE_PER_WARRIOR = 3

    def _threshold(self, c):
        return self.WARRIOR_EAT_THRESHOLD if c.role == "Warrior" else self.FARMER_EAT_THRESHOLD

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def give(c, group):
            if id(c) in assigned:
                return
            environment.assign_group(c, group)
            assigned.add(id(c))

        # Warriors already attacking in the Cave (alive, not starving).
        cave_attackers = sum(
            1 for w in environment.warriors
            if w.location == "Cave" and w.hp > 0
            and w.steps_since_meal <= self.CAVE_ATTACK_MAX_STEPS
        )

        # 1) Warriors heading to the Cave; collect villagers who need food.
        eat_candidates = []
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal == 0:
                    give(c, "cave")
                    cave_attackers += 1
                    continue
                if c.steps_since_meal == 1 and cave_attackers == 0:
                    give(c, "cave")
                    cave_attackers += 1
                    continue
            if c.steps_since_meal >= self._threshold(c):
                eat_candidates.append(c)

        # 2) Feed the most hungry first, limited by wheat.
        eat_candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)
        n_fed = min(len(eat_candidates), max(0, wheat))
        for c in eat_candidates[:n_fed]:
            give(c, "eat")
        wheat_left = wheat - n_fed

        # 3) Reserve wheat for every villager who will need a meal within the
        #    next RESERVE_HORIZON steps and is not being fed now. This includes
        #    hungry villagers that got no wheat and warriors in the Cave that
        #    will return soon.
        remaining = [c for c in components if id(c) not in assigned]
        reserve = sum(1 for c in eat_candidates if id(c) not in assigned)
        reserve += sum(
            1 for c in remaining
            if c.steps_since_meal + self.RESERVE_HORIZON >= self._threshold(c)
        )
        for w in environment.warriors:
            if w.location == "Cave" and w.hp > 0 and w.steps_since_meal >= 2:
                reserve += 1

        # 4) Spawn Warriors from surplus wheat (with a margin) and free farmers.
        free_farmers = [c for c in remaining if c.role == "Farmer"]
        surplus = wheat_left - reserve - self.SPAWN_MARGIN
        n_spawns = 0
        if surplus >= self.SPAWN_WARRIOR_WHEAT:
            n_spawns = min(surplus // self.SPAWN_WARRIOR_WHEAT, len(free_farmers) // 2)
        for c in free_farmers[:2 * n_spawns]:
            give(c, "spawn warrior")

        # 5) Everyone else works on the farm.
        for c in components:
            if id(c) not in assigned:
                give(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def give(c, group):
            if id(c) in assigned:
                return
            environment.assign_group(c, group)
            assigned.add(id(c))

        # Warriors that are still in the safe window and could attack this step.
        finish_candidates = [c for c in components
                             if c.role == "Warrior" and c.hp > 0
                             and c.steps_since_meal <= self.FINISH_MAX_STEPS]
        potential_damage = len(finish_candidates) * self.DAMAGE_PER_WARRIOR
        finishing_blow = (len(finish_candidates) > 0
                          and potential_damage >= environment.dragon.hp)

        for c in components:
            if c.role == "Warrior" and c.hp > 0:
                if c.steps_since_meal <= self.CAVE_ATTACK_MAX_STEPS:
                    give(c, "attack")
                elif finishing_blow and c in finish_candidates:
                    give(c, "attack")
                else:
                    give(c, "village")
            else:
                give(c, "village")
```