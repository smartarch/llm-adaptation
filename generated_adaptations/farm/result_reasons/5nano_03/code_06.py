import math

# Assume the base class FarmAdaptation is available from the given import path
# from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Memory: maps drone id to last assigned group
        self._prev_group_by_drone = {}

    def assign_drones(self, components, environment, group_ids, step: int):
        n = len(components)
        if n == 0:
            return

        # Helpers
        def field_center(field):
            return ((field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0)

        def dist_to_point(drone, x, y):
            loc = getattr(drone, "location", None)
            if not loc or not hasattr(loc, "x") or not hasattr(loc, "y"):
                return float("inf")
            return math.hypot(loc.x - x, loc.y - y)

        # Gather threatened fields
        threatened = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]

        # If no threats, idle all drones
        if not threatened:
            for d in components:
                grp = "idle"
                environment.assign_group(d, grp)
                self._prev_group_by_drone[id(d)] = grp
            return

        # Sort by threat (highest first)
        threatened.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)
        top_field = threatened[0]
        top_group = f"protecting {top_field.id}"
        top_required = int(getattr(top_field, "drones_for_full_protection", 0))
        can_protect_top = (top_group in group_ids) and top_required > 0

        top_center = field_center(top_field)

        # Final group map for this step
        final_group = {}  # index -> group_id

        # Current top protectors (based on current state)
        current_top = [
            i for i, d in enumerate(components)
            if getattr(d, "state", None) == "protecting" and getattr(d, "target_id", None) == top_field.id
        ]

        # Step 1: Ensure top field is fully protected with closest drones
        if can_protect_top and top_required > 0:
            # If too many protect, drop the farthest
            if len(current_top) > top_required:
                # Sort by distance to top center (farthest first)
                current_top.sort(key=lambda idx: dist_to_point(components[idx], top_center[0], top_center[1]), reverse=True)
                to_remove = current_top[top_required:]
                for idx in to_remove:
                    final_group[idx] = "idle"
                    self._prev_group_by_drone[id(components[idx])] = "idle"
                # Keep the remaining as top_group
                current_top = current_top[:top_required]

            # Assign remaining current top protectors to top_group
            for idx in current_top:
                final_group[idx] = top_group
                self._prev_group_by_drone[id(components[idx])] = top_group

            assigned_top = set(current_top)
        else:
            assigned_top = set()

        # Step 1b: Fill to reach top_required with closest drones not yet on top
        if can_protect_top and len(assigned_top) < top_required:
            need = top_required - len(assigned_top)
            pool = [i for i in range(n) if i not in assigned_top]
            pool.sort(key=lambda i: (
                self._prev_group_by_drone.get(id(components[i]), None) != top_group,
                dist_to_point(components[i], top_center[0], top_center[1])
            ))
            for idx in pool[:need]:
                final_group[idx] = top_group
                self._prev_group_by_drone[id(components[idx])] = top_group
                assigned_top.add(idx)

        # Step 2: Allocate remaining drones to secondary fields (in threat order)
        secondary_fields = threatened[1:]
        secondary_fields.sort(key=lambda f: getattr(f, "threat_level", 0), reverse=True)

        for f in secondary_fields:
            grp = f"protecting {f.id}"
            if grp not in group_ids:
                continue
            field_center_xy = field_center(f)

            # Current protectors for this field (based on final_group)
            current_for_field = [
                i for i in range(n)
                if final_group.get(i, None) == grp
            ]
            required = int(getattr(f, "drones_for_full_protection", 0))
            already = len(current_for_field)
            need = max(0, required - already)

            if need <= 0:
                # Ensure consistency
                for idx in current_for_field:
                    final_group[idx] = grp
                    self._prev_group_by_drone[id(components[idx])] = grp
                continue

            # Pool of drones not currently protecting this field
            pool = [i for i in range(n) if final_group.get(i, None) != grp]
            if not pool:
                continue

            pool.sort(key=lambda i: (
                self._prev_group_by_drone.get(id(components[i]), None) != grp,
                dist_to_point(components[i], field_center_xy[0], field_center_xy[1])
            ))
            for idx in pool[:need]:
                final_group[idx] = grp
                self._prev_group_by_drone[id(components[idx])] = grp

        # Step 3: Ensure at least half of drones are in protection when there are threats
        protecting_now = [i for i in range(n) if final_group.get(i, None) != "idle"]
        min_protect = math.ceil(n / 2.0)
        if len(protecting_now) < min_protect:
            # Build a pool of idle drones to assign
            idle_indices = [i for i in range(n) if final_group.get(i, None) == "idle"]
            # First try to fill top field if it has capacity
            if can_protect_top and top_required > 0:
                top_current = [i for i, g in final_group.items() if g == top_group]
                top_left = max(0, top_required - len(top_current))
                if top_left > 0 and idle_indices:
                    idle_indices.sort(key=lambda i: dist_to_point(components[i], top_center[0], top_center[1]))
                    for idx in idle_indices[:top_left]:
                        final_group[idx] = top_group
                        self._prev_group_by_drone[id(components[idx])] = top_group
                        protecting_now.append(idx)
                    idle_indices = idle_indices[top_left:]

            # If still not enough protection, allocate to secondary fields up to their capacity
            if len([i for i in range(n) if final_group.get(i, None) != "idle"]) < min_protect:
                for f in secondary_fields:
                    grp = f"protecting {f.id}"
                    if grp not in group_ids:
                        continue
                    field_center_xy = field_center(f)
                    current_for_field = [i for i in range(n) if final_group.get(i) == grp]
                    need = max(0, int(getattr(f, "drones_for_full_protection", 0)) - len(current_for_field))
                    if need <= 0:
                        continue
                    pool = [i for i in range(n) if final_group.get(i) != grp]
                    if not pool:
                        continue
                    pool.sort(key=lambda i: (
                        self._prev_group_by_drone.get(id(components[i]), None) != grp,
                        dist_to_point(components[i], field_center_xy[0], field_center_xy[1])
                    ))
                    for idx in pool[:need]:
                        final_group[idx] = grp
                        self._prev_group_by_drone[id(components[idx])] = grp
                        protecting_now.append(idx)
                        if len(protecting_now) >= min_protect:
                            break
                    if len(protecting_now) >= min_protect:
                        break

        # Step 4: Final pass - any drones not assigned yet get previous group if valid, else idle
        for i, d in enumerate(components):
            if i in final_group:
                grp = final_group[i]
                if grp not in group_ids:
                    grp = "idle"
                environment.assign_group(d, grp)
                self._prev_group_by_drone[id(d)] = grp
                continue

            last = self._prev_group_by_drone.get(id(d))
            if last in group_ids:
                environment.assign_group(d, last)
                self._prev_group_by_drone[id(d)] = last
            else:
                environment.assign_group(d, "idle")
                self._prev_group_by_drone[id(d)] = "idle"