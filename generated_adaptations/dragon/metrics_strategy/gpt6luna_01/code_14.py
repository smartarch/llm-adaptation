from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._warrior_spawn_requests = 0
        self._farmer_spawn_requests = 0

    @staticmethod
    def _assign(environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        meals_this_turn = 0

        for villager in components:
            if villager.role == "Warrior":
                # Feed on arrival rather than sending a hungry Warrior back out.
                if villager.steps_since_meal >= 3:
                    self._assign(environment, villager, "eat")
                    meals_this_turn += 1
                else:
                    self._assign(environment, villager, "cave")
            elif villager.steps_since_meal >= 5:
                self._assign(environment, villager, "eat")
                meals_this_turn += 1
            else:
                farmers.append(villager)

        # Save wheat for meals and a small reserve. Spawn Warriors first.
        wheat = max(0, environment.farm.wheat - meals_this_turn - 2)
        spawn_plans = []
        if self._warrior_spawn_requests < 2:
            spawn_plans.append(("spawn warrior", 12, "warrior"))
        if self._farmer_spawn_requests < 2:
            spawn_plans.append(("spawn farmer", 10, "farmer"))

        for group, cost, kind in spawn_plans:
            if len(farmers) < 2 or wheat < cost:
                continue

            pair = farmers[:2]
            farmers = farmers[2:]
            for villager in pair:
                self._assign(environment, villager, group)

            wheat -= cost
            if kind == "warrior":
                self._warrior_spawn_requests += 1
            else:
                self._farmer_spawn_requests += 1

        for villager in farmers:
            self._assign(environment, villager, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = []

        for villager in components:
            if villager.role == "Warrior":
                warriors.append(villager)
            else:
                self._assign(environment, villager, "village")

        # At hunger 5, return all affected Warriors before they become too weak.
        urgent = [w for w in warriors if w.steps_since_meal >= 5]
        returning = list(urgent)

        # Otherwise start one meal trip at hunger 3 if another Warrior can
        # continue attacking. With only one Warrior, wait until hunger 4.
        if not urgent:
            candidates = [w for w in warriors if w.steps_since_meal >= 4]
            if not candidates and len(warriors) > 1:
                candidates = [w for w in warriors if w.steps_since_meal >= 3]
            if candidates:
                returning.append(max(candidates, key=lambda w: w.steps_since_meal))

        for villager in warriors:
            if any(villager is w for w in returning):
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")