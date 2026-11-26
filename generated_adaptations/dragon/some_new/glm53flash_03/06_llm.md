## Analysis

`seed=3` likely loses because the attack force gets wiped out by Dragon counter-attacks (all villagers die). I'll make the strategy more conservative and resilient:

1. **Retreat earlier:** villagers with `steps_since_meal >= 3` or `hp <= 2` return home from the Cave (instead of 4/1), reducing deaths and starvation risk.
2. **Eat earlier:** feed at `steps_since_meal >= 3` for a bigger safety margin.
3. **Keep a reserve:** never send *everyone* to the Cave — keep at least one farmer farming in the Village at all times, so a single unlucky Dragon meal doesn't end the game.
4. Cap the spawn-warrior threshold with population checks so we never commit the whole village to the Cave.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}
        wheat = environment.farm.wheat
        n_farmers = len(environment.farmers)
        n_warriors = len(environment.warriors)
        total = n_farmers + n_warriors
        reserve = total  # keep one meal per villager as reserve

        assigned = set()

        # 1) Feeding first: anyone at risk of starving eats now.
        to_feed = [c for c in components if c.steps_since_meal >= 3]
        for c in to_feed:
            if wheat >= 1:
                groups["eat"].append(c)
                wheat -= 1
            else:
                groups["farm"].append(c)
            assigned.add(id(c))

        rest = [c for c in components if id(c) not in assigned]

        # 2) Aggressive spawning: warriors are the key to a fast kill.
        def take(pair, group, cost):
            nonlocal wheat
            groups[group].extend(pair)
            for c in pair:
                assigned.add(id(c))
            wheat -= cost

        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # Spawn warriors whenever affordable (reserve one meal per villager).
        if wheat >= 12 + reserve and len(rest) >= 2 and n_warriors < 10:
            pair = (warriors_here + farmers_here + rest)[:2]
            take(pair, "spawn warrior", 12)
        # Grow the population / food economy with farmers early on.
        elif total < 5 and wheat >= 10 + reserve and len(rest) >= 2:
            pair = (farmers_here + rest)[:2]
            take(pair, "spawn farmer", 10)

        rest = [c for c in components if id(c) not in assigned]
        farmers_here = [c for c in rest if c.role == "Farmer"]
        warriors_here = [c for c in rest if c.role == "Warrior"]

        # 3) Warriors march to the Cave; farmers farm or reinforce the Cave.
        for c in warriors_here:
            groups["cave"].append(c)
        farmers_here.sort(key=lambda c: -c.hp)
        n_farm_to_farm = 2 if total <= 5 else 1
        for i, c in enumerate(farmers_here):
            if i < n_farm_to_farm:
                groups["farm"].append(c)
            else:
                groups["cave"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        groups = {g: [] for g in group_ids}

        for c in components:
            # Starving villagers are too weak to damage the Dragon;
            # send them (and those about to starve or badly hurt) home.
            if c.steps_since_meal >= 3 or c.hp <= 2:
                groups["village"].append(c)
            else:
                groups["attack"].append(c)

        for group, members in groups.items():
            for c in members:
                environment.assign_group(c, group)
```