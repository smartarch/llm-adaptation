from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Persistent memory of last assigned group per drone (by id)
        self._last_assignment = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Collect fields with threat > 0
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute center of a field
        def center_of(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return (cx, cy)

        # Helper: check if a drone is currently protecting a given field (by memory/state)
        def is_protecting_field(d, field_id):
            d_id = id(d)
            last_grp = self._last_assignment.get(d_id, None)
            if last_grp == f"protecting {field_id}":
                return True
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field_id:
                return True
            return False

        # Helper: current protection count for a field
        def current_protect_count(field):
            count = 0
            for d in components:
                if is_protecting_field(d, field.id):
                    count += 1
            return count

        # Sort fields by threat level descending, then by id for determinism
        fields_sorted = sorted(
            fields,
            key=lambda f: (-getattr(f, "threat_level", 0), getattr(f, "id", "")),
        )

        # Prepare centers for distance calculations
        centers = {f.id: center_of(f) for f in fields_sorted}

        total_drones = len(components)
        step_assignment = {}

        if not fields_sorted:
            # No threats: all drones idle
            for d in components:
                step_assignment[id(d)] = "idle"
            for d in components:
                environment.assign_group(d, step_assignment[id(d)])
            self._last_assignment = step_assignment
            return

        # Step 1: Fully protect the top-threat field
        top = fields_sorted[0]
        current_top = current_protect_count(top)
        needed_top = max(0, getattr(top, "drones_for_full_protection", 0) - current_top)

        # Preserve any drone already protecting the top (memory/state)
        for d in components:
            if is_protecting_field(d, top.id):
                step_assignment[id(d)] = f"protecting {top.id}"

        if needed_top > 0:
            center_top = centers[top.id]
            candidates = []
            for d in components:
                if id(d) in step_assignment:
                    continue
                d_id = id(d)
                last_grp = self._last_assignment.get(d_id, None)
                priority = 0 if (last_grp == f"protecting {top.id}") or (
                    getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top.id
                ) else 1
                lx = getattr(d, "location").x
                ly = getattr(d, "location").y
                dist2 = (lx - center_top[0]) ** 2 + (ly - center_top[1]) ** 2
                candidates.append((priority, dist2, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            assigned = 0
            for _, _, d in candidates:
                if assigned >= needed_top:
                    break
                step_assignment[id(d)] = f"protecting {top.id}"
                assigned += 1

        # Step 2: Use remaining drones to protect other fields based on efficiency
        def protected_count(field):
            c = 0
            for d in components:
                did = id(d)
                if step_assignment.get(did, None) == f"protecting {field.id}":
                    c += 1
                elif is_protecting_field(d, field.id):
                    c += 1
            return c

        # Build a list of candidate fields (excluding the top) sorted by threat/drones_for_full_protection
        field_candidates = []
        for f in fields_sorted[1:]:
            if getattr(f, "drones_for_full_protection", 0) <= 0:
                continue
            current = protected_count(f)
            if current >= getattr(f, "drones_for_full_protection", 0):
                continue
            threat = getattr(f, "threat_level", 0)
            denom = max(1, getattr(f, "drones_for_full_protection", 1))
            ratio = threat / denom
            field_candidates.append((ratio, f))
        field_candidates.sort(key=lambda t: (-t[0], getattr(t[1], "id", "")))

        # Remaining unassigned drones
        unassigned = [d for d in components if id(d) not in step_assignment]

        for _, f in field_candidates:
            needed = max(0, getattr(f, "drones_for_full_protection", 0) - protected_count(f))
            if needed <= 0:
                continue
            center_f = centers[f.id]
            candidates = []
            for d in unassigned:
                d_id = id(d)
                last_grp = self._last_assignment.get(d_id, None)
                priority = 0 if (last_grp == f"protecting {f.id}") or (
                    getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
                ) else 1
                dx = getattr(d, "location").x
                dy = getattr(d, "location").y
                dist2 = (dx - center_f[0]) ** 2 + (dy - center_f[1]) ** 2
                candidates.append((priority, dist2, d))
            candidates.sort(key=lambda t: (t[0], t[1]))

            assigned = 0
            for _, _, d in candidates:
                if assigned >= needed:
                    break
                step_assignment[id(d)] = f"protecting {f.id}"
                assigned += 1
                unassigned.remove(d)

        # Step 3: Idle all remaining drones
        for d in components:
            if id(d) not in step_assignment:
                step_assignment[id(d)] = "idle"

        # Apply the assignments to the environment
        for d in components:
            environment.assign_group(d, step_assignment[id(d)])

        # Persist this step's assignments for the next step
        self._last_assignment = step_assignment