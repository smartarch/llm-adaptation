class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        # Collect all drones that still need a group
        unassigned = list(components)
        assigned_field = {}  # drone -> field reference

        # Collect active fields with their metadata, never crashing
        fields_meta = []
        try:
            raw_fields = list(environment.fields)
        except Exception:
            raw_fields = []

        for f in raw_fields:
            try:
                threat = self._read_num(f, 'threat_level')
            except Exception:
                threat = 0
            try:
                needed = self._read_num(f, 'drones_for_full_protection')
            except Exception:
                needed = 0
            needed = int(needed)
            if threat <= 0 or needed <= 0:
                continue
            fields_meta.append((threat, needed, f))

        # Sort highest threat first
        fields_meta.sort(key=lambda t: t[0], reverse=True)

        # Greedy assignment: for each field in threat order,
        # give it the closest unassigned drones (up to `needed`)
        for threat, needed, f in fields_meta:
            if not unassigned:
                break

            cx, cy = self._center(f)

            # Score available drones by squared distance
            scored = []
            for d in unassigned:
                dx, dy = self._pos(d)
                dsq = (dx - cx) ** 2 + (dy - cy) ** 2
                scored.append((dsq, d))
            scored.sort(key=lambda t: t[0])

            count = min(needed, len(scored))
            for i in range(count):
                d = scored[i][1]
                assigned_field[id(d)] = f
                unassigned.remove(d)

        # Park leftover drones in idle
        for d in unassigned:
            self._set_group(d, group_id)

        # Assign field drones using the field's own identifier
        for d in components:
            f = assigned_field.get(id(d))
            if f is None:
                continue
            gname = self._field_group_name(f)
            self._set_group(d, gname)

    # ---------- helpers ----------

    @staticmethod
    def _read_num(obj, attr, default=0):
        v = getattr(obj, attr, None)
        if v is None:
            return default
        try:
            return float(v)
        except (TypeError, ValueError):
            try:
                return float(v())
            except Exception:
                return default

    @staticmethod
    def _center(f):
        l = SmartFarmAdaptation._read_num(f, 'left')
        r = SmartFarmAdaptation._read_num(f, 'right')
        t = SmartFarmAdaptation._read_num(f, 'top')
        b = SmartFarmAdaptation._read_num(f, 'bottom')
        return (l + r) / 2.0, (t + b) / 2.0

    @staticmethod
    def _pos(d):
        loc = getattr(d, 'location', None)
        if loc is None:
            return 0.0, 0.0
        return SmartFarmAdaptation._read_num(loc, 'x'), SmartFarmAdaptation._read_num(loc, 'y')

    @staticmethod
    def _field_group_name(f):
        # Try common identifier attributes in order of likelihood
        for attr in ('group_id', 'id', 'name', 'key'):
            try:
                v = getattr(f, attr, None)
                if v is not None:
                    return str(v)
            except Exception:
                pass
        return str(id(f))

    @staticmethod
    def _set_group(d, gname):
        try:
            d.group = gname
        except Exception:
            try:
                d.group_id = gname
            except Exception:
                try:
                    d.target_id = gname
                except Exception:
                    pass