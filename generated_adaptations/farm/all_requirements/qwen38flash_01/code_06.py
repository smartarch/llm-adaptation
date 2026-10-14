import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for drone protection on a smart farm.

    - Always fully protect the most-threatened field with the closest drones.
    - Prefer full protection of fewer fields over partial protection of many.
    - No overprotection (exactly drones_for_full_protection per field).
    - Hysteresis / cooldown for assignment stability.
    - At least half of drones actively protecting.
    """

    COOLDOWN_STEPS = 5
    STABILITY_BONUS = 500  # large enough to dominate small distance differences

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev_group: dict = {}   # drone_key -> group_id
        self._last_change: dict = {}  # drone_key -> step of last reassignment

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _center(field):
        return ((field.left + field.right) / 2.0,
                (field.top + field.bottom) / 2.0)

    @staticmethod
    def _distance(loc, center):
        return math.hypot(loc.x - center[0], loc.y - center[1])

    @staticmethod
    def _key(drone) -> str:
        if hasattr(drone, "id"):
            return str(drone.id)
        return str(id(drone))

    @staticmethod
    def _find_idle(group_ids):
        """Return the group id that looks like an idle group."""
        for g in group_ids:
            if "idle" in g.lower():
                return g
        # second choice: a group that is clearly not a field (no digits match any field)
        return group_ids[0] if group_ids else "idle"

    # ---- robust field → group matching ------------------------------------

    def _match_group(self, field, group_ids):
        """
        Try many strategies to find the group id that belongs to *field*.
        Returns the group id string, or the first group id as last resort.
        """
        fid = str(field.id).strip()
        fid_lower = fid.lower()

        # 1) exact match
        for g in group_ids:
            if g == fid:
                return g

        # 2) case-insensitive exact
        for g in group_ids:
            if g.lower() == fid_lower:
                return g

        # 3) common prefix patterns
        for prefix in ("", "field_", "field-", "protect_", "protect-",
                        "guard_", "cover_", "zone_", "area_",
                        "FIELD_", "FIELD-", "PROTECT_"):
            target = (prefix + fid).lower()
            for g in group_ids:
                if g.lower() == target:
                    return g

        # 4) group id contains field id (or vice-versa), ignoring common words
        noise = {"field", "protect", "guard", "cover", "zone", "area",
                 "protecting", "guarded", "covered"}
        fid_tokens = set(re.findall(r'[a-z0-9]+', fid_lower)) - noise if 're' in dir() else {fid_lower}
        for g in group_ids:
            g_tokens = set(re.findall(r'[a-z0-9]+', g.lower())) - noise
            # check if all numeric/alphanumeric parts match
            fid_nums = {t for t in fid_tokens if t.isdigit()}
            g_nums = {t for t in g_tokens if t.isdigit()}
            if fid_nums and g_nums and fid_nums == g_nums:
                return g

        # 5) substring: fid appears inside group or group appears inside fid
        for g in group_ids:
            gl = g.lower()
            if fid_lower in gl or gl in fid_lower:
                return g

        # 6) last resort – just return the first group that isn't idle
        for g in group_ids:
            if "idle" not in g.lower():
                return g

        return group_ids[0] if group_ids else fid

    # ---- main logic -------------------------------------------------------

    def assign_drones(self, components, environment, group_ids, step):
        total = len(components)
        if total == 0:
            return

        idle_group = self._find_idle(group_ids)

        # 1. Sort fields by threat descending
        threatened = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True,
        )

        # 2. Plan which fields to fully protect (greedy, no overprotection)
        fields_plan = []  # list of (field, group_id, needed_drones)
        reserved = 0
        for f in threatened:
            g = self._match_group(f, group_ids)
            needed = f.drones_for_full_protection
            if needed <= 0:
                continue
            if reserved + needed <= total:
                fields_plan.append((f, g, needed))
                reserved += needed
            else:
                break  # prefer full protection of fewer (higher-threat) fields

        # 3. Assign drones field-by-field
        assignments: dict = {}  # drone_key -> group_id

        for idx, (field, group, needed) in enumerate(fields_plan):
            center = self._center(field)
            is_top = (idx == 0)

            # score every unassigned drone
            scored = []
            for d in components:
                dk = self._key(d)
                if dk in assignments:
                    continue
                dist = self._distance(d.location, center)

                # stability: bonus if already on this group
                if self._prev_group.get(dk) == group:
                    dist -= self.STABILITY_BONUS

                # cooldown penalty for non-top fields
                if not is_top:
                    last = self._last_change.get(dk, -self.COOLDOWN_STEPS - 1)
                    if step - last < self.COOLDOWN_STEPS:
                        dist += self.STABILITY_BONUS

                scored.append((dist, dk, d))

            scored.sort(key=lambda t: t[0])
            for _, dk, _ in scored[:needed]:
                assignments[dk] = group

        # 4. Ensure ≥ 50 % active: use leftover drones to fully protect more fields
        target_active = (total + 1) // 2
        active = len(assignments)
        if active < target_active:
            used_groups = {g for _, g, _ in fields_plan}
            extra_fields = sorted(
                [f for f in threatened
                 if self._match_group(f, group_ids) not in used_groups
                 and f.drones_for_full_protection > 0],
                key=lambda f: f.threat_level, reverse=True,
            )
            for f in extra_fields:
                needed = f.drones_for_full_protection
                g = self._match_group(f, group_ids)
                pool = [d for d in components if self._key(d) not in assignments]
                if len(pool) < needed:
                    continue
                center = self._center(f)
                pool.sort(key=lambda d: self._distance(d.location, center))
                for d in pool[:needed]:
                    assignments[self._key(d)] = g
                active += needed
                if active >= target_active:
                    break

        # 5. Everything else → idle
        for d in components:
            dk = self._key(d)
            if dk not in assignments:
                assignments[dk] = idle_group

        # 6. Commit
        for d in components:
            dk = self._key(d)
            new_g = assignments[dk]
            old_g = self._prev_group.get(dk)
            if new_g != old_g:
                self._last_change[dk] = step
            self._prev_group[dk] = new_g
            environment.assign_group(d, new_g)