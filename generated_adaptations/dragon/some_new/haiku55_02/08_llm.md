## Diagnosis

The only remaining failure is a win-within-30-steps check on the `initial_wheat=15,seed=1` scenario. The simulation win rate is 100%, but the average win takes 24.7 steps, so some games come close to the 30-step limit. The fix is to get more warriors into the fight sooner.

The current code spawns at most one pair per step, so it can only add two villagers' worth of spawning per step. When wheat is plentiful, that leaves damage on the table. The Dragon is at full HP for the first several steps, so early warrior production matters most.

## Changes

- **Batch spawning:** Each step, the code now computes how many spawn pairs the wheat budget and the pool of fed, ready villagers allow. It assigns exactly `2k` villagers to the spawn group, so several warriors can be produced in one step.
- **Higher warrior target:** The target rises from 8 to 12 total warriors, so production continues into the mid-game.
- **Farmer growth first, then warriors:** Early farmer spawns (step ≤ 6, up to 6 farmers) grow the wheat economy. Once farmers are established, the code switches to warriors.
- **Wheat accounting:** Meals are reserved first, then spawns use the remaining wheat. Spawns never consume the wheat needed to feed hungry villagers.
- **Assignment integrity:** Every component is still assigned exactly once through a single mapping.

The cave logic is unchanged. Fed warriors attack, and hungry warriors and all farmers return to the Village.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Strategy:
    - Hungry villagers (steps_since_meal >= 3) eat in the Village, most hungry first,
      limited by the wheat stock. Unfed hungry villagers stay on the farm.
    - Spawning batches as many pairs as the wheat budget and fed, ready villagers allow:
        * early on, a few farmer spawns grow the wheat economy;
        * otherwise warrior spawns are made until the warrior target is reached.
      Wheat reserved for meals is subtracted first.
    - Remaining fed warriors go to the Cave and attack while steps_since_meal <= 2.
    - In the Cave, warriors with steps_since_meal >= 3 and all farmers return to the Village.
    - Every component is assigned exactly once in every call.
    """

    EAT_THRESHOLD = 3          # eat in village when hunger reaches this
    RETURN_THRESHOLD = 3       # leave cave to eat when hunger reaches this
    WARRIOR_TARGET = 12        # total warriors we want alive
    FARMER_TARGET = 6          # total farmers we want alive
    EARLY_FARMER_STEP = 6      # farmer spawning only in early game

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_farmers = len(environment.farmers)

        # Hungry villagers, most hungry first
        hungry = sorted(
            [c for c in components if c.steps_since_meal >= self.EAT_THRESHOLD],
            key=lambda c: -c.steps_since_meal,
        )
        # Only feed as many as the wheat stock allows (1 wheat per meal)
        n_eat = max(0, min(len(hungry), wheat))
        eaters = hungry[:n_eat]
        unfed = hungry[n_eat:]
        wheat_avail = wheat - n_eat

        # Fed, ready villagers are the only candidates for spawning or the cave
        ready = [c for c in components if c.steps_since_meal < self.EAT_THRESHOLD]
        ready_farmers = [c for c in ready if c.role == "Farmer"]
        ready_warriors = [c for c in ready if c.role == "Warrior"]
        pool = ready_farmers + ready_warriors  # farmers first as spawn members

        assignment = {}
        for c in eaters:
            assignment[id(c)] = "eat"
        for c in unfed:
            assignment[id(c)] = "farm"

        spawn_members = []
        spawn_group = None

        # Early game: grow the wheat economy with farmer spawns (10 wheat per spawn)
        if step <= self.EARLY_FARMER_STEP and total_farmers < self.FARMER_TARGET:
            k = min(wheat_avail // 10, len(pool) // 2, self.FARMER_TARGET - total_farmers)
            if k > 0:
                spawn_members = pool[:2 * k]
                spawn_group = "spawn farmer"
                wheat_avail -= 10 * k

        # Otherwise: warrior spawns (12 wheat per spawn) until the warrior target
        if spawn_group is None and total_warriors < self.WARRIOR_TARGET:
            k = min(wheat_avail // 12, len(pool) // 2, self.WARRIOR_TARGET - total_warriors)
            if k > 0:
                spawn_members = pool[:2 * k]
                spawn_group = "spawn warrior"
                wheat_avail -= 12 * k

        spawn_ids = set(id(c) for c in spawn_members)
        for c in spawn_members:
            assignment[id(c)] = spawn_group

        for c in ready:
            if id(c) in spawn_ids:
                continue
            if c.role == "Warrior":
                assignment[id(c)] = "cave"
            else:
                assignment[id(c)] = "farm"

        # Every component is assigned exactly once
        for c in components:
            environment.assign_group(c, assignment[id(c)])

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role != "Warrior" or c.steps_since_meal >= self.RETURN_THRESHOLD:
                environment.assign_group(c, "village")
            elif c.hp > 0:
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")
```