Reasoning and Strategy:

- High-level goal: kill the Dragon as fast as possible while obeying the group constraints and spawn mechanics.
- Core idea: Keep all Warriors together in the Cave to maximize their combined attack on the Dragon as early as possible. All Farmers stay in the Village to farm and to spawn more villagers when possible.
- Spawn strategy: Use the two dedicated spawn groups to generate new villagers. For spawning, you need pairs of villagers in the spawn group plus a fixed amount of wheat:
  - spawn farmer: every 2 villagers in that group plus 10 wheat yields 1 new Farmer.
  - spawn warrior: every 2 villagers in that group plus 12 wheat yields 1 new Warrior.
  We want a few extra farmers and a few extra warriors to increase killing chances, especially early. To do this safely, we:
  - Keep existing farmers in villagers’ Village: most stay in "farm", some can join "spawn farmer" if wheat allows.
  - Move all Warriors to the Cave (via "cave" or "attack" routing) so they can attack when they arrive.
  - In the Village, compute how many spawns are possible given current wheat and the number of eligible villagers, and allocate up to 2 spawns for each type when possible. This creates extra fighters without overly depleting villagers from farming.
- Cave phase: In the Cave, all Warriors attack the Dragon (assign to "attack"). All Farmers that happened to be in the Cave (if any) should go back to the Village (assign to "village"), since Farmers should stay in Village per the requirements.
- Step constraints:
  - The Dragon should be attacked at least once within the first 15 steps. Since we move Warriors to the Cave in the Village phase and set them to attack in the Cave phase, an attack should occur early.
  - All Warriors should eventually go to the Cave and attack; by design, we route Warriors toward "cave" then "attack" in the next phase.
  - At least half of the Warriors should be in the Cave most of the time: our strategy places all Warriors into the Cave (either in "cave" or "attack") as appropriate.
  - Spawn of both farmers and warriors is attempted whenever wheat and available villagers permit, ensuring a few extra villagers exist to help kill the Dragon.

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Divide villagers in the Village into farming, cave-bound warriors, and spawn groups.
        # Farmers stay in Village (farm) or spawn more villagers (spawn farmer).
        # Warriors move to Cave (cave) to eventually attack Dragon, and may spawn more warriors (spawn warrior).

        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available (best effort; farm object may be absent in some test environments)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # How many spawns are possible this step
        max_farm_spawns = 0
        if len(farmers) >= 2:
            max_farm_spawns = min(len(farmers) // 2, wheat // 10)

        max_war_spawns = 0
        if len(warriors) >= 2:
            max_war_spawns = min(len(warriors) // 2, wheat // 12)

        # We'll spawn up to 2 of each type if possible
        farm_spawn = min(2, max_farm_spawns)
        war_spawn = min(2, max_war_spawns)

        # Allocate farmers for spawning
        spawn_farm = farmers[:farm_spawn * 2]
        # Remaining farmers stay in farm
        for c in farmers[farm_spawn * 2:]:
            environment.assign_group(c, "farm")

        # Allocate warriors for spawning
        spawn_war = warriors[:war_spawn * 2]
        # Remaining warriors go to cave (to eventually attack)
        for c in warriors[war_spawn * 2:]:
            environment.assign_group(c, "cave")

        # Assign spawn groups for spawning (they will generate new villagers)
        for c in spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_war:
            environment.assign_group(c, "spawn warrior")

        # If there are any villagers not yet assigned (edge cases), ensure they get assigned.
        # In this setup, all villagers are accounted for above.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, every Warrior should attack the Dragon; Farmers should return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```