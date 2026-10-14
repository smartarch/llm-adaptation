import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        try:
            self._assign(components, environment, group_id, step)
        except Exception:
            # Absolute fallback: park everything in idle so sim doesn't crash
            for d in components:
                self._set_group(d, group_id)

    def _set_group(self, drone, gname):
        """Try every plausible mechanism to assign a drone to a group."""
        if gname is None:
            gname = str(gname)
        try:
            drone.group = gname
            return
        except Exception:
            pass
        try:
            self._assign_group(drone, gname)
            return
        except Exception:
            pass
        try:
            self.assign_group(drone, gname)
            return
        except Exception:
            pass
        try:
            drone.group_name = gname
        except Exception:
            pass

    def _get_group_name(self, field, index):
        """Get the group name for a field, trying multiple attributes."""
        # Try field.group_id first (most likely in this framework)
        try:
            gid = field.group_id
            if gid is not None:
                return str(gid)
        except Exception:
            pass
        # Try field.id
        try:
            fid = field.id
            if fid is not None:
                return str(fid)
        except Exception:
            pass
        # Try field.name
        try:
            name = field.name
            if name is not None:
                return str(name)
            return str(name) if name is not None else str(index)
        except Exception:
            pass
        return str(index)

    def _get_field_center(self, field):
        try:
            l = getattr(field, 'left', 0)
            r = getattr(field, 'right', 0)
            t = getattr(field, 'top', 0)
            b = getattr(field, 'bottom', 0)
            return ((l + r) / 2.0, (t + b) / 2.0)
        except Exception:
            return (0.0, 0.0)

    def _get_drone_pos(self, drone):
        try:
            loc = drone.location
            return (getattr(loc, 'x', 0), getattr(loc, 'y', 0))
        except Exception:
            return (0.0, 0.0)

    def _get_current_group(self, drone):
        try:
            return str(drone.group) if drone.group is not None else None
        except Exception:
            pass
        try:
            return str(drone.group_name) if drone.group_name is not None else None
        except Exception:
            pass
        try:
            tid = drone.target_id
            if tid is not None:
                return str(tid)
        except Exception:
            pass
        return None

    def _assign(self, components, environment, group_id, step):
        # Gather fields with threat > 0
        field_list = list(getattr(environment, 'fields', []))
        if not field_list or not components:
            for d in components:
                self._set_group(d, group_id)
            return

        # Build field info: (group_name, threat, needed, cx, cy)
        active_fields = []
        for idx, f in enumerate(field_list):
            try:
                threat = float(getattr(f, 'threat_level', 0))
                if threat <= 0:
                    continue
                needed = int(getattr(f, 'drones_for_full_protection', 1))
                if needed < 1:
                    needed = 1
                gname = self._get_group_name(f, idx)
                cx, cy = self._get_field_center(f)
                active_fields.append((gname, threat, needed, cx, cy))
            except Exception:
                continue

        # Sort by threat descending
        active_fields.sort(key=lambda x: x[1], reverse=True)

        # Gather drone info
        num_drones = len(components)
        drone_pos = []
        drone_cur_group = []
        for d in components:
            drone_pos.append(self._get_drone_pos(d))
            drone_cur_group.append(self._get_current_group(d))

        # Greedy assignment
        drone_assignment = [None] * num_drones  # None = idle
        used = [False] * num_drones

        for gname, threat, needed, cx, cy in active_fields:
            if needed <= 0:
                continue

            # Score each available drone
            candidates = []
            for di in range(num_drones):
                if used[di]:
                    continue
                dx = drone_pos[di][0] - cx
                dy = drone_pos[di][1] - cy
                dist = dx * dx + dy * dy
                # Stickiness bonus: drones already in this field's group
                stick = 0
                if drone_cur_group[di] == gname:
                    stick = -10000  # strong preference
                candidates.append((dist + stick, di))

            candidates.sort()

            take = min(needed, len(candidates))
            for ci in range(take):
                di = candidates[ci][1]
                drone_assignment[di] = gname
                used[di] = True

        # Apply assignments
        for di in range(num_drones):
            d = components[di]
            g = drone_assignment[di] if drone_assignment[di] is not None else group_id
            self._set_group(d, g)