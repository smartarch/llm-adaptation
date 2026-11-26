from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Fast Dragon hunt with staggered warriors, a wheat reserve for upcoming
    meals, and warrior spawning from surplus wheat.

    Village:
      - Warriors that just ate (steps 0) go to the Cave.
      - If no warrior is attacking in the Cave, a warrior with steps 1 also
        goes, so the Dragon does not get free regeneration steps.
      - Hungry villagers eat first (most hungry first, limited by wheat).
      - Wheat is reserved for villagers who will need a meal next step.
      - Surplus wheat spawns Warriors from pairs of free farmers.
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

        # 3) Reserve wheat for villagers that will need a meal next step
        #    but are not being fed now.
        remaining = [c for c in components if id(c) not in assigned]
        reserve = sum(
            1 for c in remaining
            if c.steps_since_meal + 1 >= self._threshold(c)
        )
        # Villagers that were hungry but got no wheat also still need food.
        reserve += sum(1 for c in eat_candidates if id(c) not in assigned)

        # 4) Spawn Warriors from surplus wheat and free farmers.
        free_farmers = [c for c in remaining if c.role == "Farmer"]
        surplus = wheat_left - reserve
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