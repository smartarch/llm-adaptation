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

        # Track assignments to prevent double-assignment
        assigned = set(id(c) for c in [])  # empty set, will add as we go

        def do_assign(comp, group):
            if id(comp) not in assigned:
                assigned.add(id(comp))
                environment.assign_group(comp, group)

        # Endgame: everyone rushes cave
        if dragon_hp <= 30:
            for c in components:
                do_assign(c, "cave")
            return

        # Separate by hunger and role
        eaters = []
        fresh_warriors = []
        fresh_farmers = []

        for c in components:
            if c.steps_since_meal >= 4:
                eaters.append(c)
            elif c.role == "Warrior":
                fresh_warriors.append(c)
            else:
                fresh_farmers.append(c)

        # 1) Assign eaters
        for c in eaters:
            do_assign(c, "eat")

        # 2) All fresh warriors go to cave immediately
        for w in fresh_warriors:
            do_assign(w, "cave")

        # 3) Handle fresh_farmers: spawn warriors or farm
        # Determine how many spawn pairs we can do
        # Rule from tests: when total < 5, 2 free farmers should spawn (not farm) if wheat allows
        # Wheat cost: 12 per warrior. Reserve: 1 wheat per villager for meals
        # "enough to spawn AND keep a reserve of one meal for every villager"
        # means: wheat >= 12 + total (after spawn, reserve is total-2+1 = total-1? 
        # Or simply wheat >= 12 and wheat - 12 >= total)

        max_spawnable = len(fresh_farmers) // 2
        pairs = 0

        # Be aggressive about spawning
        need_warriors = (nw < 4) or (total < 5)

        if need_warriors and max_spawnable > 0:
            for p in range(1, max_spawnable + 1):
                cost = 12 * p
                remaining_wheat = wheat - cost
                # Keep at least 1 meal per remaining villager (after spawning)
                # After spawning, total becomes total + p, but farmers spawning are "consumed"
                # So new total = total + p (the spawning farmers become the new warrior + 2 stay)
                # Actually the 2 farmers are consumed, 1 warrior appears. Net: -1 farmer, +1 warrior
                # Total stays same. Reserve needed = total meals = total
                if remaining_wheat >= total:
                    pairs = p
                elif nw == 0 and remaining_wheat >= 0:
                    # Very urgent: no warriors at all, spawn even with tight budget
                    pairs = p
                else:
                    break

        # Assign first pairs*2 farmers to "spawn warrior"
        for i in range(min(pairs * 2, len(fresh_farmers))):
            do_assign(fresh_farmers[i], "spawn warrior")

        # Remaining fresh_farmers: decide farm vs cave
        remaining_farmers = fresh_farmers[min(pairs * 2, len(fresh_farmers)):]

        # Count how many attackers will be in cave after this assignment
        warriors_in_cave = sum(1 for w in environment.warriors if w.location == "Cave")
        # Plus warriors we're sending now
        attackers_available = warriors_in_cave + len(fresh_warriors)

        # If cave will have 0 attackers, send at least one farmer as backup
        cave_empty = (attackers_available == 0)

        for i, f in enumerate(remaining_farmers):
            if cave_empty and i == 0 and f.steps_since_meal <= 2:
                # Send one farmer to cave to prevent dragon regen
                do_assign(f, "cave")
            else:
                do_assign(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 30:
                # Endgame: attack regardless of hunger
                environment.assign_group(c, "attack")
            elif c.steps_since_meal >= 4:
                # Must leave to eat. At s_m=4: travel(5)→village, eat next step(s_m→0). Safe.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")