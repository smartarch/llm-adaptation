import math
from typing import List, Dict, Set, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    MOMENTUM_WINDOW = 3
    MOMENTUM_BOOST = 0.15
    MAX_MOVES_PER_STEP_FRACTION = 0.33

    def _group_for_field(self, field, group_ids: List[str]) -> str:
        fid = str(field.id)
        for gid in group_ids:
            if gid == "idle":
                continue
            if gid == fid:
                return gid
        for gid in group_ids:
            if gid == "idle":
                continue
            if fid in gid:
                return gid
        return "idle"

    @staticmethod
    def _center(field):
        return ((field.left + field.right) * 0.5,
                (field.top + field.bottom) * 0.5)

    def _dist(self, drone, field) -> float:
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _field_dist(self, f1, f2) -> float:
        c1 = self._center(f1); c2 = self._center(f2)
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

    def _parse_target(self, drone, field_id_set: Set[str]) -> Optional[str]:
        tgt = getattr(drone, 'target_id', None)
        if tgt is None:
            return None
        t = str(tgt)
        if not t or t.lower() == "idle":
            return None
        if t in field_id_set:
            return t
        for fid in field_id_set:
            if fid in t or t in fid:
                return fid
        return None

    def _effective_threat(self, field) -> float:
        """Base threat with momentum boost if rising."""
        fid = str(field.id)
        history = self._threat_history.get(fid, [])
        base = field.threat_level
        if len(history) >= 2:
            # Check if rising: compare current to average of past
            past_avg = sum(history[:-1]) / (len(history) - 1)
            if base > past_avg * 1.1:  # rising
                return base * (1.0 + self.MOMENTUM_BOOST)
        return base

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        # --- Track threat history ---
        if not hasattr(self, '_threat_history'):
            self._threat_history: Dict[str, List[float]] = {}
        for f in environment.fields:
            fid = str(f.id)
            hist = self._threat_history.setdefault(fid, [])
            hist.append(f.threat_level)
            if len(hist) > self.MOMENTUM_WINDOW:
                hist.pop(0)

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort by effective threat (with momentum) descending
        active.sort(key=lambda f: self._effective_threat(f), reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in active}
        field_ids: Set[str] = set(field_by_id.keys())

        # --- Current target (in-transit counts as at target) ---
        current: Dict[int, Optional[str]] = {}
        for d in components:
            current[id(d)] = self._parse_target(d, field_ids)

        # --- Determine protectable fields ---
        cumulative = 0
        n_full = 0
        for f in active:
            c = f.drones_for_full_protection
            if cumulative + c <= total_drones:
                cumulative += c
                n_full += 1
            else:
                break
        if n_full == 0:
            n_full = 1

        protected_fields = active[:n_full]
        protected_ids = [str(f.id) for f in protected_fields]

        # --- Compute target allocation ---
        pool: Set[int] = set(id(d) for d in components)
        target: Dict[str, List[int]] = {str(f.id): [] for f in active}

        # Assign closest drones to each protected field (priority order)
        for f in protected_fields:
            fid = str(f.id)
            cap = f.drones_for_full_protection
            avail = sorted([d for d in components if id(d) in pool],
                           key=lambda d: self._dist(d, f))
            for d in avail:
                if len(target[fid]) >= cap:
                    break
                if id(d) in pool:
                    target[fid].append(id(d))
                    pool.discard(id(d))

        # Surplus: place on the protected field closest to the NEXT threat
        # (pre-positioning for likely threat shifts)
        if pool:
            # Find next-highest threat field NOT in protected set
            next_threat_field = None
            for f in active:
                if str(f.id) not in protected_ids:
                    next_threat_field = f
                    break

            for d in [d for d in components if id(d) in pool]:
                # Pick the protected field closest to next_threat_field
                # (so reserve can reach it fast)
                if next_threat_field:
                    best_f = min(protected_fields,
                                 key=lambda pf: self._field_dist(pf, next_threat_field))
                else:
                    best_f = protected_fields[0]
                fid = str(best_f.id)
                target[fid].append(id(d))
                pool.discard(id(d))

        # Safety: any unassigned → top protected field
        if pool:
            for d in components:
                if id(d) in pool:
                    target[protected_ids[0]].append(id(d))
                    pool.discard(id(d))

        # --- Minimum-change assignment ---
        # Phase 1: drones already at their target field stay (includes in-transit)
        final: Dict[int, str] = {}
        claimed: Set[int] = set()

        for fid in protected_ids:
            for did in target[fid]:
                if current.get(did) == fid:
                    final[did] = fid
                    claimed.add(did)

        # Phase 2: fill remaining slots. Pull from donor fields with most surplus,
        # preferring drones closest to the TARGET field (minimize transit).
        # First compute keep counts and current counts per field.
        keep_per_field: Dict[Optional[str], int] = {}
        for d in components:
            did = id(d)
            if did in final:
                f = final[did]
                keep_per_field[f] = keep_per_field.get(f, 0) + 1
            elif current.get(did):
                c = current[did]
                keep_per_field[c] = keep_per_field.get(c, 0)

        cur_count: Dict[Optional[str], int] = {}
        for d in components:
            c = current.get(id(d))
            cur_count[c] = cur_count.get(c, 0) + 1

        # Surplus per field: how many drones could we safely remove?
        # A drone is "safely removable" if its field still keeps enough.
        # Fields not in protected_ids can donate all their drones (they'd get 0 anyway).

        # Collect all moves needed: (drone_id, target_field)
        needed_moves: List[Tuple[int, str]] = []
        for fid in protected_ids:
            for did in target[fid]:
                if did not in claimed:
                    needed_moves.append((did, fid))

        # Sort moves by: target field threat (descending), then by drone distance to target
        needed_moves.sort(key=lambda m: (
            -self._effective_threat(field_by_id[m[1]]),
            self._dist(next(d for d in components if id(d) == m[0]), field_by_id[m[1]])
        ))

        # Cap moves per step
        max_moves = max(1, int(total_drones * self.MAX_MOVES_PER_STEP_FRACTION))
        applied = 0

        for did, fid in needed_moves:
            if applied >= max_moves:
                # Can't move this drone yet; keep it where it is
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = fid  # must go somewhere
                claimed.add(did)
                continue

            # Find donor: this drone is currently on some field.
            # Check if pulling it would underprotect the source.
            source = current.get(did)
            source_surplus = cur_count.get(source, 0) - keep_per_field.get(source, 0)

            if source and source in protected_ids and source_surplus <= 0:
                # Source field is tight. Check if we can find an alternative
                # drone for this slot that doesn't come from a tight field.
                # For simplicity, place on target but check overall validity.
                # Actually: still move but mark it - the target field needs it more.
                # The source will be temporarily under-defended for 1-2 steps.
                # This is better than leaving a high-threat field at 0.
                pass

            final[did] = fid
            claimed.add(did)
            applied += 1

        # Any drone not in final (shouldn't happen with caps) → current or top
        for d in components:
            did = id(d)
            if did not in final:
                cur = current.get(did)
                if cur and cur in field_by_id:
                    final[did] = cur
                else:
                    final[did] = protected_ids[0] if protected_ids else str(active[0].id)

        # --- Push to environment ---
        for d in components:
            fid = final.get(id(d))
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")