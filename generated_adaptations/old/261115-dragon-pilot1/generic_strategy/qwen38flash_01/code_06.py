import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        remaining_wheat = wheat

        # Categorize villagers by urgency and role
        critical_eat = []    # sme >= 5: will starve next step
        warriors_eat = []    # warriors sme 3-4: should eat soon before cave
        warriors_go = []     # warriors sme < 3: ready to go to cave now
        farmers_pool = []    # farmers sme < 5: available for tasks

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    critical_eat.append(c)
                elif c.steps_since_meal >= 3:
                    warriors_eat.append(c)
                else:
                    warriors_go.append(c)
            else:
                if c.steps_since_meal >= 5:
                    critical_eat.append(c)
                else:
                    farmers_pool.append(c)

        # Priority 1: Critical eaters must eat
        for c in critical_eat:
            if remaining_wheat >= 1:
                environment.assign_group(c, "eat")
                remaining_wheat -= 1
            else:
                # No wheat: assign to farm (they will starve but we have no choice)
                environment.assign_group(c, "farm")

        # Priority 2: Warriors at sme 3-4 eat if wheat available
        # They'll be at sme 4-5 next step when in village, ready to go to cave
        for c in warriors_eat:
            if remaining_wheat >= 1:
                environment.assign_group(c, "eat")
                remaining_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Priority 3: Ready warriors go to cave immediately
        for c in warriors_go:
            environment.assign_group(c, "cave")

        # Priority 4: Spawning - be aggressive early
        # Spawn warriors first (need 2 villagers, 12 wheat), target up to 4 total warriors spawned
        # Spawn farmers next (need 2 villagers, 10 wheat), target up to 2 extra farmers
        available = list(farmers_pool)

        # Spawn warriors aggressively in early game
        max_warrior_spawns = 4 if step <= 10 else 3
        while len(available) >= 2 and remaining_wheat >= 12 and self.spawned_warriors < max_warrior_spawns:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            remaining_wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers (need 2 villagers, 10 wheat), up to 2
        while len(available) >= 2 and remaining_wheat >= 10 and self.spawned_farmers < 2:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            remaining_wheat -= 10
            self.spawned_farmers += 1

        # Remaining farmers farm
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        if not warriors and not others:
            return

        # Count warriors that will still be able to attack next step (sme < 5)
        # We want to avoid leaving dragon unattacked for >1 step
        attackers_next_step = sum(1 for w in warriors if w.steps_since_meal < 4)

        for c in warriors:
            sme = c.steps_since_meal

            if sme >= 6:
                # Already starving - must leave immediately
                environment.assign_group(c, "village")
            elif sme >= 5:
                # sme=5: attack one more time, accept arriving at sme=6 (starve 1 step)
                # This is better than letting dragon regen for 1+ steps
                # OR go to village to prevent further starvation
                if attackers_next_step >= 1:
                    # Another warrior will attack, we can safely go eat
                    environment.assign_group(c, "village")
                else:
                    # Nobody else will attack - we must attack this step
                    # Accept arriving at sme=6 and losing 1 HP
                    environment.assign_group(c, "attack")
            elif sme >= 4:
                # sme=4: decide whether to attack or go
                # If another warrior will attack next step, go eat now (arrive sme=5, eat)
                # If nobody else will attack, attack one more (arrive sme=6, lose 1 HP)
                if attackers_next_step >= 2:
                    # Plenty of coverage, go eat
                    environment.assign_group(c, "village")
                else:
                    # Attack to cover
                    environment.assign_group(c, "attack")
            else:
                # sme < 4: always attack
                environment.assign_group(c, "attack")

        # Non-warriors in cave shouldn't be here; send to village
        for c in others:
            environment.assign_group(c, "village")