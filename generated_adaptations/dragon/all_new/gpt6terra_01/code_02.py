import math

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        everyone = warriors + farmers

        dragon_hp = environment.dragon.hp
        cave_warriors = sum(w.location == "Cave" for w in warriors)

        # Start earlier if the dragon has already been damaged or time is short.
        target_force = max(3, math.ceil(dragon_hp / 15))
        attacking = (
            dragon_hp < 100
            or cave_warriors > 0
            or len(warriors) >= target_force
            or step >= 17
        )

        # In the final turns, send farmers too, retaining one food producer
        # until the very end when possible.
        village_farmers = sorted(
            (v for v in villagers if v.role == "Farmer"),
            key=lambda v: v.hp,
            reverse=True,
        )
        farmer_raiders = []
        if step >= 24:
            farmer_raiders = (
                village_farmers if step >= 27 else village_farmers[:-1]
            )
        raider_ids = {id(v) for v in farmer_raiders}

        def wants_to_depart(v):
            return (
                (v.role == "Warrior" and attacking)
                or id(v) in raider_ids
            )

        assignments = {}
        wheat = max(0, int(environment.farm.wheat))

        # Feed urgent villagers first. Departing villagers also eat if they
        # have gone two or more steps without a meal.
        meal_candidates = [
            v for v in villagers
            if v.steps_since_meal >= 5
            or (wants_to_depart(v) and v.steps_since_meal >= 2)
        ]
        meal_candidates.sort(
            key=lambda v: (-v.steps_since_meal, v.hp)
        )

        for villager in meal_candidates:
            if wheat > 0:
                assignments[id(villager)] = "eat"
                wheat -= 1

        # Only send villagers who have enough time to attack and return.
        for villager in villagers:
            if id(villager) in assignments:
                continue
            if wants_to_depart(villager) and villager.steps_since_meal <= 1:
                assignments[id(villager)] = "cave"

        available = [
            v for v in villagers if id(v) not in assignments
        ]

        # Preserve food for future meals, particularly for returning villagers.
        returning_soon = sum(
            v.location == "Cave" and v.steps_since_meal >= 3
            for v in everyone
        )
        food_reserve = max(2, math.ceil(len(everyone) / 3)) + returning_soon
        spawn_budget = max(0, wheat - food_reserve)

        # Keep a productive villager farming when the remaining village
        # population is large enough to farm and spawn simultaneously.
        worker = None
        if len(available) >= 3:
            worker = max(
                available,
                key=lambda v: (v.role == "Farmer", v.hp),
            )
            assignments[id(worker)] = "farm"

        spawn_candidates = [
            v for v in available if v is not worker
        ]
        spawn_candidates.sort(
            key=lambda v: (v.steps_since_meal, -v.hp)
        )

        # Each pair spawns one villager. Stop spawning when a new recruit
        # would have little time to reach the fight.
        while len(spawn_candidates) >= 2 and step < 26:
            if len(farmers) < 2 and step < 12:
                group = "spawn farmer"
                cost = 10
            else:
                group = "spawn warrior"
                cost = 12

            if spawn_budget < cost:
                break

            first = spawn_candidates.pop(0)
            second = spawn_candidates.pop(0)
            assignments[id(first)] = group
            assignments[id(second)] = group
            spawn_budget -= cost

            # Account for planned farmers when choosing the next spawn.
            if group == "spawn farmer":
                farmers.append(None)

        for villager in villagers:
            environment.assign_group(
                villager, assignments.get(id(villager), "farm")
            )

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for villager in components:
            # Returning consumes a step; at age 4 the villager reaches the
            # Village in time to eat on the next step.
            group = (
                "village" if villager.steps_since_meal >= 4 else "attack"
            )
            environment.assign_group(villager, group)