from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    DRONE_SPEED = 2.0  # units per time; travel_time = distance / speed

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components, environment, group_ids, step: int):
        idle_group = "idle"
        available_groups = set(group_ids)

        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def euclid_dist(x1, y1, x2, y2):
            return math.hypot(x1 - x2, y1 - y2)

        def travel_time(drone_loc, field):
            cx, cy = field_center(field)
            return euclid_dist(drone_loc[0], drone_loc[1], cx, cy) / self.DRONE_SPEED

        def required_for(field):
            try:
                req = int(getattr(field, "drones_for_full_protection", 0))
            except Exception:
                req = 0
            return max(0, req)

        # Fields with positive threat
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threat_fields:
            # No threats: idle everyone
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        # Precompute drone locations
        drone_locs = {}
        for c in components:
            loc = getattr(c, "location", None)
            if loc is None:
                drone_locs[c] = (0.0, 0.0)
            else:
                drone_locs[c] = (getattr(loc, "x", 0.0), getattr(loc, "y", 0.0))

        # Sort fields by descending threat; top field must be fully protected
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_group = f"protecting {top_field.id}"
        if top_group not in available_groups:
            # Protecting group not available: fallback to idle everyone
            for comp in components:
                if idle_group in available_groups:
                    environment.assign_group(comp, idle_group)
            return

        assignment = {}
        remaining = set(components)

        # Step 1: Fully protect top field using closest drones (counting already-targeting)
        req_top = required_for(top_field)
        already_top = [c for c in components if getattr(c, "target_id", None) == top_field.id]
        selected_top = list(already_top)

        if len(selected_top) < req_top:
            # pick closest drones by travel time to top_field
            cx_top, cy_top = field_center(top_field)
            candidates = []
            for c in components:
                if c in selected_top:
                    continue
                x, y = drone_locs.get(c, (0.0, 0.0))
                t = euclid_dist(x, y, cx_top, cy_top) / self.DRONE_SPEED
                candidates.append((t, c))
            candidates.sort(key=lambda x: x[0])
            needed = req_top - len(selected_top)
            for i in range(min(needed, len(candidates))):
                selected_top.append(candidates[i][1])

        for c in selected_top:
            assignment[c] = top_group
            remaining.discard(c)

        # Step 2: Greedy selection of additional fields to fully protect by score = threat / time_cost
        field_candidates = []
        for field in threat_fields[1:]:
            group_name = f"protecting {field.id}"
            if group_name not in available_groups:
                continue
            req = required_for(field)
            if req <= 0:
                continue
            # drones already in remaining that target this field
            already = [c for c in remaining if getattr(c, "target_id", None) == field.id]
            additional_needed = max(0, req - len(already))
            if additional_needed == 0:
                # Already satisfiable with zero extra travel time
                field_candidates.append((float("inf"), field, req, already, 0.0))
                continue
            if additional_needed > len(remaining):
                # Not possible now
                continue
            # compute minimal travel-time cost using remaining drones (excluding already)
            times = []
            already_set = set(already)
            for c in remaining:
                if c in already_set:
                    continue
                t = travel_time(drone_locs[c], field)
                times.append(t)
            if len(times) < additional_needed:
                continue
            times.sort()
            time_cost = sum(times[:additional_needed])
            score = float(field.threat_level) / (time_cost + 1e-9)
            field_candidates.append((score, field, req, already, time_cost))

        # sort by score descending
        field_candidates.sort(key=lambda x: x[0], reverse=True)

        # allocate full protections greedily
        for score, field, req, already, time_cost in field_candidates:
            group_name = f"protecting {field.id}"
            # recompute already among remaining
            already_now = [c for c in remaining if getattr(c, "target_id", None) == field.id]
            additional_needed = max(0, req - len(already_now))
            if additional_needed == 0:
                # assign up to req of already_now
                for c in already_now[:req]:
                    assignment[c] = group_name
                    remaining.discard(c)
                continue
            if additional_needed > len(remaining):
                continue
            # choose closest additional_needed drones from remaining
            cx, cy = field_center(field)
            candidates = []
            already_set = set(already_now)
            for c in remaining:
                if c in already_set:
                    continue
                x, y = drone_locs.get(c, (0.0, 0.0))
                t = euclid_dist(x, y, cx, cy) / self.DRONE_SPEED
                candidates.append((t, c))
            candidates.sort(key=lambda x: x[0])
            chosen = [c for (_, c) in candidates[:additional_needed]]
            for c in already_now:
                if c in remaining:
                    assignment[c] = group_name
                    remaining.discard(c)
            for c in chosen:
                if c in remaining:
                    assignment[c] = group_name
                    remaining.discard(c)

        # Step 3: Use leftover drones for best marginal benefit partial assignments
        if remaining:
            partial_fields = [f for f in threat_fields if f.id != top_field.id and f"protecting {f.id}" in available_groups]
            if partial_fields:
                for c in list(remaining):
                    best_field = None
                    best_score = -1.0
                    loc = drone_locs.get(c, (0.0, 0.0))
                    for field in partial_fields:
                        t = travel_time(loc, field)
                        # heuristic: threat per (1 + travel time)
                        score = float(field.threat_level) / (1.0 + t)
                        if score > best_score:
                            best_score = score
                            best_field = field
                    if best_field is not None:
                        g = f"protecting {best_field.id}"
                        assignment[c] = g
                        remaining.discard(c)

        # Step 4: Any drones still unassigned -> idle (or fallback)
        for c in list(remaining):
            if idle_group in available_groups:
                assignment[c] = idle_group
            else:
                assignment[c] = top_group
            remaining.discard(c)

        # Final: explicitly assign every drone
        for comp in components:
            group = assignment.get(comp)
            if group is None:
                if idle_group in available_groups:
                    group = idle_group
                elif top_group in available_groups:
                    group = top_group
                elif group_ids:
                    group = group_ids[0]
                else:
                    group = idle_group
            environment.assign_group(comp, group)