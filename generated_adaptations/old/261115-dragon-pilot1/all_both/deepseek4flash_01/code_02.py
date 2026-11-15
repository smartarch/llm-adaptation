from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.first_attack_step = None
        self.last_attack_step = None
        self.spawned_farmers = 0
        self.spawned_warriors = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        components = list(components)
        wheat = int(environment.farm.wheat)
        budget = wheat

        eaters = []
        eaten = set()

        # 1. Anyone at the starvation threshold must eat now.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and budget > 0:
                eaters.append(c)
                eaten.add(id(c))
                budget -= 1

        # 2. A warrior with steps_since_meal >= 2 would arrive in the Cave
        # at >= 3 and might have to return before attacking. Let it eat first.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if id(c) in eaten or c.role != "Warrior":
                continue
            if c.steps_since_meal >= 2 and budget > 0:
                eaters.append(c)
                eaten.add(id(c))
                budget -= 1

        for c in eaters:
            environment.assign_group(c, "eat")

        remaining = [c for c in components if id(c) not in eaten]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # Warriors go to the Cave only if they are fresh enough to attack.
        for w in warriors:
            if w.steps_since_meal < 2:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # Spawning: alternate roughly between warriors and farmers, with
        # warriors first so the Dragon can be attacked early.
        spawn_group = None
        spawners = []
        need_warrior = self.spawned_warriors < 2
        need_farmer = self.spawned_farmers < 2
        candidates = sorted(farmers, key=lambda x: x.steps_since_meal)

        if len(candidates) >= 2:
            if (
                need_warrior
                and budget >= 12
                and (self.spawned_warriors <= self.spawned_farmers or not need_farmer)
            ):
                spawn_group = "spawn warrior"
                spawners = candidates[:2]
                budget -= 12
                self.spawned_warriors += 1
            elif need_farmer and budget >= 10:
                spawn_group = "spawn farmer"
                spawners = candidates[:2]
                budget -= 10
                self.spawned_farmers += 1
            elif need_warrior and budget >= 12:
                spawn_group = "spawn warrior"
                spawners = candidates[:2]
                budget -= 12
                self.spawned_warriors += 1

        spawner_ids = {id(c) for c in spawners}
        for c in spawners:
            environment.assign_group(c, spawn_group)

        # All remaining farmers stay in the Village and farm.
        for c in farmers:
            if id(c) not in spawner_ids:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        components = list(components)
        warriors = []

        for c in components:
            if c.role == "Warrior":
                warriors.append(c)
            else:
                # Farmers should stay in the Village.
                environment.assign_group(c, "village")

        if not warriors:
            return

        returners = [w for w in warriors if w.steps_since_meal >= 3]
        attackers = [w for w in warriors if w.steps_since_meal < 3]

        # If every warrior needs to return, keep one attacker only if it is
        # still safe to attack once more. This staggers meals and prevents
        # more than two consecutive unattacked steps.
        if not attackers and returners:
            returners_sorted = sorted(returners, key=lambda w: w.steps_since_meal)
            if returners_sorted[0].steps_since_meal < 4:
                attackers = [returners_sorted[0]]
                returners = returners_sorted[1:]
            else:
                attackers = []
                returners = returners_sorted

        for w in returners:
            environment.assign_group(w, "village")

        for w in attackers:
            environment.assign_group(w, "attack")

        if attackers:
            if self.first_attack_step is None:
                self.first_attack_step = step
            self.last_attack_step = step