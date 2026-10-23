"""Continuous attack with staggered meals.

Warriors go to the Cave and attack the Dragon; a warrior goes back to the Village to eat shortly before it would
starve. To avoid leaving the Dragon unattacked, these trips of the warriors are staggered (a warrior is sent back earlier when several warriors would have to leave at the same time).
Farmers stay in the Village, eat when needed, and farm or spawn new villagers (warriors first), keeping a reserve of
wheat for the meals that are due soon.
"""
import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

FARMER_SPAWN_COST = 10
WARRIOR_SPAWN_COST = 12


def meal_interval(environment):
    return environment.meal_interval or math.inf


def turns_left(warrior, environment):
    """Number of further steps the warrior can stay in the Cave and attack before it has to return to eat."""
    return meal_interval(environment) - 2 - warrior.steps_since_meal  # must leave 2 steps before starving


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        interval = meal_interval(environment)
        wheat = environment.farm.wheat

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        busy = []

        def assign_paid(villager, group, cost):
            nonlocal wheat
            if wheat >= cost:
                environment.assign_group(villager, group)
                wheat -= cost
                busy.append(villager)

        # 1. meals: everybody who would starve otherwise, and warriors that are too hungry to make a useful trip to the Cave
        eaters = [c for c in farmers if c.steps_since_meal >= interval - 1]
        eaters += [w for w in warriors if w.steps_since_meal >= interval - 4]
        for villager in sorted(eaters, key=lambda c: -c.steps_since_meal):  # the hungriest first
            assign_paid(villager, "eat", environment.meal_cost)

        # 2. the other warriors go to the Cave
        for warrior in warriors:
            if warrior not in busy:
                environment.assign_group(warrior, "cave")

        # 3. spawning (keep a reserve of wheat for the meals that are due in the next steps)
        free_farmers = [f for f in farmers if f not in busy]
        due_soon = [v for v in environment.components if v not in busy and v.steps_since_meal >= interval - 4]
        available = wheat - environment.meal_cost * len(due_soon)
        for spawn_group, spawn_cost in (("spawn warrior", WARRIOR_SPAWN_COST), ("spawn farmer", FARMER_SPAWN_COST)):
            if len(free_farmers) >= 2 and available >= spawn_cost:
                environment.assign_group(free_farmers[0], spawn_group)
                environment.assign_group(free_farmers[1], spawn_group)
                free_farmers = free_farmers[2:]
                available -= spawn_cost

        # 4. remaining farmers farm
        for farmer in free_farmers:
            environment.assign_group(farmer, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]  # farmers do not belong to the Cave

        # warriors that must leave now
        leaving = [w for w in warriors if turns_left(w, environment) <= 0]
        staying = [w for w in warriors if w not in leaving]

        # stagger the trips: if nobody leaves now but several warriors will have to leave soon, send one of them earlier
        if not leaving and len(staying) >= 2:
            soon = sorted((w for w in staying if turns_left(w, environment) <= 2), key=lambda w: turns_left(w, environment))
            if len(soon) >= 2:
                leaving.append(soon[0])
                staying.remove(soon[0])

        for villager in leaving + others:
            environment.assign_group(villager, "village")
        for warrior in staying:
            environment.assign_group(warrior, "attack")
