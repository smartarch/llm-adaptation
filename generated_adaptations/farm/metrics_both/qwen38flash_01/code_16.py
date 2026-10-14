class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        try:
            return self._plan(components, environment, group_id)
        except Exception:
            # Absolute fallback: everyone idle, never return None
            return [group_id] * len(components)

    def _plan(self, components, environment, group_id):
        n = len(components)
        if n == 0:
            return []

        # ---- Gather fields ----
        fields = list(getattr(environment, 'fields', []))
        m = len(fields)

        def num(o, a, d=0):
            v = getattr(o, a, d)
            try:
                return float(v)
            except Exception:
                try:
                    return float(v())
                except Exception:
                    return d

        def center(f):
            return ((num(f, 'left') + num(f, 'right')) / 2.0,
                    (num(f, 'top') + num(f, 'bottom')) / 2.0)

        def pos(d):
            loc = getattr(d, 'location', None)
            if loc is None:
                return (0.0, 0.0)
            return (num(loc, 'x'), num(loc, 'y'))

        # Active fields with (threat, need, center, field_index_as_group_id)
        active = []
        for i, f in enumerate(fields):
            thr = num(f, 'threat_level')
            need = int(num(f, 'drones_for_full_protection', 0))
            if thr > 0 and need > 0:
                active.append((thr, need, center(f), i))
        active.sort(key=lambda t: t[0], reverse=True)

        # ---- Read current drone group (for stickiness) ----
        def cur_group(d):
            for a in ('group_id', 'group', 'target_id'):
                v = getattr(d, a, None)
                if v is not None:
                    try:
                        return int(v)
                    except Exception:
                        return None
            return None

        dpos = [pos(d) for d in components]
        dcur = [cur_group(d) for d in components]

        # ---- Greedy assignment ----
        result = [group_id] * n
        used = [False] * n

        for thr, need, (cx, cy), fidx in active:
            # Candidate drones not yet used, scored by:
            #   (not currently here, distance) — so current-assignees win ties
            cand = []
            for di in range(n):
                if used[di]:
                    continue
                dx = dpos[di][0] - cx
                dy = dpos[di][1] - cy
                dsq = dx * dx + dy * dy
                stick = 0 if dcur[di] == fidx else 1
                cand.append((stick, dsq, di))
            cand.sort()

            k = min(need, len(cand))
            for i in range(k):
                di = cand[i][2]
                result[di] = fidx
                used[di] = True

        # ---- Also mirror assignment onto drone objects (harmless if unused) ----
        for i, d in enumerate(components):
            g = result[i]
            try:
                d.group_id = g
            except Exception:
                try:
                    d.group = g
                except Exception:
                    pass

        return result