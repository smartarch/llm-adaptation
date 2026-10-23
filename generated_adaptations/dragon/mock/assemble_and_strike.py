"""Assemble the warriors in the Village and strike together.

The warriors wait in the Village (farming) while new warriors are spawned. Once there are enough warriors (or it is time
to start the attack), all of them eat and then go to the Cave at the same time,
so they attack the Dragon simultaneously. They attack until one of them has to return, then all of them return
together, prepare again, and strike again.
Farmers stay in the Village, eat when needed, and farm or spawn new villagers (warriors first).
"""
import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

FARMER_SPAWN_COST = 10
WARRIOR_SPAWN_COST = 12

WAVE_SIZE = 4  # number of warriors needed to start the strike
LATEST_START = 10  # start the strike at this step at the latest (with any number of warriors)


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
        warriors_in_cave = [c for c in environment.components if c.role == "Warrior" and c not in components]

        # the strike starts when enough warriors are assembled (and no wave is in the Cave)
        strike = bool(warriors) and not warriors_in_cave and (len(warriors) >= WAVE_SIZE or step >= LATEST_START)

        busy = []

        def assign_paid(villager, group, cost):
            nonlocal wheat
            if wheat >= cost:
                environment.assign_group(villager, group)
                wheat -= cost
                busy.append(villager)
                return True
            return False

        # 1. farmers eat when they have to
        for farmer in sorted(farmers, key=lambda c: -c.steps_since_meal):
            if farmer.steps_since_meal >= interval - 1:
                assign_paid(farmer, "eat", environment.meal_cost)

        # 2. warriors: eat right before the strike, then go to the Cave all together; otherwise wait and farm
        needs_meal = environment.meal_interval and any(w.steps_since_meal > 0 for w in warriors)
        if strike and needs_meal:
            for warrior in warriors:
                assign_paid(warrior, "eat", environment.meal_cost)
        elif strike:
            for warrior in warriors:
                environment.assign_group(warrior, "cave")
                busy.append(warrior)
        else:
            for warrior in warriors:
                if warrior.steps_since_meal >= interval - 1:
                    assign_paid(warrior, "eat", environment.meal_cost)
        free_warriors = [w for w in warriors if w not in busy]

        # 3. spawning (keep a reserve of wheat for the meals that are due in the next steps)
        free_farmers = [f for f in farmers if f not in busy]
        due_soon = [v for v in environment.components if v not in busy and v.steps_since_meal >= interval - 3]
        available = wheat - environment.meal_cost * len(due_soon)
        for spawn_group, spawn_cost in (("spawn warrior", WARRIOR_SPAWN_COST), ("spawn farmer", FARMER_SPAWN_COST)):
            if len(free_farmers) >= 2 and available >= spawn_cost:
                environment.assign_group(free_farmers[0], spawn_group)
                environment.assign_group(free_farmers[1], spawn_group)
                free_farmers = free_farmers[2:]
                available -= spawn_cost

        # 4. remaining villagers farm
        for villager in free_farmers + free_warriors:
            environment.assign_group(villager, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        # the whole wave returns together as soon as one of the warriors has to return
        wave_returns = any(turns_left(w, environment) <= 0 for w in warriors)
        for warrior in warriors:
            environment.assign_group(warrior, "village" if wave_returns else "attack")
        for villager in others:
            environment.assign_group(villager, "village")
