## Diagnosis

The new failures come from my last change. Raising `FINISH_MAX_STEPS` to 5 let warriors with 4 or 5 steps without a meal stay in the Cave. The test treats any villager that has gone 4 steps without eating and is still in the Cave as a violation, so the finishing-blow exception has to stay within the safe window (steps <= 3). Seed 3 still misses the 30-step deadline, so the fight needs more damage per step without weakening the hunger rules.

## Changes

1. **Revert the finishing blow to hunger 3:** `FINISH_MAX_STEPS` returns to 3, which clears the "still in the Cave" violations.
2. **Farmers eat at 4 steps instead of 3:** A farmer that has gone 4 steps without eating still has a step to spare before the 6-step limit. Eating later saves about a quarter of the meal wheat, which goes toward warrior spawns.
3. **Spawning keeps priority over farming:** Leftover wheat still spawns warriors from free farmers, as many as wheat and farmers allow.
4. **Attack and return rules unchanged:** Warriors attack at hunger <= 3, return at >= 4, and a warrior at hunger 1 covers the Cave when it would otherwise be empty.

I can't see the simulation, so the win-rate effect is unverified. The change targets wheat efficiency and keeps every starvation check inside the safe window.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with staggered warriors, wheat-efficient meals, and
    aggressive warrior spawning.

    Village:
      - Warriors that just ate (steps 0) go to the Cave.
      - If no warrior is attacking in the Cave, a warrior with steps 1 also
        goes, so the Dragon does not get free regeneration steps.
      - Hungry villagers eat first (most hungry first, limited by wheat).
      - Leftover wheat spawns Warriors from pairs of free farmers.
      - Everyone else farms.

    Cave:
      - Warriors attack while steps_since_meal <= 3.
      - Finishing blow: if the warriors still at steps <= 3 can kill the
        Dragon this step, they all attack.
      - Other warriors return to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 2     # a warrior in the Village eats at this hunger
    FARMER_EAT_THRESHOLD = 4      # farmers eat at 4 steps (limit is 6)
    CAVE_ATTACK_MAX_STEPS = 3     # warriors in the Cave attack while steps <= 3
    FINISH_MAX_STEPS = 3          # finishing blow stays inside the safe window
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