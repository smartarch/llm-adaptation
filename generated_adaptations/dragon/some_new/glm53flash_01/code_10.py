from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon

        everyone = list(environment.farmers) + list(environment.warriors)
        n_all = len(everyone)
        # Reserve: one meal per villager plus a small buffer.
        reserve = n_all + 2

        # 1) Eat first: everyone in the Village who must eat now.
        hungry = sorted(
            (c for c in components if c.steps_since_meal >= 4),
            key=lambda c: -c.steps_since_meal,
        )
        fed = []
        for c in hungry:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                fed.append(c)
            else:
                break

        remaining = [c for c in components if c not in fed]
        farmers_remaining = [c for c in remaining if c.role == "Farmer"]

        # 2) Final push: Dragon nearly dead -> send everyone healthy to attack.
        if dragon.hp <= 30:
            for c in remaining:
                if c.steps_since_meal < 3:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
            return

        # 3) Warriors travel to the Cave.
        for c in list(remaining):
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                remaining.remove(c)

        # 4) Spawn FARMERS when the population is small and wheat allows
        #    (population growth needed to win in 30 steps).
        if n_all < 5:
            while (
                len(remaining) >= 2
                and wheat - 10 >= reserve
            ):
                environment.assign_group(remaining[0], "spawn farmer")
                environment.assign_group(remaining[1], "spawn farmer")
                wheat -= 10
                remaining = remaining[2:]
        # 5) Spawn WARRIORS aggressively whenever affordable.
        while len(remaining) >= 2 and wheat - 12 >= reserve:
            environment.assign_group(remaining[0], "spawn warrior")
            environment.assign_group(remaining[1], "spawn warrior")
            wheat -= 12
            remaining = remaining[2:]

        # 6) Everyone else farms.
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 3:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")