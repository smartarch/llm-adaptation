from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: eat when steps_since_meal reaches this value (safe margin before 6)
    VILLAGE_EAT_STEPS = 2
    # Cave: warriors that have not eaten this long must return to the Village
    CAVE_MAX_STEPS_UNFED = 3
    # Cave: warriors at or below this HP retreat to the Village
    CAVE_MIN_HP = 2
    # Spawn limits (attempts)
    MAX_WARRIOR_SPAWNS = 2
    MAX_FARMER_SPAWNS = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warrior_spawn_attempts = 0
        self.farmer_spawn_attempts = 0

    def _assign(self, environment, component, group_id, assigned):
        environment.assign_group(component, group_id)
        assigned.add(id(component))

    def assign_in_village(self, components, environment, group_ids, step: int):
        assigned = set()
        wheat = environment.farm.wheat

        # 1) Eat: villagers that are close to starving (most hungry first)
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.VILLAGE_EAT_STEPS],
            key=lambda c: c.steps_since_meal,
            reverse=True,
        )
        for c in hungry:
            if wheat >= 1:
                self._assign(environment, c, "eat", assigned)
                wheat -= 1
            else:
                # No wheat to eat: keep them in the village (they cannot do anything else useful)
                self._assign(environment, c, "farm", assigned)

        # Free farmers (not eating) are the preferred spawners
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]

        # 2) Spawn warriors (priority: stronger units)
        if (self.warrior_spawn_attempts < self.MAX_WARRIOR_SPAWNS
                and wheat >= 12 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn warrior", assigned)
            wheat -= 12
            self.warrior_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 3) Spawn farmer (one extra farmer for farming)
        if (self.farmer_spawn_attempts < self.MAX_FARMER_SPAWNS
                and wheat >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn farmer", assigned)
            wheat -= 10
            self.farmer_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 4) Remaining units
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                # Fed warriors (steps_since_meal < 2) go to fight
                self._assign(environment, c, "cave", assigned)
            else:
                # Farmers keep working the farm
                self._assign(environment, c, "farm", assigned)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.CAVE_MAX_STEPS_UNFED or c.hp <= self.CAVE_MIN_HP:
                    # Hungry or badly hurt: go eat / recover
                    environment.assign_group(c, "village")
                else:
                    # Fed and healthy: keep hitting the Dragon
                    environment.assign_group(c, "attack")
            else:
                # Farmers are too weak for the Cave: go back to the Village
                environment.assign_group(c, "village")