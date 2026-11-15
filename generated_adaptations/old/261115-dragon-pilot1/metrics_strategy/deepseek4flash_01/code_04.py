from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.target_warriors = 8
        self.target_farmers = 4
        self.release_step = 9          # ensure first attack well within 15
        self.release_threshold = 7     # or release once this army size reached

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def assign(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        comps = sorted(components, key=lambda c: -c.steps_since_meal)

        # 1. Mandatory meals: anyone at 5+ steps without food must eat now.
        for c in comps:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                assign(c, 'eat')
                wheat -= 1

        # 2. Warriors: eat when stale, otherwise hold at home (build phase)
        #    or go to the Cave once the army is ready.
        army_ready = (
            self.spawned_warriors >= self.release_threshold
            or step >= self.release_step
        )
        for c in comps:
            if id(c) in assigned:
                continue
            if c.role == 'Warrior':
                if c.steps_since_meal >= 4 and wheat > 0:
                    assign(c, 'eat')
                    wheat -= 1
                elif not army_ready:
                    # Hold at home and contribute wheat until the strike.
                    assign(c, 'farm')
                else:
                    assign(c, 'cave')

        # 3. Farmers: spawn warriors aggressively, keep a farming base.
        farmers = [
            c for c in comps
            if id(c) not in assigned and c.role == 'Farmer'
        ]

        # Spawn warriors to build the alpha-strike army.
        while (
            self.spawned_warriors < self.target_warriors
            and wheat >= 12
            and len(farmers) >= 3
            and step <= 24
        ):
            a = farmers.pop(0)
            b = farmers.pop(0)
            assign(a, 'spawn warrior')
            assign(b, 'spawn warrior')
            wheat -= 12
            self.spawned_warriors += 1

        # Spawn a few extra farmers to sustain the economy / replace losses.
        while (
            self.spawned_farmers < self.target_farmers
            and wheat >= 10
            and len(farmers) >= 3
        ):
            a = farmers.pop(0)
            b = farmers.pop(0)
            assign(a, 'spawn farmer')
            assign(b, 'spawn farmer')
            wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers work the farm.
        for c in farmers:
            assign(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def assign(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors do not belong in the Cave.
        for c in components:
            if c.role != 'Warrior':
                assign(c, 'village')

        # Warriors attack in parallel; retreat only to eat.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                assign(c, 'village')
            else:
                assign(c, 'attack')