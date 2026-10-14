import math
from typing import List, Dict, Set, Tuple, Optional

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):

    def _group_for_field(self, field, group_ids: List[str]) -> str:
        fid = str(field.id)
        # Direct & pattern matches
        candidates = [fid, f"protecting_{fid}", f"protect_{fid}", f"field_{fid}",
                      f"Protect_{fid}", f"field{id}"]
        for gid in group_ids:
            if gid in candidates:
                return gid
        # Substring match excluding idle
        for gid in group_ids:
            if gid == "idle":
                continue
            if fid in str(gid):
                return gid
        return "idle"

    @staticmethod
    def _center(field):
        return ((field.left + field.right) * 0.5,
                (field.top + field.bottom) * 0.5)

    def _dist(self, drone, field) -> float:
        cx, cy = self._center(field)
        return math.hypot(drone.location.x - cx, drone.location.y - cy)

    def _field_center_dist(self, f1, f2) -> float:
        c1 = self._center(f1); c2 = self._center(f2)
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

    def assign_drones(self, components, environment, group_ids, step: int):
        total_drones = len(components)
        if total_drones == 0:
            return

        active = [f for f in environment.fields if f.threat_level > 0]
        if not active:
            for d in components:
                environment.assign_group(d, "idle")
            return

        active.sort(key=lambda f: f.threat_level, reverse=True)
        field_by_id: Dict[str, object] = {str(f.id): f for f in active}
        field_id_set = set(field_by_id.keys())
        field_need: Dict[str, int] = {str(f.id): max(1, f.drones_for_full_protection)
                                       for f in active}

        # --- Read current target for each drone ---
        def parse_target(drone) -> Optional[str]:
            tgt = getattr(drone, 'target_id', None)
            if tgt is None:
                return None
            t = str(tgt)
            if t == "" or t.lower() == "idle":
                return None
            # Match against known field ids
            if t in field_id_set:
                return t
            # Try numeric suffix
            for fid in field_id_set:
                if fid == t or t.endswith(fid) or fid in t:
                    return fid
            return None

        current: Dict[int, Optional[str]] = {id(d): parse_target(d) for d in components}

        # --- Build target allocation greedily (highest threat first, closest drones) ---
        # Work with a pool of drones; each drone can be assigned once.
        pool: Set[int] = {id(d) for d in components}
        target_assign: Dict[str, List[int]] = {str(f.id): [] for f in active}

        # Concentration check: if we can't fully protect top field with ALL drones,
        # dump everything on top field(s) we CAN fully protect.
        cumulative_cost = 0
        protectable_count = 0
        for f in active:
            c = f.drones_for_full_protection
            if cumulative_cost + c <= total_drones:
                cumulative_cost += c
                protectable_count += 1
            else:
                break
        # If we can only protect 0 fields fully (even the top is too expensive),
        # still protect top with all drones (best effort).
        if protectable_count == 0:
            protectable_count = 1

        # Assign to first `protectable_count` fields (these will be FULLY protected).
        # Remaining drones (if any) go to the next fields as best-effort partial,
        # but prefer concentration on top fields per requirements.
        for idx, f in enumerate(active):
            fid = str(f.id)
            cap = f.drones_for_full_protection
            if idx >= protectable_count and idx > 0:
                cap = 0  # Don't assign to fields beyond our protection capacity
            if idx >= protectable_count and idx == 0:
                cap = total_drones  # Concentrate on top

            # Pull from pool, closest first
            avail = [d for d in components if id(d) in pool]
            avail.sort(key=lambda d: self._dist(d, f))
            for d in avail:
                if len(target_assign[fid]) >= cap:
                    break
                if id(d) in pool:
                    target_assign[fid].append(id(d))
                    pool.discard(id(d))

        # Surplus drones in pool go to top field as reserves (small overprotection OK)
        if pool and active:
            top_fid = str(active[0].id)
            for d in components:
                if id(d) in pool:
                    target_assign[top_fid].append(id(d))
                    pool.discard(id(d))

        # --- Compute current counts ---
        current_count: Dict[str, int] = {fid: 0 for fid in field_id_set}
        current_set: Dict[str, Set[int]] = {fid: set() for fid in field_id_set}
        for d in components:
            t = current.get(id(d))
            if t is not None and t in current_count:
                current_count[t] += 1
                current_set[t].add(id(d))

        # --- Apply target with stability: keep drone if it's already on a field
        #     where it's still wanted, otherwise move ---
        # Build "stayers": drones currently on field X and target also has them on X.
        new_assign: Dict[int, str] = {}
        need_slots: Dict[str, int] = {}

        for fid, drone_ids in target_assign.items():
            staying = [did for did in drone_ids
                       if current.get(did) == fid and did in current_set[fid]]
            # Cap staying by current presence (a drone currently "targeting" X but
            # not yet counted might not actually be there; trust parse_target)
            for did in staying:
                new_assign[did] = fid
            need_slots[fid] = len(drone_ids) - len(staying)

        # Build a global list of drones that need a new assignment
        to_place: List[int] = []
        placed_set = set(new_assign.keys())
        for fid, drone_ids in target_assign.items():
            for did in drone_ids:
                if did not in placed_set:
                    to_place.append(did)

        # Sort (drone, field-slot) pairs by proximity using greedy matching
        # Iterate fields in priority order (already sorted by threat);
        # for each field needing slots, pick closest available drone.
        drone_lookup: Dict[int, object] = {id(d): d for d in components}

        for f in active:
            fid = str(f.id)
            need = need_slots.get(fid, 0)
            if need <= 0:
                continue
            # Sort to_place by distance to this field
            to_place.sort(key=lambda did: self._dist(drone_lookup[did], f))
            for did in list(to_place):
                if need <= 0:
                    break
                if did in new_assign:
                    continue
                new_assign[did] = fid
                to_place.remove(did)
                need -= 1
            need_slots[fid] = need

        # Any still-unplaced drones → top field with remaining need, else top field
        for did in to_place:
            if did in new_assign:
                continue
            # Find field still needing
            placed = False
            for f in active:
                fid = str(f.id)
                if need_slots.get(fid, 0) > 0:
                    new_assign[did] = fid
                    need_slots[fid] -= 1
                    placed = True
                    break
            if not placed:
                new_assign[did] = str(active[0].id)

        # --- Final assignment to environment ---
        for d in components:
            did = id(d)
            fid = new_assign.get(did)
            if fid is not None and fid in field_by_id:
                environment.assign_group(d, self._group_for_field(field_by_id[fid], group_ids))
            else:
                environment.assign_group(d, "idle")