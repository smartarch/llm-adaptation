The revised strategy keeps farmers in the Village, uses them to recruit continuously, and builds a small warrior force before starting the assault. New warriors provide staggered reinforcements, reducing gaps in attacks. Warriors return for food before starving; an exception allows a final attack when the available damage can kill the Dragon immediately.

This remains a heuristic: random Dragon attacks can still prevent a win, and feeding cannot be guaranteed if the initial state provides too little food or too few villagers.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        warriors = list(environment.warriors)
        farmers = list(environment.farmers)
        population = len(warriors) + len(farmers)
        wheat = max(0, environment.farm.wheat)

        assignments = ["farm"] * len(villagers)
        committed = set()

        # Feed villagers before they reach six consecutive missed meals.
        urgent = sorted(
            (i for i, v in enumerate(villagers) if v.steps_since_meal >= 5),
            key=lambda i: (-villagers[i].steps_since_meal, villagers[i].hp),
        )
        for i in urgent:
            committed.add(i)
            if wheat >= 1:
                assignments[i] = "eat"
                wheat -= 1

        cave_warriors = sum(v.location == "Cave" for v in warriors)
        assault = (
            cave_warriors > 0
            or environment.dragon.hp < 100
            or len(warriors) >= 4
            or step >= 6
        )

        # Feed warriors before deployment so they can spend more consecutive
        # turns attacking before they must return.
        for i, villager in enumerate(villagers):
            if i in committed or villager.role != "Warrior":
                continue
            threshold = 2 if assault else 4
            if villager.steps_since_meal >= threshold:
                committed.add(i)
                if wheat >= 1:
                    assignments[i] = "eat"
                    wheat -= 1

        # Recruit using available villagers. Before the assault, warriors can
        # help with spawning; during it, prefer farmers so warriors can fight.
        available = [i for i in range(len(villagers)) if i not in committed]
        if assault:
            available.sort(
                key=lambda i: (
                    villagers[i].role != "Farmer",
                    villagers[i].steps_since_meal,
                )
            )
        else:
            available.sort(
                key=lambda i: (
                    villagers[i].role != "Warrior",
                    villagers[i].steps_since_meal,
                )
            )

        planned_farmers = len(farmers)
        planned_warriors = len(warriors)
        planned_births = 0

        while len(available) >= 2 and step < 28:
            if planned_warriors == 0:
                target = "warrior"
            elif planned_farmers < 4 and step < 9:
                target = "farmer"
            else:
                target = "warrior"

            cost = 10 if target == "farmer" else 12
            food_reserve = population + planned_births
            if wheat < cost + food_reserve:
                break

            # Do not hold back attacking warriors just to recruit when there
            # are already warriors fighting.
            if assault and cave_warriors > 0:
                farmer_indices = [
                    i for i in available if villagers[i].role == "Farmer"
                ]
                if len(farmer_indices) < 2:
                    break
                first, second = farmer_indices[:2]
            else:
                first, second = available[:2]

            available.remove(first)
            available.remove(second)
            assignments[first] = assignments[second] = "spawn " + target
            committed.update((first, second))
            wheat -= cost
            planned_births += 1
            if target == "farmer":
                planned_farmers += 1
            else:
                planned_warriors += 1

        if assault:
            for i in available:
                villager = villagers[i]
                if villager.role == "Warrior" and villager.steps_since_meal < 2:
                    assignments[i] = "cave"

        for villager, group in zip(villagers, assignments):
            environment.assign_group(villager, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        villagers = list(components)

        # At age four, attacking once more is safe if it finishes the Dragon
        # this turn. Otherwise, return in time to eat in the Village.
        finishing_damage = sum(
            3 if v.role == "Warrior" else 1
            for v in villagers
            if v.steps_since_meal < 5
        )
        can_finish = finishing_damage >= environment.dragon.hp

        for villager in villagers:
            if villager.steps_since_meal >= 5:
                group = "village"
            elif villager.steps_since_meal >= 4 and not can_finish:
                group = "village"
            else:
                group = "attack"
            environment.assign_group(villager, group)
```