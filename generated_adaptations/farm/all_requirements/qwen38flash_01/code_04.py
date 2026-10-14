import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for drone protection on a smart farm.

    - Always fully protect the most threatened field with the closest drones.
    - Prefer full protection of fewer fields over partial protection of many.
    - No overprotection (exactly drones_for_full_protection per field).
    - Hysteresis / cooldown for assignment stability.
    - At least half of drones actively protecting.
    """

    COOLDOWN_STEPS = 5
    STABILITY_BONUS = 200

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev_group: dict[str, str] = {}
        self._last_change: dict[str, int] = {}

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
    def _find_idle(group_ids: list[str]) -> str:
        for g in group_ids:
            if "idle" in g.lower():
                return g
        return group_ids[-1] if group_ids else "idle"

    def _match_group(self, field, group_ids: list[str]) -> str | None:
        """Return the group id that corresponds to *field*, or None."""
        fid = str(field.id)
        if fid in group_ids:
            return fid
        # try without surrounding whitespace / common prefixes
        for g in group_ids:
            stripped = g.strip().lower()
            if stripped == fid.lower():
                return g
            if stripped == f"field_{fid}".lower():
                return g
            if stripped == f"field-{fid}".lower():
                return g
            if stripped == f"field{fid}".lower():
                return g
        # numeric fallback
        try:
            fid_int = str(int(field.id))
            if fid_int in group_ids:
                return fid_int
        except (ValueError, TypeError):
            pass
        return None

    # ---- main logic -------------------------------------------------------

    def assign_drones(self, components, environment, group_ids, step):
        total = len(components)
        if total == 0:
            return

        idle_group = self._find_idle(group_ids)

        # 1. Collect threatened fields sorted by threat descending
        threatened = [f for f in environment.fields if f.threat_level > 0]
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        # 2. Greedy: decide which fields to fully protect
        fields_plan: list[tuple[object, str]] = []   # (field, group_id)
        drones_reserved = 0
        for f in threatened:
            g = self._match_group(f, group_ids)
            if g is None:
                continue
            needed = f.drones_for_full_protection
            if drones_reserved + needed <= total:
                fields_plan.append((f, g))
                drones_reserved += needed
            # do NOT break – a later field might need fewer drones;
            # but per spec we prefer full-protection of higher-threat fields,
            # so we stop at first shortfall.
            else:
                break

        # 3. Assign drones field-by-field (most threatened first)
        assignments: dict[str, str] = {}          # drone_key -> group_id
        remaining: list = list(components)

        for idx, (field, group) in enumerate(fields_plan):
            needed = field.drones_for_full_protection
            center = self._center(field)

            # build scored candidate list
            scored = []
            for d in remaining:
                dk = self._key(d)
                if dk in assignments:
                    continue
                dist = self._distance(d.location, center)

                # stability bonus for drones already on this group
                if self._prev_group.get(dk) == group:
                    dist -= self.STABILITY_BONUS

                # cooldown penalty for non-top fields
                if idx > 0:
                    last = self._last_change.get(dk, -self.COOLDOWN_STEPS - 1)
                    if step - last < self.COOLDOWN_STEPS:
                        dist += self.STABILITY_BONUS  # discourage switch

                scored.append((dist, dk, d))

            scored.sort(key=lambda t: t[0])

            chosen = scored[:needed]
            for _, dk, _ in chosen:
                assignments[dk] = group

        # 4. Try to use leftover drones to fully protect more fields
        #    so that at least 50 % of drones are active.
        target_active = (total + 1) // 2
        active_count = len(assignments)
        leftover = [d for d in components if self._key(d) not in assignments]

        if active_count < target_active:
            protected_groups = {g for _, g in fields_plan}
            extra_fields = [f for f in threatened
                            if self._match_group(f, group_ids) not in protected_groups]
            extra_fields.sort(key=lambda f: f.threat_level, reverse=True)

            for f in extra_fields:
                if len(leftover) < f.drones_for_full_protection:
                    continue
                g = self._match_group(f, group_ids)
                if g is None:
                    continue
                center = self._center(f)
                leftover.sort(key=lambda d: self._distance(d.location, center))
                take = leftover[:f.drones_for_full_protection]
                for d in take:
                    assignments[self._key(d)] = g
                leftover = leftover[f.drones_for_full_protection:]
                active_count += len(take)
                if active_count >= target_active:
                    break

        # 5. Anything still unassigned → idle
        for d in components:
            dk = self._key(d)
            if dk not in assignments:
                assignments[dk] = idle_group

        # 6. Commit assignments and update bookkeeping
        for d in components:
            dk = self._key(d)
            new_g = assignments[dk]
            old_g = self._prev_group.get(dk)

            if new_g != old_g:
                self._last_change[dk] = step

            self._prev_group[dk] = new_g
            environment.assign_group(d, new_g)