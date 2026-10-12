from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _dist_to_field_center(self, component, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        dx = getattr(component.location, "x", 0) - cx
        dy = getattr(component.location, "y", 0) - cy
        return math.hypot(dx, dy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Prepare group names
        idle_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")

        # Build list of candidate fields (threat > 0 and have a protecting group)
        candidate_fields = []
        for f in environment.fields:
            try:
                threat = getattr(f, "threat_level", 0)
                req = int(getattr(f, "drones_for_full_protection", 0))
            except Exception:
                continue
            group_name = f"protecting {f.id}"
            if threat > 0 and req > 0 and group_name in group_ids:
                # priority = threat per required drone
                priority = threat / max(1, req)
                candidate_fields.append((f, req, priority))

        # If no candidate fields, set all drones idle
        if not candidate_fields:
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # Sort fields by priority desc, then by threat desc
        candidate_fields.sort(key=lambda x: (x[2], getattr(x[0], "threat_level", 0)), reverse=True)

        # Precompute component attributes and categorize initial states
        comp_by_id = {}
        for c in components:
            comp_by_id[id(c)] = c

        # Helper: build lists for each field for quick selection
        # Also build global pools for remaining selection
        # We'll maintain a set of assigned component ids
        assigned = set()
        # Keep track of final assignment mapping comp_id -> group_name
        final_assignment = {}

        # For fast lookups: lists of components per state
        comps_by_state = {
            "protecting": [],
            "moving_to_field": [],
            "idle": []
        }
        for c in components:
            state = getattr(c, "state", None)
            comps_by_state.setdefault(state, []).append(c)

        # Helper to get components currently protecting a specific field
        def protecting_list_for(field):
            lst = []
            for c in comps_by_state.get("protecting", []):
                if getattr(c, "target_id", None) == field.id:
                    lst.append(c)
            return lst

        # Helper to get components moving to that field
        def moving_list_for(field):
            lst = []
            for c in comps_by_state.get("moving_to_field", []):
                if getattr(c, "target_id", None) == field.id:
                    lst.append(c)
            return lst

        # For each candidate field in priority order, try to fully protect it
        for field, required, _priority in candidate_fields:
            group_name = f"protecting {field.id}"
            # Build lists of available candidates for this field (not already assigned elsewhere)
            protecting_here = [c for c in protecting_list_for(field) if id(c) not in assigned]
            if len(protecting_here) >= required:
                # Keep these protecting drones assigned to this field
                for c in protecting_here:
                    assigned.add(id(c))
                    final_assignment[id(c)] = group_name
                # We intentionally keep them; extras beyond 'required' stay (they were protecting)
                continue

            # Need additional drones
            need = required - len(protecting_here)

            # Mark existing protecting_here as selected
            for c in protecting_here:
                assigned.add(id(c))
                final_assignment[id(c)] = group_name

            # Candidate pools in order of preference
            pools = []

            # 1) drones moving to this field
            moving_here = [c for c in moving_list_for(field) if id(c) not in assigned]
            pools.append(moving_here)

            # 2) idle drones
            idle_candidates = [c for c in comps_by_state.get("idle", []) if id(c) not in assigned]
            pools.append(idle_candidates)

            # 3) drones moving to other fields
            moving_others = [c for c in comps_by_state.get("moving_to_field", []) if id(c) not in assigned and getattr(c, "target_id", None) != field.id]
            pools.append(moving_others)

            # 4) drones protecting other fields
            protecting_others = [c for c in comps_by_state.get("protecting", []) if id(c) not in assigned and getattr(c, "target_id", None) != field.id]
            pools.append(protecting_others)

            # 5) any remaining (fallback)
            others = [c for c in components if id(c) not in assigned]
            pools.append(others)

            # Iterate pools and pick closest drones until need satisfied or no drones left
            for pool in pools:
                if need <= 0:
                    break
                # sort pool by distance to field center
                pool_sorted = sorted(pool, key=lambda c: self._dist_to_field_center(c, field))
                for c in pool_sorted:
                    if need <= 0:
                        break
                    cid = id(c)
                    if cid in assigned:
                        continue
                    assigned.add(cid)
                    final_assignment[cid] = group_name
                    need -= 1
                # continue to next pool if still need

            # If after all pools we still couldn't meet required, we've used all drones we could; move to next field
            # (partial protection is allowed but less effective - this greedy approach still attempts best allocation)

        # After processing fields, assign all remaining drones to idle
        for c in components:
            cid = id(c)
            if cid in final_assignment:
                # assign to the decided protecting group
                environment.assign_group(c, final_assignment[cid])
            else:
                environment.assign_group(c, idle_group)