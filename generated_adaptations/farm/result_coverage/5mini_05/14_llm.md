Reasoning and adaptation strategy

What I change and why

- Keep the hard rule: always fully protect the single highest-threat field first.
- Be conservative about stealing drones that are already protecting other fields: prefer idle drones and moving_to_field drones before ever taking protecting drones. Only take protecting drones if they are "extras" (a field has more protectors than required) and only if absolutely necessary to secure the top field.
- After the top field is secured, greedily fully protect additional fields in order of value-per-drone = threat_level / drones_for_full_protection, using only unassigned idle and moving drones. Do not steal protecting drones at this stage (except previously taken for the top field).
- Any leftover drones remain idle. Every drone is explicitly assigned every step.
- Deterministic tie-breaking is used (coordinates and ids) so behavior is stable.

This simpler, conservative policy reduces disruptive reassignments that previously increased damage while still allocating resources where they give best marginal benefit.

```py
from typing import List, Dict
import math

from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids: List[str], step: int):
        """
        Conservative allocation:
        - Fully protect the highest-threat field first, using:
          (committed to top) -> idle nearest -> moving_to_field nearest -> protecting-extras nearest ->
          (last resort) protecting from lowest-threat fields.
        - Then try to fully protect other fields by value-per-drone (threat / required),
          using only available idle and moving drones (do not steal protecting drones).
        - Assign remaining drones to 'idle'.
        - Explicitly call environment.assign_group for every drone.
        """

        def center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def euclid(ax, ay, bx, by):
            return math.hypot(ax - bx, ay - by)

        # Validate idle group fallback
        idle_group = "idle"
        fallback_group = idle_group if idle_group in group_ids else (group_ids[0] if group_ids else idle_group)

        # Threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened:
            for comp in components:
                environment.assign_group(comp, fallback_group)
            return

        # Precompute centers and basic info
        centers = {f.id: center(f) for f in threatened}
        fields_by_id = {f.id: f for f in threatened}

        # Partition drones by state/target
        protecting_by_field: Dict[str, List] = {}
        moving_by_field: Dict[str, List] = {}
        idle_drones: List = []
        all_comps = list(components)

        for comp in all_comps:
            st = getattr(comp, "state", "")
            tid = getattr(comp, "target_id", None)
            if st == "protecting" and tid is not None:
                protecting_by_field.setdefault(tid, []).append(comp)
            elif st == "moving_to_field" and tid is not None:
                moving_by_field.setdefault(tid, []).append(comp)
            else:
                idle_drones.append(comp)

        # Helper: distance from drone to field center
        def dist_to_field(drone, fid):
            cx, cy = centers[fid]
            return euclid(drone.location.x, drone.location.y, cx, cy)

        # Deterministic key for drones
        def drone_key(d):
            return (d.location.x, d.location.y, getattr(d, "state", ""), getattr(d, "target_id", "") or "")

        # Determine top field (highest threat, tie break by id)
        top_field = max(threatened, key=lambda f: (f.threat_level, getattr(f, "id", "")))
        top_id = top_field.id
        top_group = f"protecting {top_id}"
        if top_group not in group_ids:
            # cannot protect top; fallback everything to idle
            for comp in all_comps:
                environment.assign_group(comp, fallback_group)
            return
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))

        # --- Stage 1: select drones for top field using conservative priority ---

        selected_top = []
        selected_top_set = set()

        # (1) committed to top (protecting then moving), deterministic order
        committed_top = []
        committed_top.extend(sorted(protecting_by_field.get(top_id, []), key=drone_key))
        committed_top.extend(sorted(moving_by_field.get(top_id, []), key=drone_key))
        for d in committed_top:
            if len(selected_top) >= top_required:
                break
            selected_top.append(d)
            selected_top_set.add(d)

        # (2) idle nearest
        if len(selected_top) < top_required:
            idle_candidates = [d for d in idle_drones if d not in selected_top_set]
            idle_candidates.sort(key=lambda d: (dist_to_field(d, top_id), drone_key(d)))
            for d in idle_candidates:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (3) moving_to_field from other fields (closest)
        if len(selected_top) < top_required:
            movers = []
            for fid, movs in moving_by_field.items():
                if fid == top_id:
                    continue
                for d in movs:
                    if d not in selected_top_set:
                        movers.append(d)
            movers.sort(key=lambda d: (dist_to_field(d, top_id), drone_key(d)))
            for d in movers:
                if len(selected_top) >= top_required:
                    break
                selected_top.append(d)
                selected_top_set.add(d)

        # (4) protecting-extras (protectors beyond required) from other fields, prefer lowest-threat fields and closest
        if len(selected_top) < top_required:
            extra_protectors = []
            # build list of (field_threat, distance, drone) for extras
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                required = int(getattr(fields_by_id.get(fid, None), "drones_for_full_protection", 0))
                extra = max(0, len(prots) - required)
                if extra <= 0:
                    continue
                # sort protectors by closeness to top so we consider close ones first
                for d in sorted(prots, key=lambda d: (dist_to_field(d, top_id), drone_key(d))):
                    extra_protectors.append((getattr(fields_by_id[fid], "threat_level", 0), dist_to_field(d, top_id), fid, d))
            # sort extras by lowest field threat, then closest distance
            extra_protectors.sort(key=lambda t: (t[0], t[1], drone_key(t[3])))
            for _, _, _, d in extra_protectors:
                if len(selected_top) >= top_required:
                    break
                if d in selected_top_set:
                    continue
                selected_top.append(d)
                selected_top_set.add(d)

        # (5) last resort: steal protectors from lowest-threat fields (if still short)
        if len(selected_top) < top_required:
            protect_candidates = []
            for fid, prots in protecting_by_field.items():
                if fid == top_id:
                    continue
                field_threat = getattr(fields_by_id.get(fid, None), "threat_level", 0)
                for d in prots:
                    if d in selected_top_set:
                        continue
                    protect_candidates.append((field_threat, dist_to_field(d, top_id), fid, d))
            # sort by lowest threat, then closest
            protect_candidates.sort(key=lambda t: (t[0], t[1], drone_key(t[3])))
            for _, _, _, d in protect_candidates:
                if len(selected_top) >= top_required:
                    break
                if d in selected_top_set:
                    continue
                selected_top.append(d)
                selected_top_set.add(d)

        # --- Stage 2: prepare initial drone->group mapping (default idle) and mark stolen protectors as moved ---
        drone_to_group: Dict[object, str] = {}
        for comp in all_comps:
            drone_to_group[comp] = fallback_group

        # Assign protecting drones to their own field groups (unless they were stolen for top)
        for fid, prots in protecting_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in prots:
                if d in selected_top_set:
                    # stolen; will be assigned to top later
                    continue
                drone_to_group[d] = grp

        # Assign moving_to_field drones to their target groups (unless stolen)
        for fid, movs in moving_by_field.items():
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            for d in movs:
                if d in selected_top_set:
                    continue
                # only set if not already set by protecting above
                if drone_to_group.get(d, fallback_group) == fallback_group:
                    drone_to_group[d] = grp

        # Assign selected_top to top_group
        for d in selected_top:
            drone_to_group[d] = top_group

        # Build assigned set after top selection
        assigned_set = set(d for d, g in drone_to_group.items() if g != fallback_group)

        # --- Stage 3: try to fully protect other fields using only available idle/moving drones ---
        # Available drones pool: those not assigned (idle or moving) - do not include remaining protecting drones (we kept them where they were)
        available = [d for d in all_comps if d not in assigned_set]
        # We'll not steal protecting drones at this stage

        # Candidate fields sorted by value-per-drone = threat / required (descending)
        other_fields = [f for f in threatened if f.id != top_id]
        def value_per_drone(f):
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req <= 0:
                return 0.0
            return getattr(f, "threat_level", 0) / req
        other_fields.sort(key=lambda f: (value_per_drone(f), f.threat_level, getattr(f, "id", "")), reverse=True)

        for f in other_fields:
            fid = f.id
            grp = f"protecting {fid}"
            if grp not in group_ids:
                continue
            required = int(getattr(f, "drones_for_full_protection", 0))
            # Count already committed (protecting or moving) that we left in place
            committed = []
            # protecting assigned to this field (we set those earlier)
            for d in protecting_by_field.get(fid, []):
                if drone_to_group.get(d) == grp:
                    committed.append(d)
            # moving that we left in place
            for d in moving_by_field.get(fid, []):
                if drone_to_group.get(d) == grp:
                    committed.append(d)
            # how many still needed
            needed = max(0, required - len(committed))
            if needed <= 0:
                continue
            # fill from available, closest first
            if available:
                available.sort(key=lambda d: (dist_to_field(d, fid), drone_key(d)))
                chosen = []
                for d in list(available):
                    if len(chosen) >= needed:
                        break
                    chosen.append(d)
                for d in chosen:
                    drone_to_group[d] = grp
                    if d in available:
                        available.remove(d)

        # --- Stage 4: final assignment, all drones already given group in drone_to_group (idle if not assigned) ---
        for comp in all_comps:
            grp = drone_to_group.get(comp, fallback_group)
            environment.assign_group(comp, grp)