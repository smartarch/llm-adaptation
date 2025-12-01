from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        """
        Improved strategy:
        - Compute fields with threat_level > 0 and sort by threat desc (tie-break by id).
        - Count current protectors and lock drones that are already protecting fields that are initially fully protected.
        - Greedily allocate drones to fields in descending threat order until each is fully protected or we run out of drones.
          * Selection prefers drones already protecting or already moving_to_field toward that field.
          * Uses distance to the nearest point of the field rectangle (distance 0 if inside) to prioritize closer drones.
        - Assign locked/allocated drones to their protecting groups; others go to "idle".
        """
        # Helper: distance squared from point (x,y) to rectangle field
        def dist2_to_rect(x, y, field):
            # Rectangle: left, top, right, bottom (assume axis-aligned)
            # If inside rect horizontally and vertically, dist = 0
            dx = 0.0
            if x < field.left:
                dx = field.left - x
            elif x > field.right:
                dx = x - field.right
            dy = 0.0
            if y < field.top:
                dy = field.top - y
            elif y > field.bottom:
                dy = y - field.bottom
            return dx * dx + dy * dy

        # Build list of threatened fields (threat_level > 0)
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        if not threatened_fields:
            # Nothing to protect -> idle all
            for comp in components:
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(comp, grp)
            return

        # Map fields by id
        field_by_id = {f.id: f for f in threatened_fields}

        # Count current protecting drones per threatened field and list them
        protecting_counts = {f.id: 0 for f in threatened_fields}
        protecting_drones = {f.id: [] for f in threatened_fields}
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) in protecting_drones:
                tid = d.target_id
                protecting_counts[tid] += 1
                protecting_drones[tid].append(d)

        # Determine fields that are initially fully protected and lock those drones
        fully_protected_initial = {
            fid for fid, cnt in protecting_counts.items()
            if cnt >= field_by_id[fid].drones_for_full_protection
        }
        locked_drone_ids = set()
        # assigned_to_field will keep track of drones we've committed to each field (start with current protectors)
        assigned_to_field = {f.id: list(protecting_drones.get(f.id, [])) for f in threatened_fields}
        for fid in fully_protected_initial:
            for d in protecting_drones.get(fid, []):
                locked_drone_ids.add(id(d))

        # Candidate pool: drones not locked initially
        # We'll maintain available_drones as list that we remove from as we allocate them
        available_drones = [d for d in components if id(d) not in locked_drone_ids]

        # Sort fields in descending threat_level, tie-break by id
        def field_sort_key(f):
            return (-f.threat_level, f.id)
        sorted_fields = sorted(threatened_fields, key=field_sort_key)

        # For deterministic behavior, sort available_drones by id as secondary criterion where needed
        # (we will sort them per-field by a custom key)
        # Greedy allocation over fields
        for field in sorted_fields:
            fid = field.id
            required = int(field.drones_for_full_protection)
            currently_assigned = len(assigned_to_field.get(fid, []))
            need = max(0, required - currently_assigned)
            if need == 0:
                # Field is already fully protected (either initially or by assigned protectors)
                # Lock its assigned drones (so we don't reassign them later)
                for d in assigned_to_field.get(fid, []):
                    locked_drone_ids.add(id(d))
                    # Also ensure removed from available if present
                    available_drones = [ad for ad in available_drones if id(ad) != id(d)]
                continue

            if not available_drones:
                # No drones left to allocate
                continue

            # For each available drone compute priority key:
            # - prefer drones already protecting this field (shouldn't be available but keep general)
            # - prefer drones moving_to_field with target==this field
            # - prefer drones with smaller distance^2 to rectangle
            def drone_key(d):
                # already_protecting_flag: 0 if protecting this field, 1 otherwise
                already_protecting_flag = 0 if (getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == fid) else 1
                # moving_to_target_flag: 0 if moving_to_field and target_id == fid, 1 otherwise
                moving_to_flag = 0 if (getattr(d, "state", None) == "moving_to_field" and getattr(d, "target_id", None) == fid) else 1
                loc = getattr(d, "location", None)
                if loc is None:
                    dist2 = float("inf")
                else:
                    dist2 = dist2_to_rect(getattr(loc, "x", 0), getattr(loc, "y", 0), field)
                # final key: prioritize existing protector, then movers-to-target, then distance, then id for determinism
                return (already_protecting_flag, moving_to_flag, dist2, id(d))

            # Sort available_drones by drone_key and pick the first 'need' drones
            available_drones.sort(key=drone_key)
            selected = available_drones[:need]
            # Assign them to this field
            for d in selected:
                assigned_to_field.setdefault(fid, []).append(d)
                locked_drone_ids.add(id(d))
            # Remove selected from available_drones
            selected_ids = {id(d) for d in selected}
            available_drones = [d for d in available_drones if id(d) not in selected_ids]

        # Now finalize assignments: for every drone, determine group
        # Build reverse mapping drone_id -> assigned field id (if any)
        drone_assignment = {}
        for fid, dlist in assigned_to_field.items():
            for d in dlist:
                drone_assignment[id(d)] = fid

        for d in components:
            did = id(d)
            if did in drone_assignment:
                fid = drone_assignment[did]
                group_name = f"protecting {fid}"
                if group_name in group_ids:
                    environment.assign_group(d, group_name)
                else:
                    # Fallback to idle if protecting group doesn't exist
                    env_group = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                    environment.assign_group(d, env_group)
            else:
                # Not assigned to any protected field -> idle
                grp = "idle" if "idle" in group_ids else (group_ids[0] if group_ids else "idle")
                environment.assign_group(d, grp)