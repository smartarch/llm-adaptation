## Diagnosis

Every run so far has failed to kill the Dragon within 30 steps, so the problem is damage throughput, not the eat/starve bookkeeping, which now passes its tests.

- **Too few attackers.** The last version capped the Cave at 4 attackers and only dispatched warriors whose hunger was 1 or less. Many fed warriors stayed in the Village, so damage per step was low.
- **Too little spawning.** Warriors are the only real damage source (3 per attack vs. 1 for farmers), but spawning was gated too tightly to add many.
- **Dragon regeneration.** The Dragon regenerates 5 HP on any step with no attack, so any gap in attacks costs damage.

## Revised strategy: all-in warrior pressure

1. **Send every fed warrior to the Cave.** Warriors with `steps_since_meal <= 1` leave for the Cave. The attacker cap is removed, because 100 HP at 3 damage per hit needs roughly 34 warrior attacks within 30 steps.
2. **Feed first, budgeted by wheat.** Villagers with `steps_since_meal >= 2` eat, most hungry first, limited by the wheat stock. Returning warriors eat on arrival, so they stay below the 6-step starvation limit.
3. **Farmers keep the economy running.** Farmers stay on the farm. Idle farmers are used for early spawns, with at least two farmers kept working so wheat keeps coming in.
4. **Early warrior spawns.** Two farmers are placed in "spawn warrior" when the wheat left after this step's meals covers the 12-wheat cost plus a reserve for next step's meals. Spawning is limited to early steps so new warriors can still attack.
5. **Cave rules.** Warriors attack while fed (`steps_since_meal < 4`) and healthy. They return to the Village when hungry or at 1 HP. Farmers never go to the Cave, since they would die to the Dragon's area attack and their wheat is needed.
6. **Complete assignment.** Every component is assigned exactly once per method.

This maximizes damage per step while keeping every villager fed. I can't guarantee a win, since the Dragon's counterattacks (40% area damage, 20% eat one villager per attacking step) can still wipe out the attackers, but this is the highest-throughput approach that stays within the starvation rule.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Village: villagers at or above this hunger are sent to eat
    EAT_THRESHOLD = 2
    # Cave: warriors at or above this hunger return to the village
    CAVE_RETURN_THRESHOLD = 4
    # Village: warriors this fed (or less) are dispatched to the cave
    DISPATCH_MAX_HUNGER = 1
    # Minimum HP for a warrior to be dispatched to the cave
    WARRIOR_MIN_HP = 2
    # Cave: warriors at or below this HP retreat
    WARRIOR_RETREAT_HP = 1
    # Wheat kept back for next step's meals
    WHEAT_RESERVE = 2
    WARRIOR_SPAWN_COST = 12
    # Spawn only early enough that new warriors can still attack
    SPAWN_STEP_LIMIT = 12
    # Keep at least this many farmers on the farm
    MIN_FARMERS_ON_FARM = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = max(environment.farm.wheat, 0)

        # 1) Feed the most hungry villagers first, limited by available wheat
        needy = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        eaters = needy[:wheat]
        eater_ids = set(id(c) for c in eaters)
        remaining_wheat = wheat - len(eaters)

        rest = [c for c in components if id(c) not in eater_ids]

        # 2) Send every fed, healthy warrior to the cave
        cave_ids = set(
            id(c) for c in rest
            if c.role == "Warrior"
            and c.steps_since_meal <= self.DISPATCH_MAX_HUNGER
            and c.hp >= self.WARRIOR_MIN_HP
        )

        # 3) Spawn warriors from idle farmers while wheat allows
        idle_farmers = [c for c in rest if c.role == "Farmer"]
        spawn_ids = set()
        spare_farmers = len(idle_farmers) - self.MIN_FARMERS_ON_FARM
        if (
            step < self.SPAWN_STEP_LIMIT
            and spare_farmers >= 2
            and remaining_wheat >= self.WARRIOR_SPAWN_COST + self.WHEAT_RESERVE
        ):
            for c in idle_farmers[:2]:
                spawn_ids.add(id(c))

        # 4) Assign every component exactly once
        for c in components:
            cid = id(c)
            if cid in eater_ids:
                environment.assign_group(c, "eat")
            elif cid in cave_ids:
                environment.assign_group(c, "cave")
            elif cid in spawn_ids:
                environment.assign_group(c, "spawn warrior")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            hungry = c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD
            if c.role == "Warrior":
                weak = c.hp <= self.WARRIOR_RETREAT_HP
            else:
                # Farmers should not be in the cave; send any back to farm
                weak = True

            if hungry or weak:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```