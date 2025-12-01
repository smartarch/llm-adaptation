import math

# Assuming the base class can be imported as described
# from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Per-drone memory: last assigned group name
        self._prev_group_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        n = len(components)
        if n == 0:
            return

        # Helpers
        def center_field(f):
            return ((f.left + f.right) / 2.0, (f.top + f.bottom) / 2.0)

        def dist_to_point(drone, x, y):
            loc = getattr(drone, "location", None)
            if not loc or not hasattr(loc, "x") or not hasattr(loc, "y"):
                return float("inf")
            return math.hypot(loc.x - x, loc.y - y)

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones (preserve memory)
        if not threatened:
            for d in components:
                grp = "idle"
                if grp not in group_ids:
                    grp = "idle"
                environment.assign_group(d, grp)
                self._prev_group_by_drone[id(d)] = grp
            return

        # Sort fields by threat level (desc)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        can_protect_top = (top_group in group_ids) and top_required > 0

        top_center = center_field(top_field)

        final_group = {}  # index -> group_id

        # Current top protectors (based on current drone state)
        current_top = [
            i for i, d in enumerate(components)
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]

        # Step 1: If too many drones are protecting top, move farthest away first
        if can_protect_top and len(current_top) > top_required:
            # Sort by distance to top center (farthest first)
            current_top.sort(key=lambda idx: dist_to_point(components[idx], top_center[0], top_center[1]), reverse=True)
            to_remove = current_top[top_required:]
            for idx in to_remove:
                final_group[idx] = "idle"
                self._prev_group_by_drone[id(components[idx])] = "idle"

        # Step 2: Ensure remaining current_top drones are assigned to top_group
        for idx in current_top:
            if final_group.get(idx) != "idle":
                final_group[idx] = top_group
                self._prev_group_by_drone[id(components[idx])] = top_group

        # Step 2b: Fill to reach top_required with closest drones not already on top
        assigned_top = {idx for idx, g in final_group.items() if g == top_group}
        need_top = max(0, top_required - len(assigned_top))
        if can_protect_top and need_top > 0:
            pool = [i for i in range(n) if i not in assigned_top]
            pool.sort(key=lambda i: (
                self._prev_group_by_drone.get(id(components[i]), None) != top_group,
                dist_to_point(components[i], top_center[0], top_center[1])
            ))
            for idx in pool[:need_top]:
                final_group[idx] = top_group
                self._prev_group_by_drone[id(components[idx])] = top_group
                assigned_top.add(idx)

        # Step 3: Allocate remaining drones to secondary fields in threat order
        # Build list of secondary fields (excluding top_field)
        secondary_fields = [f for f in threatened if f.id != top_field.id]
        secondary_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for f in secondary_fields:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            # Current protectors for this field
            current = [
                i for i, d in enumerate(components)
                if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == f.id
            ]
            required = int(getattr(f, "drones_for_full_protection", 0))
            already = len([i for i in current if final_group.get(i) == grp])
            need = max(0, required - already)
            if need <= 0:
                for idx in current:
                    final_group[idx] = grp
                    self._prev_group_by_drone[id(components[idx])] = grp
                continue

            pool = [i for i in range(n) if i not in current]
            if not pool:
                continue

            cx, cy = center_field(f)
            pool.sort(key=lambda i: (
                self._prev_group_by_drone.get(id(components[i]), None) != grp,
                dist_to_point(components[i], cx, cy)
            ))
            for idx in pool[:need]:
                final_group[idx] = grp
                self._prev_group_by_drone[id(components[idx])] = grp

        # Step 4: Maintain some protection presence (at least half should be protecting when there are threats)
        protecting_now = [i for i in range(n) if final_group.get(i, None) != "idle"]
        if len(protecting_now) < math.ceil(n / 2):
            # First try to fill top field if it has capacity
            current_top_count = len([i for i in range(n) if final_group.get(i) == top_group])
            top_left = max(0, top_required - current_top_count)
            if top_left > 0 and can_protect_top:
                idle_indices = [i for i in range(n) if final_group.get(i) == "idle"]
                idle_indices.sort(key=lambda i: dist_to_point(components[i], top_center[0], top_center[1]))
                for idx in idle_indices[:top_left]:
                    final_group[idx] = top_group
                    self._prev_group_by_drone[id(components[idx])] = top_group
                    protecting_now.append(idx)

            # If still not enough, try to allocate to next threatened fields with remaining capacity
            if len([i for i in range(n) if final_group.get(i) != "idle"]) < math.ceil(n / 2):
                for f in secondary_fields:
                    grp = f"protecting {f.id}"
                    if grp not in group_ids:
                        continue
                    current = [i for i in range(n) if final_group.get(i) == grp]
                    need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(current))
                    if need <= 0:
                        continue
                    pool = [i for i in range(n) if final_group.get(i) != grp]
                    if not pool:
                        continue
                    cx, cy = center_field(f)
                    pool.sort(key=lambda i: (
                        self._prev_group_by_drone.get(id(components[i]), None) != grp,
                        dist_to_point(components[i], cx, cy)
                    ))
                    for idx in pool[:need]:
                        final_group[idx] = grp
                        self._prev_group_by_drone[id(components[idx])] = grp
                        if len([i for i in range(n) if final_group.get(i) != "idle"]) >= math.ceil(n / 2):
                            break

        # Step 5: Finalize assignments
        for i, d in enumerate(components):
            grp = final_group.get(i, "idle")
            if grp not in group_ids:
                grp = "idle"
            environment.assign_group(d, grp)
            self._prev_group_by_drone[id(d)] = grp