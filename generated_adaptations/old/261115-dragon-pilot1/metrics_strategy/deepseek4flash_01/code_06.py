from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.war_started = False
        self.target_warriors = 8
        self.wheat_buffer = 14

    # ---------------- Village ----------------
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # 1. Urgent meals (never let anyone reach the 6-step starvation mark).
        for c in sorted(components, key=lambda x: -x.steps_since_meal):
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 5 and wheat > 0:
                A(c, 'eat')
                wheat -= 1

        # Decide whether the war has begun (army big enough OR deadline near).
        if not self.war_started:
            if self.spawned_warriors >= self.target_warriors or step >= 12:
                self.war_started = True

        # 2. Warriors in the Village.
        for c in components:
            if id(c) in assigned or c.role != 'Warrior':
                continue
            if c.steps_since_meal >= 4 and wheat > 0:
                A(c, 'eat')
                wheat -= 1
            elif self.war_started:
                A(c, 'cave')      # head to the battlefield
            else:
                A(c, 'farm')      # help the economy while the army builds

        # 3. Farmers.
        farmers = [c for c in components
                   if id(c) not in assigned and c.role == 'Farmer']

        # Early: grow a tiny population so the economy can bootstrap.
        if len(components) < 5 and len(farmers) >= 2 and wheat >= 12 and step <= 8:
            A(farmers[0], 'spawn farmer')
            A(farmers[1], 'spawn farmer')
            self.spawned_farmers += 1
            farmers = farmers[2:]

        # Build the warrior army: keep 2 breeders while >= 5 farmers remain
        # (so at least 3 farmers still fund the 12-wheat cost plus meals).
        if len(farmers) >= 5 and wheat >= self.wheat_buffer and 'spawn warrior' in group_ids:
            A(farmers[0], 'spawn warrior')
            A(farmers[1], 'spawn warrior')
            self.spawned_warriors += 1
            farmers = farmers[2:]

        # Everyone else farms.
        for f in farmers:
            A(f, 'farm')

    # ---------------- Cave -------------------
    def assign_in_cave(self, components, environment, group_ids, step: int):
        assigned = set()

        def A(c, g):
            environment.assign_group(c, g)
            assigned.add(id(c))

        # Non-warriors have no business in the Cave.
        for c in components:
            if c.role != 'Warrior':
                A(c, 'village')

        # Warriors: attack while fed, otherwise go home to eat.
        for c in components:
            if id(c) in assigned:
                continue
            if c.steps_since_meal >= 4:
                A(c, 'village')   # return to eat, come back fed
            else:
                A(c, 'attack')