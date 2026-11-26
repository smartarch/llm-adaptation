import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        nw = len(environment.warriors)
        nf = len(environment.farmers)
        total = nw + nf

        assigned = set()

        def do_assign(comp, group):
            if id(comp) not in assigned:
                assigned.add(id(comp))
                environment.assign_group(comp, group)

        # Count attackers currently in cave who can still attack (s_m < 4)
        active_in_cave = 0
        for w in environment.warriors:
            if w.location == "Cave" and w.steps_since_meal < 4:
                active_in_cave += 1
        for f in environment.farmers:
            if f.location == "Cave" and f.steps_since_meal < 4:
                active_in_cave += 1

        # Separate villagers by hunger and role
        eaters = []
        fresh_warriors = []
        fresh_farmers = []

        for c in components:
            if c.steps_since_meal >= 4:
                eaters.append(c)
            elif c.role == "Warrior":
                fresh_warriors.append(c)
            else:
                fresh_farmers.append(fresh_farmers and None or None) if False else fresh_farmers.append(c)

        # Fix the bug: properly append farmers
        fresh_farmers = [c for c in components if c.steps_since_meal < 4 and c.role == "Farmer"]
        fresh_warriors = [c for c in components if c.steps_since_meal < 4 and c.role == "Warrior"]
        eaters = [c for c in components if c.steps_since_meal >= 4]

        # 1) Hungry villagers eat
        for c in eaters:
            do_assign(c, "eat")

        # 2) All fresh warriors go to cave
        for w in fresh_warriors:
            do_assign(w, "cave")

        # 3) Farmer decisions
        # Need warriors: target ~6, urgent if <4
        need_warriors = (nw < 6)
        max_spawnable = len(fresh_farmers) // 2
        pairs = 0

        if need_warriors and max_spawnable > 0:
            for p in range(1, max_spawnable + 1):
                cost = 12 * p
                remaining_wheat = wheat - cost
                if remaining_wheat >= total:
                    pairs = p
                elif nw < 2:
                    if remaining_wheat >= 0:
                        pairs = p
                    else:
                        break
                else:
                    break

        for i in range(pairs * 2):
            do_assign(fresh_farmers[i], "spawn warrior")

        remaining_farmers = fresh_farmers[pairs * 2:]

        # Keep at least 1-2 farmers farming for food production
        min_farm = 1 if nw >= 3 else 2

        # Decide: farm vs backup cave attack
        # Target total cave attackers: ~4 active. If we have fewer, send farmers.
        target_active_in_cave = max(2, 4 - active_in_cave)

        # Farmers going to cave: at most a few, keep some farming
        max_cave_farmers = 3 if nw >= 3 else 2

        to_cave = 0
        to_farm = 0
        for f in remaining_farmers:
            if to_farm < min_farm:
                do_assign(f, "farm")
                to_farm += 1
            elif to_cave < target_active_in_cave and to_cave < max_cave_farmers:
                # Send to cave as backup DPS
                do_assign(f, "cave")
                to_cave += 1
            else:
                do_assign(f, "farm")
                to_farm += 1

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # Always leave at s_m >= 4 to safely eat (arrive village at s_m=5, eat, safe)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")