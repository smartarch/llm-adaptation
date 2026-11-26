from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def _assign(self, environment, component, group):
        environment.assign_group(component, group)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(0, getattr(environment.farm, "wheat", 0))
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))
        warriors = list(getattr(environment, "warriors", []))
        warrior_count = len(warriors)
        population = warrior_count + len(getattr(environment, "farmers", []))
        available = list(components)

        # Feed villagers with the longest time since their last meal first.
        for villager in sorted(
            available,
            key=lambda c: getattr(c, "steps_since_meal", 0),
            reverse=True,
        ):
            if (
                getattr(villager, "steps_since_meal", 0) >= 4
                and wheat >= 1
            ):
                self._assign(environment, villager, "eat")
                wheat -= 1
                available.remove(villager)

        if dragon_hp <= 0:
            for villager in available:
                self._assign(environment, villager, "farm")
            return

        # Keep a farmer working so wheat continues to accumulate. Spawn from
        # other villagers as soon as the actual warrior cost is available.
        farmers = [v for v in available if getattr(v, "role", "") == "Farmer"]
        farm_worker = None
        if farmers:
            farm_worker = farmers[0]
        elif available:
            farm_worker = available[0]

        # Build a small, sustainable warrior force. Do not require an
        # additional meal reserve before spawning; that delay can prevent
        # warrior production altogether in low-wheat starts.
        target_warriors = max(4, min(7, population))
        while wheat >= 12 and warrior_count < target_warriors:
            candidates = [
                v for v in available
                if v is not farm_worker
            ]
            if len(candidates) < 2:
                break

            # Prefer assigning Farmers to the spawn group; retain the selected
            # farm worker whenever there is another pair available.
            candidates.sort(
                key=lambda c: getattr(c, "role", "") != "Farmer"
            )
            pair = candidates[:2]
            for villager in pair:
                self._assign(environment, villager, "spawn warrior")
                available.remove(villager)

            wheat -= 12
            warrior_count += 1

        # Keep the reserved worker farming unless the Dragon is nearly dead
        # and the immediate damage is more valuable than further food.
        if farm_worker in available:
            remaining_hp = getattr(farm_worker, "hp", 0)
            if dragon_hp > 12 or remaining_hp <= 1:
                self._assign(environment, farm_worker, "farm")
                available.remove(farm_worker)

        # Warriors are the most efficient attackers. Other healthy villagers
        # can also contribute damage when they are not needed for spawning.
        for villager in available:
            if getattr(villager, "hp", 0) > 1:
                self._assign(environment, villager, "cave")
            else:
                self._assign(environment, villager, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = max(0, getattr(environment.dragon, "hp", 0))

        for villager in components:
            if dragon_hp <= 0:
                self._assign(environment, villager, "cave")
                continue

            hunger = getattr(villager, "steps_since_meal", 0)
            hp = getattr(villager, "hp", 0)

            # Leave time for the trip home and the Village meal assignment.
            if hunger >= 3 or hp <= 1:
                self._assign(environment, villager, "village")
            else:
                self._assign(environment, villager, "attack")