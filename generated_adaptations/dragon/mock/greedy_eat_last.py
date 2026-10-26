"""Greedy strategy with meals, spawning first: like greedy_with_meals, but the spawning is decided before the meals,
and the villagers are sent to eat without checking whether there is enough wheat left (a likely mistake).

All Warriors go to the Cave and attack the Dragon; a warrior returns to the Village when it would otherwise starve,
eats, and goes back to the Cave. All Farmers stay in the Village and farm or spawn new villagers; they eat when they
have to.
"""
import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        interval = environment.meal_interval or math.inf
        hungry = [c for c in components if c.steps_since_meal >= interval - 1]
        farmers = [c for c in components if c.role == "Farmer" and c not in hungry]
        warriors = [c for c in components if c.role == "Warrior" and c not in hungry]
        wheat = environment.farm.wheat

        if wheat >= 12 and len(farmers) >= 2:  # warrior spawn cost
            # spawn warrior
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            farmers = farmers[2:]  # remove assigned farmers
            wheat -= 12

        if wheat >= 10 and len(farmers) >= 2:  # farmer spawn cost
            # spawn farmer
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            farmers = farmers[2:]  # remove assigned farmers
            wheat -= 10

        # Hungry villagers eat
        for c in hungry:
            environment.assign_group(c, "eat")

        # All other Warriors should go to the Cave
        for c in warriors:
            environment.assign_group(c, "cave")

        # Remaining Farmers should farm
        for c in farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        interval = environment.meal_interval or math.inf
        # Warriors attack the Dragon until they have to go eating
        for c in components:
            if c.role != "Warrior" or c.steps_since_meal >= interval - 2:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
