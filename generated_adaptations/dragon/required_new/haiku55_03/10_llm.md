## Diagnosis

The two remaining failures are both "Dragon not killed within 30 steps". Starvation is no longer the issue. The fight is too slow because the team's damage output is too low for the step budget. The main lever is army size, but the current code spawns at most one pair of farmers per step, and only when wheat is left over after feeding. Over 30 steps this leaves warriors too few to finish the fight.

## Changes

1. **Multiple spawns per step:** The Village logic spawns `min(wheat_left // 12, free_farmers // 2)` warriors in one step, not just one. Wheat is still reserved for meals first, so nobody starves.
2. **Farmers are kept as spawn sources only as needed:** Spawning draws from farmers who are not eating, so farming income is preserved for the majority of the time.
3. **Cave rotation unchanged:** Warriors attack while `steps_since_meal <= 2`, leave at 3, and the finishing-blow exception still applies to warriors with hunger up to 3. This keeps all villagers within the starvation limit.
4. **Attack coverage unchanged:** A warrior with `steps_since_meal == 1` is sent to the Cave if no warrior is attacking, so the Dragon does not get free regeneration steps.

Because the simulation results are not visible to me, I can't confirm the exact win-rate change. These edits target the speed problem directly, and the starvation rules are unchanged.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with staggered warrior attacks and aggressive spawning.

    Village:
      - Warriors that just ate (steps 0) go to the Cave.
      - If no warrior is attacking in the Cave, a warrior with steps 1 also
        goes, so the Dragon never gets a free regeneration step.
      - Hungry villagers eat first (most hungry first, limited by wheat).
      - With leftover wheat, as many Warriors as possible are spawned from
        pairs of free farmers (multiple spawns per step).
      - Everyone else farms.

    Cave:
      - Warriors attack while steps_since_meal <= 2.
      - Finishing blow: if the warriors still safe (steps <= 3) can kill the
        Dragon this step, they all attack.
      - Everyone else returns to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 2     # a warrior in the Village eats at this hunger
    FARMER_EAT_THRESHOLD = 3      # farmers eat before the 6-step limit
    CAVE_ATTACK_MAX_STEPS = 2     # warriors in the Cave attack while steps <= 2
    FINISH_MAX_STEPS = 3          # finishing blow allowed up to this hunger
    SPAWN_WARRIOR_WHEAT = 12
    DAMAGE_PER_WARRIOR = 3

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

        # 1) Warriors heading to the Cave.
        eat_candidates = []
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal == 0:
                    give(c, "cave")
                    cave_attackers += 1
                elif c.steps_since_meal == 1 and cave_attackers == 0:
                    give(c, "cave")
                    cave_attackers += 1
                elif c.steps_since_meal >= self.WARRIOR_EAT_THRESHOLD:
                    eat_candidates.append(c)
            else:
                if c.steps_since_meal >= self.FARMER_EAT_THRESHOLD:
                    eat_candidates.append(c)

        # 2) Feed the most hungry first, limited by wheat.
        eat_candidates.sort(key=lambda c: c.steps_since_meal, reverse=True)
        n_fed = min(len(eat_candidates), max(0, wheat))
        for c in eat_candidates[:n_fed]:
            give(c, "eat")
        wheat_left = wheat - n_fed

        # 3) Spawn as many Warriors as wheat and free farmers allow.
        free_farmers = [c for c in components
                        if id(c) not in assigned and c.role == "Farmer"]
        n_spawns = min(wheat_left // self.SPAWN_WARRIOR_WHEAT, len(free_farmers) // 2)
        for c in free_farmers[:2 * n_spawns]:
            give(c, "spawn warrior")

        # 4) Everyone else works on the farm.
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

        # Warriors that are still safe enough to attack this step.
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