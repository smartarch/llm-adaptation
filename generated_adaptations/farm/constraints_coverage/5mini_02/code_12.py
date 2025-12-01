from generated_adaptations.base_classes.farm import FarmAdaptation
import math
from math import ceil
from itertools import product

class SmartFarmAdaptation(FarmAdaptation):
    """
    Improved allocation that accounts for drone travel time and field area:
    - Always fully protects the highest-threat field using the closest drones (keep existing protectors).
    - Computes per-drone-per-field marginal score = (threat * area) / max(1, drones_needed) / (1 + travel_time).
    - Greedily assigns remaining drones to maximize those scores, preferring to fully protect other fields first,
      then allowing partial protection if drones remain.
    - Explicitly assigns every drone each step and validates group names.
    """
    DRONE_SPEED = 2.0  # units per time

    def assign_drones(self, components, environment, group_ids, step: int):
        def valid_group(name):
            return name if name in group_ids else "idle"

        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats => idle all
        if not threatened_fields:
            idle = valid_group("idle")
            for c in components:
                environment.assign_group(c, idle)
            return

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def distance(comp, field):
            cx, cy = field_center(field)
            dx = getattr(comp.location, "x", 0) - cx
            dy = getattr(comp.location, "y", 0) - cy
            return math.hypot(dx, dy)

        def travel_time(comp, field):
            return distance(comp, field) / self.DRONE_SPEED

        def field_area(field):
            return max(0.0, (field.right - field.left) * (field.bottom - field.top))

        # Build current protectors and movers by field id
        protecting_by_field = {}
        moving_by_field = {}
        for comp in components:
            state = getattr(comp, "state", "")
            target = getattr(comp, "target_id", None)
            if state == "protecting" and target is not None:
                protecting_by_field.setdefault(target, []).append(comp)
            if state == "moving_to_field" and target is not None:
                moving_by_field.setdefault(target, []).append(comp)

        # Choose top field by threat_level (must be fully protected)
        top_field = max(threatened_fields, key=lambda f: f.threat_level)

        # Precompute importance and score denominator for each field
        field_info = {}
        for f in threatened_fields:
            area = field_area(f)
            importance = getattr(f, "threat_level", 0.0) * area
            required = int(getattr(f, "drones_for_full_protection", 0))
            # treat non-positive required as 0 (no drones needed)
            field_info[f.id] = {
                "field": f,
                "importance": importance,
                "required": max(0, required)
            }

        # Selected assignment map and available drones set
        selected_assignment = {}  # comp -> field_id
        available = set(components)

        # Helper to assign chosen comps to a field and remove from available
        def assign_comps_to_field(comps_list, field_id):
            for c in comps_list:
                if c in available:
                    selected_assignment[c] = field_id
                    available.remove(c)

        # Fill a field to required with preference: current protectors -> movers -> nearest by travel_time
        def fill_field_to_required(field_obj, required):
            f = field_obj
            chosen = []
            # keep protectors
            for c in protecting_by_field.get(f.id, []):
                if c in available:
                    chosen.append(c)
            # add movers
            for c in moving_by_field.get(f.id, []):
                if c in available and c not in chosen:
                    chosen.append(c)
            # if still need, add nearest by travel_time
            if len(chosen) < required:
                need = required - len(chosen)
                candidates = [c for c in available if c not in chosen]
                candidates.sort(key=lambda c: travel_time(c, f))
                chosen.extend(candidates[:need])
            assign_comps_to_field(chosen, f.id)

        # Ensure top_field fully protected
        req_top = field_info[top_field.id]["required"]
        if req_top > 0:
            fill_field_to_required(top_field, req_top)

        # Build list of remaining fields (excluding top)
        other_fields = [f for f in threatened_fields if f.id != top_field.id]

        # Precompute per-drone-per-field scores for available drones (will update as available changes)
        def compute_score(comp, field_obj):
            info = field_info[field_obj.id]
            denom = max(1, info["required"])  # avoid division by zero; use 1 as minimum
            # travel_time adds penalty; add 1 to avoid zero divide and reduce importance of distant drones
            t = travel_time(comp, field_obj)
            score = (info["importance"] / denom) / (1.0 + t)
            return score

        # First pass: try to fully protect other fields by greedy matching maximizing score,
        # but not exceeding each field's required count.
        if available and other_fields:
            # Build all candidate triples (score, comp, field_id)
            triples = []
            for c, f in product(list(available), other_fields):
                s = compute_score(c, f)
                triples.append((s, c, f))
            # Sort descending by score
            triples.sort(key=lambda t: t[0], reverse=True)
            # Track assigned counts per field
            assigned_count = {f.id: len([c for c in selected_assignment if selected_assignment.get(c) == f.id]) for f in threatened_fields}
            # Greedily pick highest scoring pairs while respecting field required caps
            for s, comp, field_obj in triples:
                if comp not in available:
                    continue
                fid = field_obj.id
                cap = field_info[fid]["required"]
                # If field needed 0, skip
                if cap <= 0:
                    continue
                current = assigned_count.get(fid, 0)
                # If field already has at least cap assigned, skip (we don't over-assign in this pass)
                if current >= cap:
                    continue
                # Assign comp to this field
                selected_assignment[comp] = fid
                available.remove(comp)
                assigned_count[fid] = current + 1
                # stop early if no available drones
                if not available:
                    break

        # Second pass: if drones remain, allow partial protection (assign remaining drones to best remaining field for them)
        if available and threatened_fields:
            # For each remaining comp pick the field with highest per-comp score (no cap)
            for comp in list(available):
                best_field = None
                best_score = -1.0
                for f in threatened_fields:
                    s = compute_score(comp, f)
                    if s > best_score:
                        best_score = s
                        best_field = f
                if best_field and best_score > 0:
                    selected_assignment[comp] = best_field.id
                    available.remove(comp)
                else:
                    # No beneficial field found (score non-positive), leave comp for idle
                    pass

        # Prepare valid group names
        idle_group = valid_group("idle")
        protecting_group_cache = {f.id: valid_group(f"protecting {f.id}") for f in threatened_fields}

        # Assign groups for all components explicitly
        for comp in components:
            if comp in selected_assignment:
                field_id = selected_assignment[comp]
                gid = protecting_group_cache.get(field_id, idle_group)
                environment.assign_group(comp, gid)
            else:
                environment.assign_group(comp, idle_group)