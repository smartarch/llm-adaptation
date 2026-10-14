import math
import re

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
    STABILITY_BONUS = 500

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev_group: dict = {}
        self._last_change: dict = {}

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
        for g in group_ids:
            if "idle" in g.lower():
                return g
        return group_ids[0] if group_ids else "idle"

    @staticmethod
    def _tokens(s: str) -> set:
        """Split *s* into alphanumeric tokens without using re."""
        toks: list[str] = []
        cur: list[str] = []
        for ch in s:
            if ch.isalnum():
                cur.append(ch)
            else:
                if cur:
                    toks.append("".join(cur))
                    cur = []
        if cur:
            toks.append("".join(cur))
        return set(toks)

    def _match_group(self, field, group_ids):
        fid = str(field.id).strip()
        fid_lower = fid.lower()

        # 1) exact
        for g in group_ids:
            if g == fid:
                return g

        # 2) case-insensitive exact
        for g in group_ids:
            if g.lower() == fid_lower:
                return g

        # 3) prefix patterns
        prefixes = ["", "field_", "field-", "protect_", "protect-",
                     "guard_", "guard-", "cover_", "zone_", "area_",
                     "FIELD_", "FIELD-", "PROTECT_"]
        for p in prefixes:
            target = (p + fid).lower()
            for g in group_ids:
                if g.lower() == target:
                    return g

        # 4) numeric-token overlap  (e.g. "Field_2" vs "field_2_protect")
        fid_toks = self._tokens(fid_lower)
        fid_nums = {t for t in fid_toks if t.isdigit()}
        if fid_nums:
            for g in group_ids:
                g_nums = {t for t in self._tokens(g.lower()) if t.isdigit()}
                if fid_nums == g_nums and g_nums:
                    return g

        # 5) substring
        for g in group_ids:
            gl = g.lower()
            if fid_lower in gl or gl in fid_lower:
                return g

        # 6) first non-idle group as ultimate fallback
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

        # 1. threatened fields sorted by threat descending
        threatened = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level, reverse=True,
        )

        # 2. plan which fields to fully protect (greedy)
        fields_plan = []  # (field, group_id, needed)
        reserved = 0
        for f in threatened:
            g = self._match_group(f, group_ids)
            needed = int(f.drones_for_full_protection)
            if needed <= 0:
                continue
            if reserved + needed <= total:
                fields_plan.append((f, g, needed))
                reserved += needed
            else:
                break

        # 3. assign drones field-by-field
        assignments: dict = {}

        for idx, (field, group, needed) in enumerate(fields_plan):
            center = self._center(field)
            is_top = (idx == 0)

            scored = []
            for d in components:
                dk = self._key(d)
                if dk in assignments:
                    continue
                dist = self._distance(d.location, center)

                if self._prev_group.get(dk) == group:
                    dist -= self.STABILITY_BONUS

                if not is_top:
                    last = self._last_change.get(dk, -self.COOLDOWN_STEPS - 1)
                    if step - last < self.COOLDOWN_STEPS:
                        dist += self.STABILITY_BONUS

                scored.append((dist, dk))

            scored.sort(key=lambda t: t[0])
            for _, dk in scored[:needed]:
                assignments[dk] = group

        # 4. fill up to 50 % active if possible
        target_active = (total + 1) // 2
        if len(assignments) < target_active:
            used_groups = {g for _, g, _ in fields_plan}
            extra = sorted(
                [f for f in threatened
                 if self._match_group(f, group_ids) not in used_groups
                 and int(f.drones_for_full_protection) > 0],
                key=lambda f: f.threat_level, reverse=True,
            )
            for f in extra:
                needed = int(f.drones_for_full_protection)
                g = self._match_group(f, group_ids)
                pool = [d for d in components
                        if self._key(d) not in assignments]
                if len(pool) < needed:
                    continue
                center = self._center(f)
                pool.sort(key=lambda d: self._distance(d.location, center))
                for d in pool[:needed]:
                    assignments[self._key(d)] = g
                if len(assignments) >= target_active:
                    break

        # 5. leftover → idle
        for d in components:
            dk = self._key(d)
            if dk not in assignments:
                assignments[dk] = idle_group

        # 6. commit
        for d in components:
            dk = self._key(d)
            new_g = assignments[dk]
            old_g = self._prev_group.get(dk)
            if new_g != old_g:
                self._last_change[dk] = step
            self._prev_group[dk] = new_g
            environment.assign_group(d, new_g)