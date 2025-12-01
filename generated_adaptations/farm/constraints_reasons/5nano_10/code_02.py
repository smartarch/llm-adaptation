from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember last group assignment for each drone (keyed by id(component))
        self.prev_assignment_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        # Gather fields and identify those with threat > 0
        fields = list(getattr(environment, "fields", []))
        threat_fields = [f for f in fields if getattr(f, "threat_level", 0) > 0]

        # Helper to compute field center
        def center_of(field):
            left = getattr(field, "left", 0.0)
            right = getattr(field, "right", 0.0)
            top = getattr(field, "top", 0.0)
            bottom = getattr(field, "bottom", 0.0)
            return ((left + right) / 2.0, (top + bottom) / 2.0)

        # Helper to compute distance from drone to a point
        def dist(drone, pt):
            dx = drone.location.x - pt[0]
            dy = drone.location.y - pt[1]
            return (dx * dx + dy * dy) ** 0.5

        # If no fields or no threats, idle all drones
        if not threat_fields:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_assignment_by_drone[id(d)] = "idle"
            return

        # Choose top-threat field. Break ties by closeness of nearest drone to the field center.
        top_field = None
        top_threat = -1.0
        top_center = None
        for f in threat_fields:
            cx, cy = center_of(f)
            nearest = float("inf")
            for d in components:
                dpt = dist(d, (cx, cy))
                if dpt < nearest:
                    nearest = dpt
            threat = getattr(f, "threat_level", 0)
            # Prefer higher threat; if equal, prefer closer
            if (threat > top_threat) or (threat == top_threat and nearest < (top_center and dist(next(iter([c for c in components if getattr(c, "location", None) is not None]), (0,0))), (0,0)) if top_center else True):
                top_threat = threat
                top_field = f
                top_center = (cx, cy)

        # If none found, idle all
        if top_field is None:
            for d in components:
                environment.assign_group(d, "idle")
                self.prev_assignment_by_drone[id(d)] = "idle"
            return

        # Current protection on the top field
        current_protect = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protect += 1

        required = getattr(top_field, "drones_for_full_protection", 0)
        needed = max(0, int(required) - int(current_protect))

        top_center = center_of(top_field)

        # Build candidates to fill top_field: drones not currently protecting it
        candidates = []
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                continue
            ddist = dist(d, top_center)
            prev_group = self.prev_assignment_by_drone.get(id(d), None)
            # Prefer drones that previously protected this field
            prefer = 1 if prev_group == f"protecting {top_field.id}" else 0
            candidates.append((ddist, -prefer, d))
        candidates.sort(key=lambda t: (t[0], t[1]))

        # Assign top_field with closest drones, prioritizing continuity
        chosen_for_top = []
        for ddist, negpref, d in candidates:
            if len(chosen_for_top) >= needed:
                break
            chosen_for_top.append(d)

        for d in chosen_for_top:
            environment.assign_group(d, f"protecting {top_field.id}")
            self.prev_assignment_by_drone[id(d)] = f"protecting {top_field.id}"

        # Recompute current protection for top_field after assignments
        current_protect = 0
        for d in components:
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                current_protect += 1

        # If still not fully protected, try to fill with more drones (if available)
        if current_protect < required:
            remaining_needed = int(required) - int(current_protect)
            rem_candidates = []
            for d in components:
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id:
                    continue
                ddist = dist(d, top_center)
                prev_group = self.prev_assignment_by_drone.get(id(d), None)
                prefer = 1 if prev_group == f"protecting {top_field.id}" else 0
                rem_candidates.append((ddist, -prefer, d))
            rem_candidates.sort(key=lambda t: (t[0], t[1]))
            for dist_val, negpref, d in rem_candidates:
                if remaining_needed <= 0:
                    break
                environment.assign_group(d, f"protecting {top_field.id}")
                self.prev_assignment_by_drone[id(d)] = f"protecting {top_field.id}"
                remaining_needed -= 1

        # Now consider other threatened fields in descending threat order
        others = [f for f in threat_fields if f.id != top_field.id]
        others.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        # Drones already protecting top_field
        assigned_to_top_ids = {id(d) for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id}

        for field in others:
            center = center_of(field)
            current = sum(1 for d in components if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id)
            needed_field = max(0, int(getattr(field, "drones_for_full_protection", 0)) - int(current))
            if needed_field <= 0:
                continue

            candidates2 = []
            for d in components:
                if id(d) in assigned_to_top_ids:
                    # skip drones already on top_field; we will leave them there
                    continue
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == field.id:
                    continue
                ddist = dist(d, center)
                prev_group = self.prev_assignment_by_drone.get(id(d), None)
                prefer = 1 if prev_group == f"protecting {field.id}" else 0
                candidates2.append((ddist, -prefer, d))
            candidates2.sort(key=lambda t: (t[0], t[1]))

            for dist_val, negpref, d in candidates2:
                if needed_field <= 0:
                    break
                environment.assign_group(d, f"protecting {field.id}")
                self.prev_assignment_by_drone[id(d)] = f"protecting {field.id}"
                assigned_to_top_ids.add(id(d))
                needed_field -= 1

        # Finally, any drones not assigned to protecting something become idle
        for d in components:
            if getattr(d, "state", None) == "protecting":
                # It's already protecting something; keep it assigned
                self.prev_assignment_by_drone[id(d)] = f"protecting {getattr(d, 'target_id', None)}"
            else:
                environment.assign_group(d, "idle")
                self.prev_assignment_by_drone[id(d)] = "idle"