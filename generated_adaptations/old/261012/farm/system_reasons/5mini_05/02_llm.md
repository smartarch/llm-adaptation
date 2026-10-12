Reasoning and strategy

We must always fully protect the single most-threatened field using the closest drones, avoid overprotecting fields, keep at least half of the drones assigned to protection most of the time, and avoid reassigning drones too often (stability). To achieve these goals with each call to assign_drones we:

1. Identify fields with threat_level > 0 and pick the primary (highest threat_level). If none, put all drones to "idle".

2. For the primary field:
   - Determine how many drones are required (drones_for_full_protection).
   - Prefer to keep drones that are already protecting that field (to satisfy stability).
   - Fill remaining slots with the closest drones, preferring those that are already en route to that field or idle (to minimize disruption).
   - Never assign more than the required number.

3. After the primary is fully protected, ensure at least half of the fleet is used for protection (if possible) by fully protecting additional fields in descending threat order. For each other field we:
   - Keep already-protecting drones for that field.
   - Add the closest available drones until the field is fully protected, but don't overprotect.

4. Assign any remaining drones to "idle".

5. Stability heuristic: the algorithm records the last assignment per drone (by Python id(component)) and increases a "staying" counter when the drone remains in the same group. When choosing drones to move, the algorithm favors those with lower staying counts and avoids removing drones that have been assigned to the same protecting group recently (this helps satisfy the "at least half should stay assigned at least 25% of the time" requirement as a heuristic).

6. Always use environment.assign_group(component, group_id) for each drone (every drone must be explicitly assigned each step).

The code implements these steps. It uses simple Euclidean distance to pick closest drones, ensures group names exist in group_ids, and keeps internal bookkeeping across calls (prev_assignments and stay_counters) to drive stability.

```py
from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from collections import defaultdict

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Track previous assignments keyed by id(component) -> group_id
        self.prev_assignments = {}
        # Track how many consecutive steps a component stayed in the same group
        self.stay_counters = defaultdict(int)
        # simple step when last seen to avoid stale counters (not strictly necessary)
        self.last_step_seen = {}

    def _field_center(self, field):
        return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

    def _dist(self, loc, center):
        dx = loc.x - center[0]
        dy = loc.y - center[1]
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare mapping and lists
        components = list(components)
        total_drones = len(components)
        min_protectors_target = math.ceil(total_drones / 2)  # at least half should be used for protection

        # Build list of fields with threat > 0
        fields_with_threat = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper to generate group name
        def protecting_group(field_id):
            return f"protecting {field_id}"

        # If no threatened fields, assign all to idle
        if not fields_with_threat:
            for c in components:
                # assign to idle only if group exists
                if "idle" in group_ids:
                    environment.assign_group(c, "idle")
                    cid = id(c)
                    prev = self.prev_assignments.get(cid)
                    if prev == "idle":
                        self.stay_counters[cid] += 1
                    else:
                        self.stay_counters[cid] = 1
                    self.prev_assignments[cid] = "idle"
                    self.last_step_seen[cid] = step
            return

        # Select primary field (highest threat; tie broken arbitrarily by ordering)
        primary_field = max(fields_with_threat, key=lambda f: f.threat_level)

        # Precompute distances to primary and centers for other fields
        primary_center = self._field_center(primary_field)
        field_centers = {f.id: self._field_center(f) for f in environment.fields}

        # For each component compute useful metadata
        comp_meta = {}
        for c in components:
            cid = id(c)
            dist_primary = self._dist(c.location, primary_center)
            prev_group = self.prev_assignments.get(cid)
            # Determine if currently protecting (from component state/target_id)
            currently_protecting = (getattr(c, "state", None) == "protecting")
            target_id = getattr(c, "target_id", None)
            comp_meta[cid] = {
                "comp": c,
                "dist_primary": dist_primary,
                "currently_protecting": currently_protecting,
                "target_id": target_id,
                "prev_group": prev_group,
                "stay": self.stay_counters.get(cid, 0)
            }

        # Build sets to hold assigned components for each field_id
        assigned_for_field = defaultdict(list)  # field_id -> list of component objects

        # 1) Ensure primary field is fully protected by closest drones, prefer keeping current protectors
        primary_required = int(getattr(primary_field, "drones_for_full_protection", 0))
        primary_group_name = protecting_group(primary_field.id)
        if primary_group_name not in group_ids:
            # fallback: if group not present, treat as idle (shouldn't happen per spec)
            primary_required = 0

        # Candidate ranking:
        #   priority tuple (priority_level, distance)
        # priority_level: lower is better
        # levels: 0 = currently protecting primary, 1 = prev assigned protecting primary, 2 = moving_to_primary (target_id==primary), 3 = idle, 4 = other protecting/moving, 5 = others
        def primary_priority(meta):
            # meta is comp_meta[cid]
            if meta["currently_protecting"] and meta["target_id"] == primary_field.id:
                level = 0
            elif meta["prev_group"] == primary_group_name:
                level = 1
            elif meta["target_id"] == primary_field.id:
                level = 2
            elif meta["comp"].state == "idle":
                level = 3
            elif meta["currently_protecting"]:
                level = 4
            else:
                level = 5
            # also prefer lower stay counters when moving someone (favor moving ones with low stay)
            # but we keep the primary prioritization first
            return (level, meta["stay"], meta["dist_primary"])

        # Sort components by this priority
        sorted_for_primary = sorted(comp_meta.values(), key=primary_priority)

        primary_selected = []
        for meta in sorted_for_primary:
            if len(primary_selected) >= primary_required:
                break
            # Choose the component
            primary_selected.append(meta["comp"])

        # Remove selected components from available pool
        selected_ids = set(id(c) for c in primary_selected)
        available_meta = {cid: m for cid, m in comp_meta.items() if cid not in selected_ids}

        # Record assignment
        if primary_required > 0:
            assigned_for_field[primary_field.id].extend(primary_selected)

        # 2) Protect additional fields until we reach at least half of drones protected (heuristic)
        # Sort other fields by threat desc (excluding primary)
        other_fields = sorted(
            [f for f in fields_with_threat if f.id != primary_field.id],
            key=lambda f: f.threat_level,
            reverse=True
        )

        current_protected_count = len(primary_selected)

        # First, keep any drones that are currently protecting other fields (we'll count them)
        # But we must not overprotect: keep up to required for each field
        for f in other_fields:
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req == 0:
                continue
            # Count existing protectors (from component state or prev assignment) for this field
            existing = []
            for meta in available_meta.values():
                if meta["currently_protecting"] and meta["target_id"] == f.id:
                    existing.append(meta)
                elif meta["prev_group"] == protecting_group(f.id):
                    # treat previous assignments as existing (less preferred than active protecting)
                    existing.append(meta)
            # sort existing by distance to that field to pick best to keep
            fc = field_centers.get(f.id, self._field_center(f))
            for m in existing:
                m["dist_field"] = self._dist(m["comp"].location, fc)
            existing_sorted = sorted(existing, key=lambda m: (m.get("dist_field", 0), m["stay"]))
            keep = []
            for m in existing_sorted:
                if len(keep) >= req:
                    break
                keep.append(m["comp"])
            if keep:
                # Add them
                assigned_for_field[f.id].extend(keep)
                # Remove from available_meta
                for c in keep:
                    available_meta.pop(id(c), None)
                current_protected_count += len(keep)

        # If we still need more protected drones to meet min_protectors_target, assign full protections to other fields by closeness
        for f in other_fields:
            if current_protected_count >= min_protectors_target:
                break
            req = int(getattr(f, "drones_for_full_protection", 0))
            if req == 0:
                continue
            already = len(assigned_for_field.get(f.id, []))
            need = max(0, req - already)
            if need == 0:
                continue
            # Build available candidates list sorted by distance to this field
            fc = field_centers.get(f.id, self._field_center(f))
            candidates = []
            for m in available_meta.values():
                mdist = self._dist(m["comp"].location, fc)
                # Lower priority for components with high stay counters (we prefer to move low-stay drones first)
                candidates.append( (m["stay"], mdist, m["comp"]) )
            candidates.sort(key=lambda x: (x[0], x[1]))  # prefer low stay then close
            pick = []
            for s, d, comp in candidates:
                if len(pick) >= need or current_protected_count >= min_protectors_target:
                    break
                pick.append(comp)
                # remove from available_meta
                available_meta.pop(id(comp), None)
                current_protected_count += 1
            if pick:
                assigned_for_field[f.id].extend(pick)

        # 3) Assign groups: for each drone that we decided to protect a field, assign protecting {field.id}
        # Avoid overprotecting: ensure per-field we don't exceed drones_for_full_protection
        final_assignments = {}  # cid -> group_name

        # Enforce per-field limits and prefer closest when trimming
        for fid, comps in list(assigned_for_field.items()):
            # Trim to field requirement if needed
            # find field object to get drones_for_full_protection (look up by id)
            fobj = next((f for f in environment.fields if f.id == fid), None)
            req = int(getattr(fobj, "drones_for_full_protection", 0)) if fobj else len(comps)
            if req < 0:
                req = 0
            if len(comps) > req:
                # sort comps by distance to field center and keep closest req
                fc = field_centers.get(fid, self._field_center(fobj) if fobj else (0,0))
                comps_sorted = sorted(comps, key=lambda c: self._dist(c.location, fc))
                comps = comps_sorted[:req]
                assigned_for_field[fid] = comps
            for c in comps:
                final_assignments[id(c)] = protecting_group(fid)

        # Remaining drones -> idle
        for c in components:
            cid = id(c)
            if cid not in final_assignments:
                # assign idle if available
                if "idle" in group_ids:
                    final_assignments[cid] = "idle"
                else:
                    # fallback: if idle not available, try to keep previous group or assign to primary if group exists
                    prev = self.prev_assignments.get(cid)
                    if prev in group_ids:
                        final_assignments[cid] = prev
                    elif primary_group_name in group_ids and len(assigned_for_field.get(primary_field.id, [])) < primary_required:
                        final_assignments[cid] = primary_group_name
                    else:
                        # arbitrary valid group (first in group_ids)
                        final_assignments[cid] = group_ids[0] if group_ids else "idle"

        # 4) Execute assignments and update internal tracking
        for c in components:
            cid = id(c)
            group = final_assignments.get(cid, "idle")
            # ensure group exists in group_ids; if not, fallback to idle or first group_id
            if group not in group_ids:
                if "idle" in group_ids:
                    group = "idle"
                elif group_ids:
                    group = group_ids[0]
                else:
                    group = "idle"
            environment.assign_group(c, group)

            prev = self.prev_assignments.get(cid)
            if prev == group:
                # stayed the same
                self.stay_counters[cid] = self.stay_counters.get(cid, 0) + 1
            else:
                self.stay_counters[cid] = 1
            self.prev_assignments[cid] = group
            self.last_step_seen[cid] = step
```