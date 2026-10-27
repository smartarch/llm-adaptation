import generated_adaptations.base_classes.dragon
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        rem_wheat = wheat

        eat_critical = []    # sme >= 5: must eat now
        warriors_ready = []  # warriors sme < 5: can go to cave
        farmers_avail = []   # farmers sme < 5: available for tasks

        for c in components:
            if c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    eat_critical.append(c)
                else:
                    warriors_ready.append(c)
            else:
                if c.steps_since_meal >= 5:
                    eat_critical.append(c)
                else:
                    farmers_avail.append(c)

        # Critical eaters must eat (or starve with no wheat)
        for c in eat_critical:
            if rem_wheat >= 1:
                environment.assign_group(c, "eat")
                rem_wheat -= 1
            else:
                environment.assign_group(c, "farm")

        # Aggressive spawning: use available farmers to spawn warriors first
        available = list(farmers_avail)

        # Spawn warriors: need 2 villagers + 12 wheat each, target up to 4 extra
        max_w_spawns = 4 if step <= 12 else 3
        while len(available) >= 2 and rem_wheat >= 12 and self.spawned_warriors < max_w_spawns:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn warrior")
            environment.assign_group(c2, "spawn warrior")
            rem_wheat -= 12
            self.spawned_warriors += 1

        # Spawn farmers: need 2 villagers + 10 wheat each, target up to 2 extra
        while len(available) >= 2 and rem_wheat >= 10 and self.spawned_farmers < 2:
            c1 = available.pop(0)
            c2 = available.pop(0)
            environment.assign_group(c1, "spawn farmer")
            environment.assign_group(c2, "spawn farmer")
            rem_wheat -= 10
            self.spawned_farmers += 1

        # Warriors ready to go: send to cave immediately
        for c in warriors_ready:
            environment.assign_group(c, "cave")

        # Remaining farmers farm
        for c in available:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        warriors = [c for c in components if c.role == "Warrior"]
        others = [c for c in components if c.role != "Warrior"]

        # Count how many other warriors will still attack next step (sme < 5 means they'll be sme+1 <= 5, still can attack)
        # A warrior with sme < 4 will definitely attack next step if we let them
        # A warrior with sme == 4 will attack next step only if we don't send them back
        others_attack_next = sum(1 for w in warriors if w.steps_since_meal <= 3)

        for c in warriors:
            sme = c.steps_since_meal
            if sme >= 6:
                # Already starving, must return immediately
                environment.assign_group(c, "village")
            elif sme == 5:
                # Last attack opportunity; after this step sme=6 on return = 1 HP loss
                # Only return if another warrior definitely attacks next step
                if others_attack_next >= 1:
                    environment.assign_group(c, "village")
                else:
                    # Attack one more step to prevent dragon regen, accept HP loss later
                    # Actually at sme=5 we still attack safely this step
                    environment.assign_group(c, "attack")
            elif sme == 4:
                # Can attack one more (sme=5 safe), then must return
                # Only send back if plenty of coverage
                if others_attack_next >= 2:
                    environment.assign_group(c, "village")
                else:
                    environment.assign_group(c, "attack")
            else:
                # sme 0-3: always attack
                environment.assign_group(c, "attack")

        for c in others:
            environment.assign_group(c, "village")