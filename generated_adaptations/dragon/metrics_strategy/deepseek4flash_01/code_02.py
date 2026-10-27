from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.last_attack_step = -10

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def assign(component, group_id):
            environment.assign_group(component, group_id)
            assigned.add(id(component))

        comps = sorted(
            components,
            key=lambda c: (-c.steps_since_meal, c.hp, 0 if c.role == "Warrior" else 1),
        )

        # 1. Urgent meals: anybody at 5+ steps without food must eat now.
        for c in comps:
            if id(c) not in assigned and c.steps_since_meal >= 5 and wheat > 0:
                assign(c, "eat")
                wheat -= 1

        # 2. Do not send a warrior to the cave if it would immediately need to return.
        for c in comps:
            if (
                id(c) not in assigned
                and c.role == "Warrior"
                and c.steps_since_meal >= 4
                and wheat > 0
            ):
                assign(c, "eat")
                wheat -= 1

        # 3. If food is comfortable, farmers eat earlier as well.
        for c in comps:
            if (
                id(c) not in assigned
                and c.role == "Farmer"
                and c.steps_since_meal >= 4
                and wheat >= 15
            ):
                assign(c, "eat")
                wheat -= 1

        # 4. Warriors go to the cave unless they just ate / are too hungry.
        for c in comps:
            if id(c) not in assigned and c.role == "Warrior":
                if c.hp > 0 and c.steps_since_meal <= 3:
                    assign(c, "cave")
                else:
                    assign(c, "farm")

        # 5. Farmers spawn a small early army, then farm.
        farmers = [
            c for c in comps
            if id(c) not in assigned and c.role == "Farmer"
        ]

        if step <= 24:
            need_warriors = max(0, 2 - self.spawned_warriors)
            while (
                need_warriors > 0
                and wheat >= 12
                and len(farmers) >= 2
                and "spawn warrior" in group_ids
            ):
                a = farmers.pop(0)
                b = farmers.pop(0)
                assign(a, "spawn warrior")
                assign(b, "spawn warrior")
                wheat -= 12
                self.spawned_warriors += 1
                need_warriors -= 1

            need_farmers = max(0, 2 - self.spawned_farmers)
            while (
                need_farmers > 0
                and wheat >= 10
                and len(farmers) >= 2
                and "spawn farmer" in group_ids
            ):
                a = farmers.pop(0)
                b = farmers.pop(0)
                assign(a, "spawn farmer")
                assign(b, "spawn farmer")
                wheat -= 10
                self.spawned_farmers += 1
                need_farmers -= 1

        # 6. Everyone left in the village farms.
        for c in comps:
            if id(c) not in assigned:
                assign(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(component, group_id):
            environment.assign_group(component, group_id)
            assigned.add(id(component))

        # Farmers should not attack; send them back to the village.
        for c in components:
            if c.role != "Warrior":
                assign(c, "village")

        warriors = [
            c for c in components
            if c.role == "Warrior" and id(c) not in assigned
        ]

        # Warriors that have been away too long return to eat.
        ready = [
            c for c in warriors
            if c.steps_since_meal < 4 and c.hp > 0
        ]
        need_return = [
            c for c in warriors
            if c.steps_since_meal >= 4
        ]

        # If every warrior is at the return threshold, keep one attacker for this
        # step if it has not reached the starvation counter. This helps prevent
        # the Dragon from regenerating for too many consecutive steps.
        if not ready and warriors:
            fallback = [
                c for c in warriors
                if c.steps_since_meal < 5 and c.hp > 0
            ]
            if fallback:
                attacker = min(
                    fallback,
                    key=lambda c: (c.steps_since_meal, -c.hp),
                )
                ready = [attacker]
                need_return = [
                    c for c in warriors
                    if c is not attacker
                ]

        for c in need_return:
            if id(c) not in assigned:
                assign(c, "village")

        for c in ready:
            if id(c) not in assigned:
                assign(c, "attack")
                self.last_attack_step = step

        # Safety fallback: every component must be assigned exactly once.
        for c in components:
            if id(c) not in assigned:
                assign(c, "cave")