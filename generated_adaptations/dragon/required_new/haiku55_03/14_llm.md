## Diagnosis

Only seed 3 still fails, with "Dragon not killed within 30 steps". The starvation rules hold, so the remaining gap is in the final fight. Warriors are sent home at `steps_since_meal >= 4` to protect them from starvation, but that limit is stricter than it needs to be on the step that ends the fight.

A warrior with `steps_since_meal = 5` has not yet starved. Starvation begins only after 6 consecutive steps without eating, and a starving villager deals no damage. So a warrior at 5 can still attack on the step it is in the Cave. If the attacking group deals at least the Dragon's remaining HP, the Dragon dies that step and nobody needs to travel or eat afterward.

## Changes

1. **Finishing blow extended to hunger 5:** `FINISH_MAX_STEPS` is raised from 3 to 5. When the warriors that can still attack (`steps_since_meal <= 5`) would deal at least the Dragon's current HP, all of them attack this step, even those past the normal attack window.
2. **Safety preserved:** A warrior at hunger 5 is not starving, so it still deals full damage. The exception only applies when the attack is guaranteed to kill the Dragon. If it does not, the normal rule sends those warriors home.
3. **Rest unchanged:** Attack window (`<= 3`), return threshold (`>= 4`), eating thresholds, and spawning logic are the same as before.

Since I can't see the simulation, the win-rate effect is unverified. The change targets the last-step kill directly and does not relax any starvation rule.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with a longer attack window and a safe finishing blow.

    Village:
      - Warriors that just ate (steps 0) go to the Cave.
      - If no warrior is attacking in the Cave, a warrior with steps 1 also
        goes, so the Dragon does not get free regeneration steps.
      - Hungry villagers eat first (most hungry first, limited by wheat).
      - Leftover wheat spawns Warriors from pairs of free farmers.
      - Everyone else farms.

    Cave:
      - Warriors attack while steps_since_meal <= 3.
      - Finishing blow: if the warriors that are not yet starving (steps <= 5)
        can kill the Dragon this step, all of them attack. A villager is only
        starving after 6 steps without a meal, so attacking at 5 is safe.
      - Other warriors return to the Village to eat.
    """

    WARRIOR_EAT_THRESHOLD = 2     # a warrior in the Village eats at this hunger
    FARMER_EAT_THRESHOLD = 3      # farmers eat before the 6-step limit
    CAVE_ATTACK_MAX_STEPS = 3     # warriors in the Cave attack while steps <= 3
    FINISH_MAX_STEPS = 5          # finishing blow allowed while not yet starving
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

        # Warriors that are not yet starving and could attack this step.
        finish_candidates = [c for c in components
                             if c.role == "Warrior" and c.hp > 0
                             and c.steps_since_meal <= self.FINISH_MAX_STEPS]
        potential_damage = len(finish_candidates) * self.DAMAGE_PER_WARRIOR
        finishing_blow = (len(finish_candidates) > 0
                          and potential_damage >= environment.dragon.hp)

        for c in components:
            if c.role == "Warrior" and c.hp > 0:
                if finishing_blow and c in finish_candidates:
                    give(c, "attack")
                elif c.steps_since_meal <= self.CAVE_ATTACK_MAX_STEPS:
                    give(c, "attack")
                else:
                    give(c, "village")
            else:
                give(c, "village")
```