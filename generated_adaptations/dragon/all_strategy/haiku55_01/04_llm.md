## Fixing the failed runs: the dragon was not killed

Seeds 1 and 3 ran out of steps before the Dragon died. The previous strategy caused this in three ways:

1. **Spawning was capped at two of each type.** That limited the warrior count, and the Dragon has 50 HP, so the team needed far more damage output.
2. **Warriors retreated at 1 HP or less.** Retreating removed the most damaging units from the fight just when they were still useful. Dragon hits are probabilistic, so a warrior at low HP still adds damage before it dies.
3. **Farmers never attacked.** Late in the fight, when the Dragon is nearly dead, farmers' 1 damage per attack helps finish it.

The revised strategy:

- **Warriors** attack continuously and never retreat.
- **Spawning is uncapped for warriors.** Whenever wheat is at least 12 and two farmers are available, a pair goes to "spawn warrior". Warriors are the damage source.
- **Farmers are spawned as needed.** A pair goes to "spawn farmer" when wheat is at least 10, but only while the farmer count is below 6, so the farm is not starved. Warriors have priority when both are possible.
- **Farmers join the fight late.** When the Dragon has 10 HP or less, farmers in the Village are sent to the Cave to finish it. Farmers in the Cave attack in that phase instead of returning.
- **Early attack is kept.** Warriors are sent to the Cave from step 1, so the Dragon is attacked well before step 15.

The farmers-and-warriors requirement is still satisfied because the spawn priority keeps both populations growing from the start.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    FARMER_CAP = 6          # stop spawning farmers beyond this count
    FINISH_HP_THRESHOLD = 10  # send farmers to fight when the dragon is this weak

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always go to the cave to attack the dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Late game: when the dragon is nearly dead, farmers also join the fight
        if dragon_hp <= self.FINISH_HP_THRESHOLD:
            for f in farmers:
                environment.assign_group(f, "cave")
            return

        # Choose at most one spawn per step, using a pair of farmers
        spawn_target = None
        if len(farmers) >= 2:
            if wheat >= 12:
                spawn_target = "spawn warrior"
            elif wheat >= 10 and len(farmers) < self.FARMER_CAP:
                spawn_target = "spawn farmer"

        spawn_pair = farmers[:2] if spawn_target is not None else []

        for f in farmers:
            if f in spawn_pair:
                environment.assign_group(f, spawn_target)
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking; they never retreat
                environment.assign_group(c, "attack")
            else:
                # Farmers only fight in the finishing phase
                if dragon_hp <= self.FINISH_HP_THRESHOLD:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")
```