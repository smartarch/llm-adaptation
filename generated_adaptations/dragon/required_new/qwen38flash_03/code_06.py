from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.attack_started = False

    def assign_in_village(self, components, environment, group_ids, step):
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        num_warriors = len(all_warriors)
        num_farmers = len(all_farmers)

        wheat = environment.farm.wheat
        assigned = set()

        # Priority 1: Feed hungry villagers, but only if wheat is available
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= 4],
            key=lambda c: c.steps_since_meal,
            reverse=True
        )

        for c in hungry:
            if wheat >= 1:
                environment.assign_group(c, "eat")
                assigned.add(id(c))
                wheat -= 1
            else:
                # No wheat to eat; must still be assigned
                environment.assign_group(c, "farm")
                assigned.add(id(c))

        # Determine attack phase transition
        if not self.attack_started:
            if num_warriors >= 8 and wheat >= 10 and step >= 3:
                self.attack_started = True

        remaining = [c for c in components if id(c) not in assigned]

        if not self.attack_started:
            # --- BUILDUP PHASE ---
            spawnable = list(remaining)

            # Spawn warriors: 2 villagers in group → 1 new warrior, costs 12 wheat
            while len(spawnable) >= 2 and wheat >= 12 and num_warriors < 16:
                c1 = spawnable.pop(0)
                c2 = spawnable.pop(0)
                environment.assign_group(c1, "spawn warrior")
                environment.assign_group(c2, "spawn warrior")
                assigned.add(id(c1))
                assigned.add(id(c2))
                wheat -= 12
                num_warriors += 1

            # Spawn farmers if very few and affordable
            while len(spawnable) >= 2 and wheat >= 10 and num_farmers < 5:
                c1 = spawnable.pop(0)
                c2 = spawnable.pop(0)
                environment.assign_group(c1, "spawn farmer")
                environment.assign_group(c2, "spawn farmer")
                assigned.add(id(c1))
                assigned.add(id(c2))
                wheat -= 10
                num_farmers += 1

            # Everyone else farms
            for c in spawnable:
                if id(c) not in assigned:
                    environment.assign_group(c, "farm")
                    assigned.add(id(c))
        else:
            # --- ATTACK PHASE ---
            # Warriors with steps_since_meal <= 2 can survive a cave roundtrip
            # (travel=1, attack, travel back=1 → arrives at meal step + 2 or 3)
            for c in remaining:
                if id(c) in assigned:
                    continue
                if c.role == "Warrior" and c.steps_since_meal <= 2:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                assigned.add(id(c))

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            # If steps_since_meal >= 4, return to village to eat
            # (1 step to travel back, then eat at village)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")