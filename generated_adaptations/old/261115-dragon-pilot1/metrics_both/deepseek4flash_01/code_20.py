from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10

    def _spawn(self, avail, group, cost, budget, spawn):
        """Assign as many disjoint pairs as budget allows; return (rest, spent)."""
        spent, i = 0, 0
        while i + 1 < len(avail) and budget - spent >= cost:
            spawn[avail[i]] = group
            spawn[avail[i + 1]] = group
            i += 2
            spent += cost
        return avail[i:], spent

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # Meals: mandatory at 5; warriors at >=3 cannot enter the Cave -> eat.
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 3:
                to_eat.add(c)

        avail = [f for f in farmers if f not in to_eat]

        # Dynamic reserve: protect imminent meals with a tight buffer.
        imminent = sum(1 for c in components if c.steps_since_meal >= 4)
        spend = max(0, wheat - (imminent + 1))
        spawn = {}

        TARGET_FARMERS = 6
        need_farmers = len(farmers) < TARGET_FARMERS

        # Wheat-aware ordering: press the warrior pipeline once we have surplus.
        if need_farmers and wheat < 24:
            # Tight economy -> secure farmers first, then warriors.
            if spend >= 10:
                avail, spent = self._spawn(avail, 'spawn farmer', 10, spend, spawn)
                spend -= spent
            if spend >= 12:
                self._spawn(avail, 'spawn warrior', 12, spend, spawn)
        else:
            # Surplus economy -> warriors first, then top up farmers.
            if spend >= 12:
                avail, spent = self._spawn(avail, 'spawn warrior', 12, spend, spawn)
                spend -= spent
            if need_farmers and spend >= 10:
                avail, spent = self._spawn(avail, 'spawn farmer', 10, spend, spawn)
                spend -= spent

        # Assign every component exactly once.
        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn:
                environment.assign_group(c, spawn[c])
            elif c.role == 'Warrior' and c.steps_since_meal <= 2:
                environment.assign_group(c, 'cave')   # fed enough -> attack
            else:
                environment.assign_group(c, 'farm')   # farmers stay & farm

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == 'Warrior']

        # Non-warriors shouldn't be here; starving warriors (6+) deal no damage.
        go_home = set(c for c in components if c.role != 'Warrior')
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