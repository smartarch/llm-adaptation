## Analysis

`seed=3` likely loses from attrition: villagers get whittled down in the Cave until a Dragon meal/snack wipes the team. I'll keep the proven fast config (eat/retreat at `>=4`) but make two changes:

1. Retreat at `hp <= 2` (instead of 1) so badly hurt villagers survive — a dead attacker deals nothing later.
2. Make the all-in push **damage-aware**: only everyone attacks (ignoring low HP) if the collective damage of healthy attackers can already finish the Dragon this step — no pointless exposure, faster kills.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        assigned = set()

        def put(c, group):
            if id(c) not in assigned:
                groups[group].append(c)
                assigned.add(id(c))

        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)
        total = n_farmers + n_warriors
        reserve = total  # keep one meal per villager as reserve

        # 1) Feeding first: anyone at risk of starving eats now.
        for c in components:
            if c.steps_since_meal >= 4:
                if wheat >= 1:
                    put(c, "eat")
                    wheat -= 1
                else:
                    put(c, "farm")

        rest = [c for c in components if id(c) not in assigned]

        # 2) Aggressive spawning: warriors are the key to a fast kill.
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        if wheat >= 12 + reserve and len(rest) >= 2 and n_warriors < 10:
            pair = (warriors_here + farmers_here + rest)[:2]
            for c in pair:
                put(c, "spawn warrior")
            wheat -= 12
        elif total < 5 and wheat >= 10 + reserve and len(rest) >= 2:
            pair = (farmers_here + rest)[:2]
            for c in pair:
                put(c, "spawn farmer")
            wheat -= 10

        rest = [c for c in components if id(c) not in assigned]
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # 3) Warriors march to the Cave; farmers farm or reinforce the Cave.
        for c in warriors_here:
            put(c, "cave")
        farmers_here.sort(key=lambda c: -c.hp)
        n_farm_to_farm = 2 if total <= 5 else 1
        for i, c in enumerate(farmers_here):
            put(c, "farm" if i < n_farm_to_farm else "cave")

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}

        # Can the healthy attackers finish the Dragon this step?
        damage = sum(3 if c.role == "Warrior" else 1
                     for c in components
                     if c.steps_since_meal < 6 and c.hp > 2)
        all_in = damage >= environment.dragon.hp

        for c in components:
            # Eating rule is absolute: hungry villagers go home now.
            if c.steps_since_meal >= 4:
                groups["village"].append(c)
            # Badly hurt villagers retreat to recover - unless the
            # healthy force can finish the Dragon right now anyway.
            elif c.hp <= 2 and not all_in:
                groups["village"].append(c)
            else:
                groups["attack"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)
```