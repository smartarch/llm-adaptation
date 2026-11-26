The failures were caused by spending wheat on spawning (and generally running the wheat stock down to zero), so meals could not be paid for — which also caused unassigned/invalid assignments when "eat" failed. Fix: meals get absolute priority, and a **wheat reserve** covering all meals due in the near future (villagers who must eat within ~2 steps, both in the Village and those walking back from the Cave) is kept before any spawning. I also added a final push: when the Dragon is nearly dead, everyone healthy attacks to finish it faster.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon

        # Meals due in the near future (within the next 2 steps), across
        # ALL villagers (Village + Cave), used as a wheat reserve.
        everyone = list(environment.farmers) + list(environment.warriors)
        reserve = sum(1 for c in everyone if 6 - c.steps_since_meal <= 2)

        # 1) Eat first: everyone in the Village who must eat now.
        hungry = sorted(
            (c for c in components if c.steps_since_meal >= 4),
            key=lambda c: -c.steps_since_meal,
        )
        fed = []
        for c in hungry:
            if wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                fed.append(c)
            else:
                break  # no wheat left; they must farm this step

        remaining = [c for c in components if c not in fed]

        # 2) Final push: if the Dragon is nearly dead, everyone healthy attacks.
        if dragon.hp <= 30:
            for c in remaining:
                environment.assign_group(c, "cave")
            return

        # 3) Warriors travel to the Cave (they are useless on the farm).
        for c in list(remaining):
            if c.role == "Warrior":
                environment.assign_group(c, "cave")
                remaining.remove(c)

        # 4) Spawn warriors when affordable while keeping the meal reserve.
        i = 0
        while (
            i + 1 < len(remaining)
            and wheat - 12 >= reserve
        ):
            environment.assign_group(remaining[i], "spawn warrior")
            environment.assign_group(remaining[i + 1], "spawn warrior")
            wheat -= 12
            i += 2
        remaining = remaining[i:]

        # 5) Spawn farmers only with a large surplus (economy growth).
        if wheat - 10 >= reserve + 5:
            i = 0
            while i + 1 < len(remaining) and wheat - 10 >= reserve + 5:
                environment.assign_group(remaining[i], "spawn farmer")
                environment.assign_group(remaining[i + 1], "spawn farmer")
                wheat -= 10
                i += 2
            remaining = remaining[i:]

        # 6) Everyone else farms.
        for c in remaining:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon = environment.dragon
        for c in components:
            if c.steps_since_meal >= 4:
                # Must head home now; arrives in the Village next step
                # and can still eat before starving.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```

Changes vs. the previous version:

- **Meals have absolute priority** — hungry villagers eat before anything else, and "eat" is only assigned while wheat is actually available, so no invalid assignments.
- **Wheat reserve** equal to the number of meals due within the next 2 steps (counted over all villagers, including those returning from the Cave) is never spent on spawning. This fixes the "0 wheat left but meals due" constraint violations.
- **Final push**: once the Dragon drops to ≤ 30 HP, all healthy villagers in the Village rush to the Cave to finish it off, avoiding the end-game loss seen in seed 3.
- Spawning warriors is more aggressive (as long as the reserve is intact), which should shorten the average winning time below the current 22 steps.