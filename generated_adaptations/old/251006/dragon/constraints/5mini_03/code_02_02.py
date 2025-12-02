from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # small internal counters for deterministic behavior
        self._step_counter = 0
        # configuration: how many warriors should actively attack in cave at once
        self.ATTACK_SHIFT_SIZE = 2
        # how many warriors to send from village to cave per village assignment (conservative)
        self.SEND_PER_STEP = 1

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Village strategy:
          - Send a small number of Warriors to the Cave ("cave") per step (conservative).
          - Keep most Farmers farming: reserve roughly half the farmers (at least 1) to "farm".
          - From the remaining farmers, allow up to one warrior spawn (if wheat and pairs permit)
            and up to one farmer spawn (if wheat and pairs permit). This is conservative to avoid
            stripping too many farmers from the Village.
          - All unassigned farmers farm.
        """
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_cave = g("cave")
        group_farm = g("farm")
        group_spawn_w = g("spawn warrior")
        group_spawn_f = g("spawn farmer")

        # Partition components deterministically
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # 1) Send a small number of warriors from village to cave (we are conservative)
        send_count = min(self.SEND_PER_STEP, len(warriors))
        # send the first send_count warriors to cave; the rest we leave in village (they will farm)
        for i, w in enumerate(warriors):
            if i < send_count:
                environment.assign_group(w, group_cave)
            else:
                # leave other warriors in village to avoid mass casualties; let them farm
                environment.assign_group(w, group_farm)

        # 2) Farmers: reserve roughly half (to protect the fields); ensure at least 1 farms if any exist
        n_farmers = len(farmers)
        if n_farmers == 0:
            self._step_counter += 1
            return

        # Keep at least half of farmers farming (rounded up), but never more than n_farmers
        reserve_to_farm = max(1, (n_farmers + 1) // 2)

        # split farmers deterministically
        idx = 0
        for _ in range(reserve_to_farm):
            environment.assign_group(farmers[idx], group_farm)
            idx += 1

        # remaining farmers available for possible spawning (in pairs)
        remaining = farmers[idx:]
        remaining_count = len(remaining)
        available_pairs = remaining_count // 2

        wheat = getattr(environment.farm, "wheat", 0)

        # Conservative spawning policy: at most one warrior spawn and at most one farmer spawn per step
        warrior_spawns = 0
        farmer_spawns = 0

        # Try to spawn one warrior if possible (needs 2 villagers and 12 wheat)
        if available_pairs >= 1 and wheat >= 12:
            warrior_spawns = 1
            wheat -= 12
            available_pairs -= 1
            remaining_count -= 2

        # Try to spawn one farmer if possible (needs 2 villagers and 10 wheat)
        if available_pairs >= 1 and wheat >= 10:
            farmer_spawns = 1
            wheat -= 10
            available_pairs -= 1
            remaining_count -= 2

        # Assign spawn warrior pairs (if any)
        r_idx = 0
        for _ in range(warrior_spawns):
            if r_idx + 1 < len(remaining):
                environment.assign_group(remaining[r_idx], group_spawn_w); r_idx += 1
                environment.assign_group(remaining[r_idx], group_spawn_w); r_idx += 1

        # Assign spawn farmer pairs (if any)
        for _ in range(farmer_spawns):
            if r_idx + 1 < len(remaining):
                environment.assign_group(remaining[r_idx], group_spawn_f); r_idx += 1
                environment.assign_group(remaining[r_idx], group_spawn_f); r_idx += 1

        # Any leftover remaining farmers farm
        while r_idx < len(remaining):
            environment.assign_group(remaining[r_idx], group_farm)
            r_idx += 1

        self._step_counter += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Cave strategy:
          - Select up to ATTACK_SHIFT_SIZE healthiest Warriors to "attack".
          - Send any additional Warriors back to the Village ("village") to keep cave population small.
          - Send all Farmers in the Cave back to the Village ("village") to protect them.
        """
        def g(name):
            return name if name in group_ids else group_ids[0]

        group_attack = g("attack")
        group_village = g("village")
        group_cave = g("cave")  # not used for assignments in this strategy but present for completeness

        # Separate warriors and farmers in cave
        warriors = [c for c in components if getattr(c, "role", "").lower() == "warrior"]
        farmers = [c for c in components if getattr(c, "role", "").lower() == "farmer"]

        # Send all farmers back to village (protect fields)
        for f in farmers:
            environment.assign_group(f, group_village)

        # Choose healthiest warriors to attack (sort by hp desc), others go back to village
        warriors_sorted = sorted(warriors, key=lambda x: getattr(x, "hp", 0), reverse=True)
        attackers = warriors_sorted[:self.ATTACK_SHIFT_SIZE]
        non_attackers = warriors_sorted[self.ATTACK_SHIFT_SIZE:]

        for a in attackers:
            environment.assign_group(a, group_attack)
        for n in non_attackers:
            # send back to village to avoid piling up in cave
            environment.assign_group(n, group_village)