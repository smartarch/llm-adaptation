The failures point to combat capacity and survival: a fixed, relatively small Warrior force can lose too many villagers to the Dragon’s random attacks. This revision builds a larger Warrior force when wheat and available villagers allow, while keeping food production going. It also avoids sending wounded Warriors home too early, and lets Farmers join the attack when the Dragon is close to death.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    @staticmethod
    def _get(obj, name, default=0):
        return getattr(obj, name, default)

    def assign_in_village(self, components, environment, group_ids, step: int):
        villagers = list(components)
        wheat = max(0, self._get(environment.farm, "wheat", 0))
        dragon_hp = max(0, self._get(environment.dragon, "hp", 0))

        all_warriors = list(getattr(environment, "warriors", []))
        all_farmers = list(getattr(environment, "farmers", []))
        warrior_count = len(all_warriors)
        population = warrior_count + len(all_farmers)

        remaining = list(villagers)
        assigned_ids = set()

        def put(v, group):
            self._assign(environment, v, group)
            assigned_ids.add(id(v))
            remaining.remove(v)

        # Eat while there is enough wheat, prioritizing those closest to
        # starvation. The attributes are snapshots, so do not reconsider
        # villagers after assigning them.
        hungry = sorted(
            (v for v in remaining
             if self._get(v, "steps_since_meal", 0) >= 4),
            key=lambda v: (
                self._get(v, "steps_since_meal", 0),
                -self._get(v, "hp", 0),
            ),
            reverse=True,
        )
        for v in hungry:
            if wheat <= 0:
                break
            put(v, "eat")
            wheat -= 1

        local_farmers = [
            v for v in remaining
            if self._get(v, "role", "") == "Farmer"
        ]

        spawn_group = None
        if dragon_hp > 0 and warrior_count == 0:
            # Establish a Warrior force as soon as the food reserve permits.
            spawn_group = "spawn warrior"
        elif dragon_hp > 0 and population < 5 and warrior_count > 0:
            # Build the food-producing population before expanding the army.
            spawn_group = "spawn farmer"
        elif dragon_hp > 0 and warrior_count < 7:
            spawn_group = "spawn warrior"

        # Keep a Farmer back to produce food whenever possible. Use the
        # remaining villagers in pairs to spawn as many as the current food
        # reserve supports.
        spawn_candidates = list(remaining)
        if len(local_farmers) > 0:
            reserve_farmer = local_farmers[0]
            spawn_candidates.remove(reserve_farmer)

        if spawn_group and len(spawn_candidates) >= 2:
            if spawn_group == "spawn warrior":
                cost = 12
            else:
                cost = 10

            # Account for the spawned villagers' future meal reserve too.
            affordable_pairs = max(0, (wheat - population) // (cost + 1))
            target_pairs = max(0, (7 - warrior_count)) if spawn_group == "spawn warrior" else 1
            pair_count = min(len(spawn_candidates) // 2, affordable_pairs, target_pairs)

            for v in spawn_candidates[:2 * pair_count]:
                put(v, spawn_group)

        # Keep the remaining Farmers working and send available Warriors to
        # the Cave. Once the Dragon is near defeat, send every healthy villager.
        for v in list(remaining):
            role = self._get(v, "role", "")
            hp = self._get(v, "hp", 0)
            age = self._get(v, "steps_since_meal", 0)

            if dragon_hp > 0 and hp > 0 and age < 4:
                if role == "Warrior" or dragon_hp <= 15:
                    put(v, "cave")
                else:
                    put(v, "farm")
            else:
                put(v, "farm")

        # Explicitly assign every component, including any unusual leftovers.
        for v in villagers:
            if id(v) not in assigned_ids:
                self._assign(environment, v, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, self._get(environment.dragon, "hp", 0))

        for v in components:
            age = self._get(v, "steps_since_meal", 0)
            hp = self._get(v, "hp", 0)
            role = self._get(v, "role", "")

            if dragon_hp <= 0:
                self._assign(environment, v, "village")
            elif age >= 4:
                # Leave time to travel back and eat before the starvation
                # threshold.
                self._assign(environment, v, "village")
            elif hp <= 1 and dragon_hp > 15:
                # Withdraw only critically wounded villagers while the fight
                # is still expected to continue.
                self._assign(environment, v, "village")
            elif role == "Farmer" and dragon_hp > 15:
                self._assign(environment, v, "village")
            else:
                self._assign(environment, v, "attack")
```