from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # --- Decide meals ------------------------------------------------
        # Mandatory meal at 5 steps; warriors that are >=3 are useless to
        # send to the Cave (they'd have to turn back), so feed them first.
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 3:
                to_eat.add(c)

        avail_farmers = [f for f in farmers if f not in to_eat]

        # Dynamic wheat reserve: protect only villagers who *must* eat soon
        imminent = sum(1 for c in components if c.steps_since_meal >= 4)
        reserve = imminent + 2
        spend = max(0, wheat - reserve)
        spawn = {}

        # --- 1) Build a small farmer economy early (target 4 farmers) ----
        if len(farmers) < 4 and len(avail_farmers) >= 2 and spend >= 10:
            n = min(len(avail_farmers) // 2, spend // 10,
                    max(1, (4 - len(farmers) + 1) // 2))
            for j in range(n):
                spawn[avail_farmers[2 * j]] = 'spawn farmer'
                spawn[avail_farmers[2 * j + 1]] = 'spawn farmer'
            avail_farmers = avail_farmers[2 * n:]
            spend -= 10 * n

        # --- 2) Spend everything left on warriors (multiple pairs!) ------
        nw = min(len(avail_farmers) // 2, spend // 12)
        for j in range(nw):
            spawn[avail_farmers[2 * j]] = 'spawn warrior'
            spawn[avail_farmers[2 * j + 1]] = 'spawn warrior'

        # --- 3) Assign every component exactly once ----------------------
        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn:
                environment.assign_group(c, spawn[c])
            elif c.role == 'Warrior' and c.steps_since_meal <= 2:
                environment.assign_group(c, 'cave')   # fresh enough to attack
            else:
                environment.assign_group(c, 'farm')   # farmers stay & farm

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == 'Warrior']

        # Farmers should never be here; send them home.
        go_home = set(c for c in components if c.role != 'Warrior')

        # Warriors at 6+ steps since meal starve -> deal no damage -> return.
        for w in warriors:
            if w.steps_since_meal >= 6:
                go_home.add(w)

        attackers = [w for w in warriors if w not in go_home]

        # Guarantee the dragon is never left unattacked for > 2 steps.
        if not attackers and warriors and (step - self.last_attack_step) >= 3:
            keep = min(warriors, key=lambda x: x.steps_since_meal)
            go_home.discard(keep)
            attackers = [keep]

        attacked = False
        for c in components:
            if c in go_home:
                environment.assign_group(c, 'village')
            else:
                environment.assign_group(c, 'attack')
                attacked = True

        if attacked:
            self.last_attack_step = step