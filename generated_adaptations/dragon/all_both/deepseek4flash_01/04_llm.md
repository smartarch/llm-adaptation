The main failure was the Cave rotation: warriors were all kept attacking until they were nearly starving, then returned together, leaving the Dragon unattacked for long stretches. The fix is to proactively rotate warriors out of the Cave one at a time so that meals are staggered and at least one warrior remains attacking. I also prioritize spawning the first two warriors before farmers, which helps when there are no initial warriors.

```py
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
        eaten_ids = set()

        # 1. Starvation-critical villagers eat first.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if c.steps_since_meal >= 5 and budget > 0:
                eaters.append(c)
                eaten_ids.add(id(c))
                budget -= 1

        # 2. Warriors that would arrive in the Cave too hungry should eat now.
        #    This keeps them from arriving at 3+ steps without a meal.
        for c in sorted(components, key=lambda x: x.steps_since_meal, reverse=True):
            if id(c) in eaten_ids or c.role != "Warrior":
                continue
            if c.steps_since_meal >= 2 and budget > 0:
                eaters.append(c)
                eaten_ids.add(id(c))
                budget -= 1

        for c in eaters:
            environment.assign_group(c, "eat")

        remaining = [c for c in components if id(c) not in eaten_ids]
        warriors = [c for c in remaining if c.role == "Warrior"]
        farmers = [c for c in remaining if c.role == "Farmer"]

        # 3. Warriors fresh enough to fight go to the Cave. Warriors with
        #    >= 2 steps since eating should not be sent, as they would likely
        #    have to return before attacking.
        for w in warriors:
            if w.steps_since_meal < 2:
                environment.assign_group(w, "cave")
            else:
                environment.assign_group(w, "farm")

        # 4. Spawn plan:
        #    - first two new warriors, so early attacks are possible
        #    - then two new farmers
        #    - then extra warriors if wheat is abundant
        spawn_group = None
        spawners = []
        candidates = sorted(farmers, key=lambda x: x.steps_since_meal)

        if len(candidates) >= 2:
            if self.spawned_warriors < 2 and budget >= 12:
                spawn_group = "spawn warrior"
                spawners = candidates[:2]
                budget -= 12
                self.spawned_warriors += 1
            elif self.spawned_farmers < 2 and budget >= 10:
                spawn_group = "spawn farmer"
                spawners = candidates[:2]
                budget -= 10
                self.spawned_farmers += 1
            elif (
                self.spawned_warriors < 4
                and budget >= 24
                and len(candidates) >= 3
            ):
                spawn_group = "spawn warrior"
                spawners = candidates[:2]
                budget -= 12
                self.spawned_warriors += 1

        spawner_ids = {id(c) for c in spawners}
        if spawn_group is not None:
            for c in spawners:
                environment.assign_group(c, spawn_group)

        # 5. All remaining farmers stay in the Village and farm.
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
                environment.assign_group(c, "village")

        if not warriors:
            return

        to_return = []

        if len(warriors) > 1:
            urgent = sorted(
                [w for w in warriors if w.steps_since_meal >= 5],
                key=lambda w: w.steps_since_meal,
                reverse=True,
            )

            if urgent:
                non_urgent = [w for w in warriors if w.steps_since_meal < 5]
                if non_urgent:
                    # Return all urgent warriors; at least one non-urgent
                    # warrior remains in the Cave to attack.
                    to_return.extend(urgent)
                else:
                    # Everyone is urgent. Keep the least-urgent warrior in
                    # the Cave for coverage and return the rest.
                    to_return.extend(urgent[:-1])
            else:
                # Proactive rotation: return the hungriest warrior while at
                # least one other warrior remains fresh enough to attack.
                # This staggers meals and prevents all warriors from being
                # away from the Dragon at the same time.
                max_w = max(warriors, key=lambda w: w.steps_since_meal)
                if max_w.steps_since_meal >= 1:
                    to_return.append(max_w)
        else:
            # With a single warrior, attack until it must return to eat.
            w = warriors[0]
            if w.steps_since_meal >= 4:
                to_return.append(w)

        returning_ids = {id(w) for w in to_return}
        attackers = [w for w in warriors if id(w) not in returning_ids]

        for w in to_return:
            environment.assign_group(w, "village")

        for w in attackers:
            environment.assign_group(w, "attack")

        if attackers:
            if self.first_attack_step is None:
                self.first_attack_step = step
            self.last_attack_step = step
```