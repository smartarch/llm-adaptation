class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        n = len(components)
        if n == 0:
            return []

        # ---- Collect field data; NEVER skip a threatened field ----
        fields = list(getattr(environment, "fields", []))
        field_data = []  # (threat, need, group_id_int, cx, cy)

        for idx, f in enumerate(fields):
            # Read threat (default to 1.0 if missing so field is still protected)
            try:
                threat = float(getattr(f, "threat_level", 1.0))
            except (TypeError, ValueError):
                threat = 1.0
            if threat <= 0:
                continue

            # Read required drones (default 2 if missing)
            try:
                need = int(getattr(f, "drones_for_full_protection", 2))
            except (TypeError, ValueError):
                need = 2
            if need < 1:
                need = 1

            # Group id: use field's own integer group_id, else its index.
            # Do NOT stringify.
            fid = getattr(f, "group_id", None)
            if fid is None:
                fid = getattr(f, "id", idx)
            try:
                fid = int(fid)
            except (TypeError, ValueError):
                fid = idx

            l = float(getattr(f, "left", 0.0) or 0.0)
            r = float(getattr(f, "right", 0.0) or 0.0)
            t = float(getattr(f, "top", 0.0) or 0.0)
            b = float(getattr(f, "bottom", 0.0) or 0.0)
            cx, cy = (l + r) / 2.0, (t + b) / 2.0

            field_data.append((threat, need, fid, cx, cy))

        # Sort by threat descending
        field_data.sort(key=lambda x: x[0], reverse=True)

        # ---- Pre-compute drone positions ----
        dpos = []
        for d in components:
            loc = getattr(d, "location", None)
            x = float(getattr(loc, "x", 0.0) or 0.0) if loc is not None else 0.0
            y = float(getattr(loc, "y", 0.0) or 0.0) if loc is not None else 0.0
            dpos.append((x, y))

        # ---- Greedy: closest unused drones to highest-threat field ----
        assignments = [group_id] * n   # integer group ids
        used = [False] * n

        for _thr, need, fid, cx, cy in field_data:
            cands = []
            for i in range(n):
                if used[i]:
                    continue
                dx = dpos[i][0] - cx
                dy = dpos[i][1] - cy
                cands.append((dx * dx + dy * dy, i))
            cands.sort()
            for k in range(min(need, len(cands))):
                di = cands[k][1]
                assignments[di] = fid
                used[di] = True

        # ---- Apply assignments (integer group ids) ----
        for i, d in enumerate(components):
            g = assignments[i]
            try:
                d.group = g
            except Exception:
                pass
            try:
                d.group_id = g
            except Exception:
                pass

        return assignments