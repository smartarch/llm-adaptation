from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon

        # Meals due in the near future (within the next 3 steps), across
        # ALL villagers (Village + Cave). Villagers with steps_since_meal >= 3
        # must eat soon, and ones returning from the Cave need an extra step
        # of travel, so they are covered too.
        everyone = list(environment.farmers) + list(environment.warriors)
        reserve = sum(1 for c in everyone if c.steps_since_meal >= 3)

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
                break  # no wheat left; they must farm this step

        remaining = [c for c in components if c not in fed]

        # 2) Final push: if the Dragon is nearly dead, everyone healthy attacks.
        if dragon.hp <= 40:
            for c in remaining:
                environment.assign_group(c, "cave")
            return

        # 3) Warriors travel to the Cave (they are useless on the farm).
        for c in list(remaining):
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                remaining.remove(c)

        # 4) Spawn warriors when affordable while keeping the meal reserve.
        i = 0
        while i + 1 < len(remaining) and wheat - 12 >= reserve:
            environment.assign_group(remaining[i], "spawn warrior")
            environment.assign_group(remaining[i + 1], "spawn warrior")
            wheat -= 12
            i += 2
        remaining = remaining[i:]

        # 5) Spawn farmers only with a large surplus (economy growth).
        if wheat - 10 >= reserve + 5:
            i = 0
            while i + 1 < len(remaining) and wheat - 10 >= reserve + 5:
                environment.assign_group(remaining[i], "spawn farmer")
                environment.assign_group(remaining[i + 1], "spawn farmer")
                wheat -= 10
                i += 2
            remaining = remaining[i:]

        # 6) Everyone else farms.
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 3:
                # Head home now: arrives in the Village next step (ssm 4-5)
                # and can still eat before starving (ssm 6).
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")