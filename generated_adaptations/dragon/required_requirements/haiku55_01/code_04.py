from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: warriors/farmers eat when steps_since_meal reaches this value
    VILLAGE_EAT_STEPS = 2
    # Cave: warriors are kept attacking until they have gone this many steps unfed
    # (starvation happens at 6, leaving 1 step for the return trip)
    CAVE_MAX_STEPS_UNFED = 4
    # Cave: warriors at or below this HP retreat to the Village
    CAVE_MIN_HP = 1
    # Spawn limits (attempts)
    MAX_WARRIOR_SPAWNS = 3
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

        # 1) Eat: villagers close to starving, most hungry first
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
                # No wheat available: stay in the village
                self._assign(environment, c, "farm", assigned)

        # Free farmers (not eating) are the spawners
        free_farmers = [c for c in components
                        if c.role == "Farmer" and id(c) not in assigned]

        # 2) Spawn warriors
        if (self.warrior_spawn_attempts < self.MAX_WARRIOR_SPAWNS
                and wheat >= 12 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn warrior", assigned)
            wheat -= 12
            self.warrior_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 3) Spawn farmer
        if (self.farmer_spawn_attempts < self.MAX_FARMER_SPAWNS
                and wheat >= 10 and len(free_farmers) >= 2):
            for c in free_farmers[:2]:
                self._assign(environment, c, "spawn farmer", assigned)
            wheat -= 10
            self.farmer_spawn_attempts += 1
            free_farmers = free_farmers[2:]

        # 4) Remaining villagers
        for c in components:
            if id(c) in assigned:
                continue
            if c.role == "Warrior":
                # Warriors that are not hungry go to the Cave to attack
                self._assign(environment, c, "cave", assigned)
            else:
                # Farmers keep working the farm
                self._assign(environment, c, "farm", assigned)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= self.CAVE_MAX_STEPS_UNFED or c.hp <= self.CAVE_MIN_HP:
                    # Too hungry or too hurt: return to eat/recover
                    environment.assign_group(c, "village")
                else:
                    # Keep attacking so the Dragon never regenerates
                    environment.assign_group(c, "attack")
            else:
                # Farmers are too weak for the Cave
                environment.assign_group(c, "village")