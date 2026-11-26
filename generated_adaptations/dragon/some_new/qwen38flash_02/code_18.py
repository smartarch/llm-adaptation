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

        # Endgame: everyone rushes cave (but hunger still takes priority)
        endgame = (dragon_hp <= 30)

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

        # 1) Hungry villagers must eat (ALWAYS, even in endgame)
        for c in eaters:
            do_assign(c, "eat")

        # 2) Fresh warriors go to cave
        for w in fresh_warriors:
            do_assign(w, "cave")

        # 3) Handle fresh_farmers: spawn warriors, farm, or attack
        # In endgame, send all farmers to cave
        if endgame:
            for f in fresh_farmers:
                do_assign(f, "cave")
            return

        # Determine spawning priority
        need_warriors = (nw < 6) or (total < 5)
        max_spawnable = len(fresh_farmers) // 2
        pairs = 0

        if need_warriors and max_spawnable > 0:
            for p in range(1, max_spawnable + 1):
                cost = 12 * p
                remaining_wheat = wheat - cost
                # Reserve: 1 wheat per villager for meals (current population)
                # After spawn: 2 farmers consumed, 1 warrior gained, net -1 person eating
                # Reserve = total (current count)
                if remaining_wheat >= total:
                    pairs = p
                elif nw == 0:
                    # Urgent: no warriors at all, spawn with minimal reserve
                    if remaining_wheat >= 0:
                        pairs = p
                    else:
                        break
                else:
                    break

        # Assign spawn pairs
        for i in range(pairs * 2):
            do_assign(fresh_farmers[i], "spawn warrior")

        # Remaining farmers: farm to produce wheat
        for i in range(pairs * 2, len(fresh_farmers)):
            do_assign(fresh_farmers[i], "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            # ALWAYS leave cave at s_m >= 4 to eat in time
            # Starving villagers deal 0 damage, so staying is useless
            if c.steps_since_meal >= 4:
                environment.assign_group(c, "village")
            elif dragon_hp <= 20:
                # Endgame: attack aggressively, but still respect hunger
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "attack")