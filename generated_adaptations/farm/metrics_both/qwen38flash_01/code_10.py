class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        try:
            self._run(components, environment, group_id, step)
        except Exception:
            for d in components:
                self._try_assign(d, group_id)

    def _try_assign(self, drone, group):
        """Attempt all known group-assignment mechanisms."""
        # Method 1: self._assign(component, group_name)
        try:
            self._assign(drone, group)
            return
        except Exception:
            pass
        # Method 2: direct .group attribute
        try:
            drone.group = group
            return
        except Exception:
            pass
        # Method 3: self._adapt()
        try:
            self._adapt(drone, group)
            return
        except Exception:
            pass
        # Method 4: .group_id
        try:
            drone.group_id = group
            return
        except Exception:
            pass
        # Method 5: .target
        try:
            drone.target = group
            return
        except Exception:
            pass

    def _run(self, components, environment, group_id, step):
        fields = list(environment.fields)
        if not components or not fields:
            for d in components:
                self._try_assign(d, group_id)
            return

        # --- Build field list sorted by threat desc ---
        active = []
        for idx, f in enumerate(fields):
            threat = getattr(f, 'threat_level', 0)
            if threat <= 0:
                continue
            needed = getattr(f, 'drones_for_full_protection', 1)
            needed = max(1, int(needed))
            # Get group identifier for this field
            gname = getattr(f, 'group_id', idx)
            # Get center
            l = getattr(f, 'left', 0)
            r = getattr(f, 'right', 0)
            t = getattr(f, 'top', 0)
            b = getattr(f, 'bottom', 0)
            cx = (l + r) / 2.0
            cy = (t + b) / 2.0
            active.append((threat, needed, gname, cx, cy))

        active.sort(key=lambda x: x[0], reverse=True)

        # --- Drone info ---
        nd = len(components)
        dpos = []
        dcur = []
        for d in components:
            loc = getattr(d, 'location', None)
            x = getattr(loc, 'x', 0) if loc else 0
            y = getattr(loc, 'y', 0) if loc else 0
            dpos.append((x, y))
            dcur.append(getattr(d, 'group', None))

        # --- Greedy: assign drones to fields in threat order ---
        assigned_group = [group_id] * nd  # default idle

        for threat, needed, gname, cx, cy in active:
            # Score available drones: prefer ones already in this group
            scores = []
            for di in range(nd):
                if assigned_group[di] != group_id:
                    continue  # already assigned to a field
                dx = dpos[di][0] - cx
                dy = dpos[di][1] - cy
                dist = dx * dx + dy * dy
                already = 0 if str(dcur[di]) == str(gname) else 1
                scores.append((already, dist, di))

            scores.sort()
            take = min(needed, len(scores))
            for ci in range(take):
                di = scores[ci][2]
                assigned_group[di] = gname

        # --- Apply all assignments ---
        for di in range(nd):
            self._try_assign(components[di], assigned_group[di])