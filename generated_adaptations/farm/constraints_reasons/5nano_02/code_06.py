from generated_adaptations.base_classes.farm import FarmAdaptation
import math

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remember previous step's assignments to help persistence
        self.prev_assignments = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        n = len(components)
        fields = getattr(environment, 'fields', []) or []
        threat_fields = [f for f in fields if getattr(f, 'threat_level', 0) > 0]

        # If no threats, idle all drones
        if not threat_fields:
            for i, comp in enumerate(components):
                environment.assign_group(comp, 'idle')
                self.prev_assignments[i] = 'idle'
            return

        # Sort threat fields by threat level (desc)
        threat_fields.sort(key=lambda f: f.threat_level, reverse=True)
        top_field = threat_fields[0]
        top_group = f"protecting {top_field.id}"
        top_group_valid = top_group in group_ids

        # Center of the top field
        top_center = ((top_field.left + top_field.right) / 2.0,
                      (top_field.top + top_field.bottom) / 2.0)
        required = max(0, int(getattr(top_field, 'drones_for_full_protection', 0)))

        def dist_to_top(i):
            loc = getattr(components[i], 'location', None)
            if loc is None:
                return float('inf')
            return math.hypot(loc.x - top_center[0], loc.y - top_center[1])

        # Build list of drones already protecting top_field or en route to it
        candidates = []
        for i, comp in enumerate(components):
            prev = self.prev_assignments.get(i, None)
            if top_group_valid and prev == top_group:
                candidates.append((i, dist_to_top(i)))
            else:
                st = getattr(comp, 'state', None)
                tid = getattr(comp, 'target_id', None)
                if st in ('protecting','moving_to_field') and tid == top_field.id:
                    candidates.append((i, dist_to_top(i)))

        # Prefer closer drones
        candidates.sort(key=lambda t: t[1])
        to_protect = []
        max_keep = min(required, n)
        for idx, _ in candidates:
            if len(to_protect) >= max_keep:
                break
            to_protect.append(idx)

        # If not enough, fill with closest remaining drones
        if len(to_protect) < max_keep:
            remaining = [(i, dist_to_top(i)) for i in range(n) if i not in to_protect]
            remaining.sort(key=lambda t: t[1])
            for i, _ in remaining:
                if len(to_protect) >= max_keep:
                    break
                to_protect.append(i)

        # Assign initial
        assigned = ['idle'] * n
        for idx in to_protect:
            if top_group_valid:
                assigned[idx] = top_group
            else:
                assigned[idx] = 'idle'

        # Ensure at least half protected
        half_target = int(math.ceil(n/2.0))
        current_protected = len(to_protect)

        other_fields = threat_fields[1:]
        # Allocate to secondary fields to reach half_target
        for f in other_fields:
            if current_protected >= half_target:
                break
            group = f"protecting {f.id}"
            if group not in group_ids:
                continue
            fx = (f.left + f.right) / 2.0
            fy = (f.top + f.bottom) / 2.0

            pool = []
            for i in range(n):
                if assigned[i] != top_group:
                    loc = getattr(components[i], 'location', None)
                    d = float('inf')
                    if loc is not None:
                        d = math.hypot(loc.x - fx, loc.y - fy)
                    pool.append((i, d))
            pool.sort(key=lambda t: t[1])

            cap = max(0, int(getattr(f, 'drones_for_full_protection', 0)))
            slots = min(cap, len(pool))

            # First try to pick drones that previously protected this field
            used = set()
            if slots > 0:
                for i, _ in pool:
                    if slots <= 0:
                        break
                    if self.prev_assignments.get(i, '') == group:
                        assigned[i] = group
                        used.add(i)
                        current_protected += 1
                        slots -= 1

            # Fill remaining slots with closest available drones
            if slots > 0:
                for i, _ in pool:
                    if i in used:
                        continue
                    if assigned[i] != top_group:
                        assigned[i] = group
                        used.add(i)
                        current_protected += 1
                        slots -= 1
                        if slots == 0 or current_protected >= half_target:
                            break

        # If still below half_target, try to allocate more to secondary fields
        if current_protected < half_target:
            for f in other_fields:
                if current_protected >= half_target:
                    break
                group = f"protecting {f.id}"
                if group not in group_ids:
                    continue
                fx = (f.left + f.right) / 2.0
                fy = (f.top + f.bottom) / 2.0
                pool = []
                for i in range(n):
                    if assigned[i] != top_group:
                        loc = getattr(components[i], 'location', None)
                        d = float('inf')
                        if loc is not None:
                            d = math.hypot(loc.x - fx, loc.y - fy)
                        pool.append((i, d))
                pool.sort(key=lambda t: t[1])
                cap = max(0, int(getattr(f, 'drones_for_full_protection', 0)))
                slots = min(cap, len(pool))
                for i, _ in pool:
                    if slots <= 0:
                        break
                    if assigned[i] != group:
                        assigned[i] = group
                        current_protected += 1
                        slots -= 1
                        if current_protected >= half_target:
                            break

        # Any remaining unassigned go idle
        for i in range(n):
            if assigned[i] not in group_ids:
                assigned[i] = 'idle'

        # Apply assignments and persist them
        for i, comp in enumerate(components):
            grp = assigned[i]
            if grp not in group_ids:
                grp = 'idle'
            environment.assign_group(comp, grp)
            self.prev_assignments[i] = grp