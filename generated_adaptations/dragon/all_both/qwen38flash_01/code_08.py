from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Track assignments to ensure everyone gets exactly one
        assigned = set()

        # --- WARRIORS ---
        must_eat_warriors = []
        should_eat_warriors = []
        can_go_cave_warriors = []

        for w in warriors:
            if w.steps_since_meal >= 5:
                must_eat_warriors.append(w)
            elif w.steps_since_meal >= 3:
                should_eat_warriors.append(w)
            else:
                can_go_cave_warriors.append(w)

        # Forced eat (sms >= 5)
        for w in must_eat_warriors:
            if wheat > 0:
                environment.assign_group(w, "eat")
                wheat -= 1
            else:
                environment.assign_group(w, "farm")
            assigned.add(w)

        # Warriors that should eat before going to cave (sms 3-4)
        # Don't send them to cave - they'd arrive with sms>=4 and waste a trip
        for w in should_eat_warriors:
            if wheat > 0:
                environment.assign_group(w, "eat")
                wheat -= 1
            else:
                # No wheat, can't eat. Stay in village (they'll suffer but survive)
                environment.assign_group(w, "farm")
            assigned.add(w)

        # Warriors with sms <= 2 can go to cave
        # Stagger initial deployment: don't send all at once to create offset
        to_cave = []
        stay_farm = []

        if can_go_cave_warriors:
            if step <= 1 and len(can_go_cave_warriors) > 1:
                # Initial stagger: send only 1 warrior at step 0, rest eat/delay
                to_cave = [can_go_cave_warriors[0]]
                stay_farm = can_go_cave_warriors[1:]
            elif step <= 3 and len(can_go_cave_warriors) > 2:
                # Early: send at most half to maintain stagger
                mid = (len(can_go_cave_warriors) + 1) // 2
                to_cave = can_go_cave_warriors[:mid]
                stay_farm = can_go_cave_warriors[mid:]
            else:
                to_cave = can_go_cave_warriors[:]

        for w in to_cave:
            environment.assign_group(w, "cave")
            assigned.add(w)

        for w in stay_farm:
            if w.steps_since_meal >= 2 and wheat > 0:
                environment.assign_group(w, "eat")
                wheat -= 1
            else:
                environment.assign_group(w, "farm")
            assigned.add(w)

        # --- FARMERS ---
        must_eat_farmers = []
        work_farmers = []

        for f in farmers:
            if f.steps_since_meal >= 5:
                must_eat_farmers.append(f)
            elif f.steps_since_meal >= 4:
                must_eat_farmers.append(f)
            else:
                work_farmers.append(f)

        for f in must_eat_farmers:
            if wheat > 0:
                environment.assign_group(f, "eat")
                wheat -= 1
            else:
                environment.assign_group(f, "farm")
            assigned.add(f)

        # --- SPAWNING (aggressive) ---
        # Reserve wheat for meals: estimate ~2 meals needed per step from villagers
        # Be more aggressive about spawning warriors early
        remaining_farmers = work_farmers[:]

        # Spawn warriors: most important priority for killing dragon
        # Need 2 farmers + 12 wheat
        if step >= 1 and len(remaining_farmers) >= 2:
            # Count current warriors to decide spawn priority
            num_warriors = len(warriors)
            if num_warriors < 6:
                # Aggressive warrior spawning
                reserve_for_meals = (len(remaining_farmers) + len(warriors)) * 1
                if wheat >= 12 + reserve_for_meals:
                    pair = remaining_farmers[:2]
                    remaining_farmers = remaining_farmers[2:]
                    wheat -= 12
                    for f in pair:
                        environment.assign_group(f, "spawn warrior")
                        assigned.add(f)

        # Spawn farmers: needed for wheat production
        if step >= 4 and len(remaining_farmers) >= 2:
            reserve_for_meals = (len(remaining_farmers) + len(warriors)) * 1
            if wheat >= 10 + reserve_for_meals:
                pair = remaining_farmers[:2]
                remaining_farmers = remaining_farmers[2:]
                wheat -= 10
                for f in pair:
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(f)

        # Remaining farmers → farm
        for f in remaining_farmers:
            if f not in assigned:
                environment.assign_group(f, "farm")
                assigned.add(f)

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= 4:
                # Return to village to eat (arrive with sms=5, eat next step)
                environment.assign_group(c, "village")
            else:
                # Attack the dragon (allows attack at sms 1, 2, 3)
                environment.assign_group(c, "attack")