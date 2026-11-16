from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        people = list(components)

        def hunger(person):
            return max(0, getattr(person, "steps_since_meal", 0))

        def hp(person):
            return getattr(person, "hp", 0)

        farmers = [p for p in people if getattr(p, "role", "") == "Farmer"]
        assigned = set()

        def assign(person, group):
            environment.assign_group(person, group)
            assigned.add(id(person))

        # Meals come first. Eat at four steps since the last meal to leave
        # room for travel and avoid reaching the starvation threshold.
        urgent = sorted(
            (p for p in people if hunger(p) >= 4),
            key=lambda p: (-hunger(p), hp(p)),
        )
        for person in urgent[:wheat]:
            assign(person, "eat")
        wheat -= min(wheat, len(urgent))

        # Spend only wheat above a small meal reserve. Reserving more when
        # villagers are already getting hungry helps avoid an economic spiral.
        remaining = [p for p in people if id(p) not in assigned]
        meal_reserve = max(
            2,
            sum(1 for p in people if hunger(p) >= 3),
            len(people) // 2,
        )
        spendable = max(0, wheat - meal_reserve)

        available_farmers = [
            p for p in farmers if id(p) not in assigned and hunger(p) < 4
        ]
        farmer_count = len(farmers)

        # If the workforce is very small, grow the farming base once. With
        # three or more farmers, keep at least one farming and use pairs to
        # spawn the higher-damage Warriors.
        if farmer_count <= 2 and len(available_farmers) >= 2 and spendable >= 10:
            for person in available_farmers[:2]:
                assign(person, "spawn farmer")
            spendable -= 10
        elif farmer_count >= 3 and len(available_farmers) >= 3:
            max_pairs = (len(available_farmers) - 1) // 2
            pairs = min(max_pairs, spendable // 12)
            for person in available_farmers[: 2 * pairs]:
                assign(person, "spawn warrior")
            spendable -= 12 * pairs

        # All remaining Warriors head to the Cave. Farmers stay to produce
        # wheat. If wheat was unavailable for a meal, a waiting Warrior farms
        # until food is available rather than risking starvation.
        for person in people:
            if id(person) in assigned:
                continue
            if getattr(person, "role", "") == "Warrior":
                if hunger(person) >= 4:
                    assign(person, "farm")
                else:
                    assign(person, "cave")
            else:
                assign(person, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        people = list(components)

        def hunger(person):
            return max(0, getattr(person, "steps_since_meal", 0))

        def hp(person):
            return getattr(person, "hp", 0)

        # At three steps without food, send a small cohort back to begin
        # staggering meals. Anyone still in the Cave at four steps returns,
        # so the travel step does not take them past the safe meal window.
        early = sorted(
            (p for p in people if hunger(p) == 3),
            key=lambda p: (hp(p), -hunger(p)),
        )
        early_count = (len(early) + 2) // 3
        returning = {id(p) for p in early[:early_count]}

        for person in people:
            if hp(person) <= 1 or hunger(person) >= 4:
                returning.add(id(person))

        for person in people:
            if id(person) in returning:
                environment.assign_group(person, "village")
            else:
                environment.assign_group(person, "attack")