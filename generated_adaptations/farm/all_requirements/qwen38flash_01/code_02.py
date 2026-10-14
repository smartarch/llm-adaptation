import math


class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for drone protection on a smart farm.
    
    Strategy:
    - Always fully protect the most threatened field with the closest drones.
    - Prefer full protection of fewer fields over partial protection of many.
    - No overprotection.
    - Hysteresis / cooldown to maintain assignment stability.
    - At least half of drones actively protecting.
    """

    COOLDOWN_STEPS = 5  # Minimum steps between reassignments (non-critical)
    STABILITY_THRESHOLD = 0.5  # fraction of drones that should stay put

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._prev_assignment = {}   # drone_id (str) -> group_id
        self._last_change_step = {}  # drone_id (str) -> step of last change
        self._step_counter = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _field_center(field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return (cx, cy)

    @staticmethod
    def _dist(loc, center):
        dx = loc.x - center[0]
        dy = loc.y - center[1]
        return math.sqrt(dx * dx + dy * dy)

    def _drone_id(self, drone):
        """Stable identifier for a drone."""
        # Prefer explicit id attribute; fall back to string repr
        if hasattr(drone, "id"):
            return str(drone.id)
        return str(id(drone))

    def _resolve_group(self, field, group_ids):
        """Map a field to its corresponding group_id."""
        fid = str(field.id)
        # Try exact match, then common patterns
        candidates = [fid, f"field_{fid}", f"protect_{fid}", f"field_{fid}_protect"]
        for c in candidates:
            if c in group_ids:
                return c
        # If group_ids contains numeric ids, try int match
        try:
            fid_int = str(int(field.id))
            if fid_int in group_ids:
                return fid_int
        except (ValueError, TypeError):
            pass
        # Last resort: return the field id string and hope assign_group handles it
        return fid

    def _find_idle_group(self, group_ids):
        for g in group_ids:
            if "idle" in g.lower():
                return g
        # If there is no explicit idle group, pick the last group or a safe default
        return group_ids[-1] if group_ids else "idle"

    # ------------------------------------------------------------------
    # Main logic
    # ------------------------------------------------------------------
    def assign_drones(self, components, environment, group_ids, step):
        self._step_counter = step

        # --- 1. Gather and sort threatened fields ---
        threatened = [f for f in environment.fields if f.threat_level > 0]
        threatened.sort(key=lambda f: f.threat_level, reverse=True)

        total = len(components)
        if total == 0:
            return

        # --- 2. Decide how many fields to fully protect ---
        # Greedy: take fields in threat order until we run out of drones.
        fields_to_protect = []
        drones_committed = 0
        for f in threatened:
            needed = f.drones_for_full_protection
            if drones_committed + needed <= total:
                fields_to_protect.append(f)
                drones_committed += needed
            else:
                break  # prefer full protection of fewer fields

        # --- 3. Assign the most threatened field with the closest drones ---
        # (stability is overridden for the #1 field)
        assignments = {}  # drone_id -> group_id
        assigned_set = set()  # drone ids already placed

        remaining = list(components)

        for idx, field in enumerate(fields_to_protect):
            group = self._resolve_group(field, group_ids)
            needed = field.drones_for_full_protection
            center = self._field_center(field)

            # Score each available drone; lower is better
            candidates = []
            for d in remaining:
                did = self._drone_id(d)
                if did in assigned_set:
                    continue
                dist = self._dist(d.location, center)
                # Stability bonus: if drone was previously on THIS field, subtract bonus
                prev = self._prev_assignment.get(did)
                bonus = 0
                if prev == group:
                    bonus = -200  # strong preference to stay
                # For the #1 threatened field, ignore cooldown (always override)
                cooldown_ok = True
                if idx > 0:  # not the most threatened field
                    last = self._last_change_step.get(did, -999)
                    if (step - last) < self.COOLDOWN_STEPS:
                        # Only override cooldown for #1 field
                        cooldown_ok = True  # we already handle idx>0 below
                candidates.append((dist + bonus, did, d, cooldown_ok))

            candidates.sort(key=lambda x: x[0])

            # Pick 'needed' drones, preferring stable ones for non-top fields
            chosen = []
            skipped_stable = []
            for score, did, d, cool_ok in candidates:
                if len(chosen) >= needed:
                    break
                if idx > 0 and not cool_ok:
                    skipped_stable.append((score, did, d))
                    continue
                chosen.append((score, did, d))

            # If we need more (due to cooldown skips), fill from skipped
            if len(chosen) < needed:
                for score, did, d in skipped_stable:
                    if len(chosen) >= needed:
                        break
                    chosen.append((score, did, d))

            for _, did, d in chosen:
                assignments[did] = group
                assigned_set.add(did)

        # --- 4. Distribute leftover drones (ensure ≥50% active) ---
        idle_group = self._find_idle_group(group_ids)
        unassigned = [d for d in components if self._drone_id(d) not in assigned_set]

        # How many more active drones to reach 50%?
        active_count = len(assigned_set)
        target_active = (total + 1) // 2
        extra_needed = max(0, target_active - active_count)

        # Try to fully protect additional fields with leftover drones
        already_protected = set(self._resolve_group(f, group_ids) for f in fields_to_protect)
        leftover_fields = [f for f in threatened if self._resolve_group(f, group_ids) not in already_protected]
        leftover_fields.sort(key=lambda f: f.threat_level, reverse=True)

        extra_assigned = 0
        for field in leftover_fields:
            if extra_assigned >= extra_needed:
                break
            group = self._resolve_group(field, group_ids)
            needed = field.drones_for_full_protection
            center = self._field_center(field)

            pool = [d for d in unassigned if self._drone_id(d) not in assigned_set]
            pool.sort(key=lambda d: self._dist(d.location, center))

            if len(pool) >= needed:
                for d in pool[:needed]:
                    did = self._drone_id(d)
                    assignments[did] = group
                    assigned_set.add(did)
                extra_assigned += needed

        # --- 5. Remaining drones → idle ---
        for d in components:
            did = self._drone_id(d)
            if did not in assigned_set:
                assignments[did] = idle_group

        # --- 6. Apply assignments & update tracking ---
        for d in components:
            did = self._drone_id(d)
            new_group = assignments.get(did, idle_group)
            old_group = self._prev_assignment.get(did)

            if new_group != old_group:
                self._last_change_step[did] = step

            self._prev_assignment[did] = new_group
            environment.assign_group(d, new_group)