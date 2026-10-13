The adaptation strategy prioritizes getting at least one warrior to the Cave early, then builds a small economy by spawning a few extra farmers while also spawning additional warriors. All warriors are always sent to the Cave and assigned to attack; any farmers that end up in the Cave are sent back to the Village. Farmers in the Village are assigned to farm unless there is enough wheat to spawn new villagers, in which case the strategy spawns first the required minimum farmers and warriors, then spends surplus wheat on extra warriors while trying to keep at least two farmers working the farm.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.attack_started = False

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        warriors = []

        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                warriors.append(c)
            else:
                farmers.append(c)

        # All warriors should go to the Cave.
        for w in warriors:
            environment.assign_group(w, "cave")

        F = len(farmers)
        W = len(warriors)
        wheat = getattr(environment.farm, "wheat", 0)

        nF, nW = self._allocate_spawns(F, W, wheat, step, environment)

        idx = 0

        # Spawn farmers.
        for _ in range(nF * 2):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # Spawn warriors.
        for _ in range(nW * 2):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # Remaining farmers work on the farm.
        while idx < F:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        self.spawned_farmers += nF
        self.spawned_warriors += nW

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
                self.attack_started = True
            else:
                # Farmers should stay in the Village.
                environment.assign_group(c, "village")

    def _allocate_spawns(self, F, W, wheat, step, environment):
        nF = 0
        nW = 0
        rem_f = F
        rem_w = wheat

        # Priority 1: if we have no warriors at all, spawn one early so the
        # Dragon is attacked within the first 15 steps.
        if W == 0 and self.spawned_warriors == 0 and not self.attack_started:
            if rem_f >= 2 and rem_w >= 12:
                nW += 1
                rem_f -= 2
                rem_w -= 12

        # Priority 2: spawn at least two new farmers.
        while self.spawned_farmers + nF < 2 and rem_f >= 2 and rem_w >= 10:
            nF += 1
            rem_f -= 2
            rem_w -= 10

        # Priority 3: spawn at least two new warriors.
        while self.spawned_warriors + nW < 2 and rem_f >= 2 and rem_w >= 12:
            nW += 1
            rem_f -= 2
            rem_w -= 12

        # Priority 4: use surplus wheat for extra warriors, but keep at least
        # two farmers working the farm when possible.
        while rem_f >= 4 and rem_w >= 12:
            nW += 1
            rem_f -= 2
            rem_w -= 12

        # If we still have two farmers and enough wheat, and the Dragon is
        # alive, spend them on one more warrior to help finish the fight.
        if rem_f >= 2 and rem_w >= 12 and environment.dragon.hp > 0:
            if self.spawned_warriors + nW < 8:
                nW += 1
                rem_f -= 2
                rem_w -= 12

        return nF, nW
```