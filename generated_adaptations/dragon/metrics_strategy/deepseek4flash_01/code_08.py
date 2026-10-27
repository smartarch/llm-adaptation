from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.release = False          # has the alpha-strike begun?
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    # ------------------------- Village -------------------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Decide whether to launch the assault.
        warriors_here = sum(
            1 for c in components
            if c.role == 'Warrior' and id(c) not in assigned
        )
        if (step >= 7 and warriors_here >= 3) or step >= 11:
            self.release = True

        # 1) Eat urgent villagers so nobody reaches the starvation step.
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                A(c, 'eat')
                wheat -= 1

        # 2) Warriors.
        for c in components:
            if id(c) in assigned or c.role != 'Warrior':
                continue
            if c.steps_since_meal >= 4 and wheat > 0:
                A(c, 'eat')          # must be fed to matter in the Cave
                wheat -= 1
            elif self.release:
                A(c, 'cave')         # head to the battlefield
            else:
                A(c, 'farm')         # hold & help economy; Dragon not woken

        # 3) Farmers: bootstrap economy, then breed warriors.
        farmers = [c for c in components
                   if id(c) not in assigned and c.role == 'Farmer']
        n = len(farmers)
        total_farmers = n + self.spawned_farmers

        if not self.release:
            if total_farmers < 5 and n >= 2 and wheat >= 12:
                A(farmers[0], 'spawn farmer')
                A(farmers[1], 'spawn farmer')
                self.spawned_farmers += 1
                farmers = farmers[2:]; n -= 2; wheat -= 10
            elif n >= 3 and wheat >= 14:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12
            elif n >= 2 and wheat >= 12:
                A(farmers[0], 'spawn farmer')
                A(farmers[1], 'spawn farmer')
                self.spawned_farmers += 1
                farmers = farmers[2:]; n -= 2; wheat -= 10
        else:
            # War phase: keep replacement warriors coming.
            if n >= 4 and wheat >= 14:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12
            if n >= 7 and wheat >= 26:
                A(farmers[0], 'spawn warrior')
                A(farmers[1], 'spawn warrior')
                self.spawned_warriors += 1
                farmers = farmers[2:]; n -= 2; wheat -= 12

        # 4) Everyone remaining farms.
        for f in farmers:
            A(f, 'farm')

    # --------------------------- Cave --------------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors never fight; send them home.
        for c in components:
            if c.role != 'Warrior':
                A(c, 'village')

        # Warriors: attack while fed; return home to eat well before starving.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                A(c, 'village')     # go eat, then come straight back
            else:
                A(c, 'attack')