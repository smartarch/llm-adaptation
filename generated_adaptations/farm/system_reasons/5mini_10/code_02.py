import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persistent maps keyed by python id(component)
        self.prev_group = {}     # comp_id -> group_name
        self.stay_counts = defaultdict(int)  # comp_id -> consecutive steps staying in same group

    def _dist(self, comp_loc, cx, cy):
        dx = comp_loc.x - cx
        dy = comp_loc.y - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Helper to ensure group exists in provided group_ids
        def valid_group(name):
            return name in group_ids

        total_drones = len(components)
        if total_drones == 0:
            return  # nothing to assign

        # Index components for convenience
        comp_by_id = {id(c): c for c in components}

        # Threatened fields (only those with threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no fields threatened, idle everyone
        if not threatened_fields:
            for c in components:
                grp = "idle" if valid_group("idle") else (group_ids[0] if group_ids else "idle")
                environment.assign_group(c, grp)
                cid = id(c)
                # update persistence
                prev = self.prev_group.get(cid)
                if prev == grp:
                    self.stay_counts[cid] += 1
                else:
                    self.stay_counts[cid] = 1
                self.prev_group[cid] = grp
            return

        # Choose main field = highest threat_level, tie-breaker by how many drones already assigned there
        def already_assigned_count(field):
            name = f"protecting {field.id}"
            return sum(1 for cid, grp in self.prev_group.items() if grp == name)

        threatened_fields.sort(key=lambda f: (f.threat_level, already_assigned_count(f)), reverse=True)
        main_field = threatened_fields[0]

        # Helper: field center
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Precompute distances to main field
        main_cx, main_cy = field_center(main_field)

        # Prepare lists and maps
        comps = components[:]  # list copy
        # sort by distance to main field (ascending)
        comps_sorted_by_dist = sorted(comps, key=lambda c: self._dist(c.location, main_cx, main_cy))

        # Determine required drones to fully protect main field
        required_main = int(getattr(main_field, "drones_for_full_protection", 0))
        required_main = max(0, required_main)
        required_main = min(required_main, total_drones)

        target_main_group = f"protecting {main_field.id}"
        if not valid_group(target_main_group):
            # Defensive: if group not available, fallback idle for everyone
            for c in components:
                environment.assign_group(c, "idle" if valid_group("idle") else (group_ids[0] if group_ids else "idle"))
            return

        assignments = {}  # comp_id -> group

        # Step A: pick drones already assigned to main_field (stability)
        already_main = []
        for c in comps:
            cid = id(c)
            prev = self.prev_group.get(cid)
            # also consider state/target_id suggesting they are protecting main field
            if prev == target_main_group or (getattr(c, "state", None) == "protecting" and getattr(c, "target_id", None) == main_field.id):
                already_main.append(c)

        # Avoid duplicates and cap to required_main
        chosen_main = []
        seen = set()
        for c in already_main:
            if len(chosen_main) >= required_main:
                break
            cid = id(c)
            if cid not in seen:
                chosen_main.append(c)
                seen.add(cid)

        # Fill remaining slots from closest drones not yet chosen
        for c in comps_sorted_by_dist:
            if len(chosen_main) >= required_main:
                break
            cid = id(c)
            if cid in seen:
                continue
            chosen_main.append(c)
            seen.add(cid)

        # Mark chosen_main assigned to main group
        for c in chosen_main:
            assignments[id(c)] = target_main_group

        used_count = len(chosen_main)

        # Step B: attempt to fully protect additional fields in threat order using remaining drones
        remaining_comps = [c for c in comps if id(c) not in assignments]
        # For other fields sorted by threat descending (we already had threatened_fields sorted and used main_field)
        for field in threatened_fields[1:]:
            if not remaining_comps:
                break
            group_name = f"protecting {field.id}"
            if not valid_group(group_name):
                continue
            need = int(getattr(field, "drones_for_full_protection", 0))
            need = max(0, need)
            # Don't exceed available drones
            if need <= 0:
                continue
            if need > len(remaining_comps):
                # cannot fully protect this field, skip for now (we may use partial later if needed to reach half)
                continue
            # choose closest remaining_comps to this field
            cx, cy = field_center(field)
            remaining_comps.sort(key=lambda c: self._dist(c.location, cx, cy))
            chosen = remaining_comps[:need]
            for c in chosen:
                assignments[id(c)] = group_name
            # update remaining list
            remaining_comps = [c for c in remaining_comps if id(c) not in assignments]
            used_count += len(chosen)

        # Step C: Ensure at least half of the drones are used for protection.
        half_required = (total_drones + 1) // 2  # ceil(N/2)
        if used_count < half_required:
            # We will assign extra drones (closest available) to threatened fields (starting from highest threat)
            remaining_comps = [c for c in comps if id(c) not in assignments]
            # Build a list of candidate (comp, field) by closeness to fields (higher threat first)
            candidate_pairs = []
            for field in threatened_fields:
                group_name = f"protecting {field.id}"
                if not valid_group(group_name):
                    continue
                cx, cy = field_center(field)
                for c in remaining_comps:
                    candidate_pairs.append((field, c, self._dist(c.location, cx, cy)))
            # sort by (field.threat desc then distance asc) -> we already have threatened_fields in desc order,
            # so sort by threat descending and distance ascending
            candidate_pairs.sort(key=lambda x: (-x[0].threat_level, x[2]))
            # We'll pick pairs while respecting per-field max (drones_for_full_protection), but allow partial if needed
            field_assigned_counts = defaultdict(int)
            # Count existing assigned per field
            for cid, grp in assignments.items():
                if grp.startswith("protecting "):
                    fid = grp[len("protecting "):]
                    field_assigned_counts[fid] += 1
            # iterate candidate pairs and assign unique comps until used_count >= half_required
            assigned_comp_ids = set(assignments.keys())
            for field, c, _dist in candidate_pairs:
                if used_count >= half_required:
                    break
                cid = id(c)
                if cid in assigned_comp_ids:
                    continue
                group_name = f"protecting {field.id}"
                max_allowed = int(getattr(field, "drones_for_full_protection", 0))
                # allow assignment if it doesn't exceed max_allowed, but if we need to reach half and no other options, we may allow partial
                if field_assigned_counts[str(field.id)] >= max_allowed and max_allowed > 0:
                    # skip overprotected field
                    continue
                # assign
                assignments[cid] = group_name
                assigned_comp_ids.add(cid)
                field_assigned_counts[str(field.id)] += 1
                used_count += 1
            # If we still didn't reach half (e.g., no threatened fields left or all capped), assign remaining closest drones to idle->protect groups anyway:
            if used_count < half_required:
                remaining_comps = [c for c in comps if id(c) not in assignments]
                # assign them to any protecting group (choose main_field) until half reached
                for c in sorted(remaining_comps, key=lambda c: self._dist(c.location, main_cx, main_cy)):
                    if used_count >= half_required:
                        break
                    assignments[id(c)] = target_main_group
                    used_count += 1

        # Step D: All other drones -> idle
        for c in comps:
            cid = id(c)
            if cid not in assignments:
                # idle group fallback check
                grp = "idle" if valid_group("idle") else (group_ids[0] if group_ids else "idle")
                assignments[cid] = grp

        # Finally, call environment.assign_group for each component and update persisted state
        for c in comps:
            cid = id(c)
            grp = assignments[cid]
            # Safety: if grp not in group_ids, fallback to idle or first group
            if not valid_group(grp):
                grp = "idle" if valid_group("idle") else (group_ids[0] if group_ids else grp)
            environment.assign_group(c, grp)
            prev = self.prev_group.get(cid)
            if prev == grp:
                self.stay_counts[cid] += 1
            else:
                self.stay_counts[cid] = 1
            self.prev_group[cid] = grp