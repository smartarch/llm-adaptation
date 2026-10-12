from typing import List
import math

# Import the base class to derive from
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_drones(self, components: List, environment, group_ids: List[str], step: int):
        """
        Assign drones into groups to protect fields.
        Strategy:
        - Fully protect as many high-threat fields as possible (greedy by threat level).
        - Use closest available drones to fill each field's full_protection requirement.
        - After trying to fully protect, if any drones remain, allocate them to the highest-threat field
          that is still not fully protected to provide partial protection.
        - Drones already protecting a field are preserved in place if that field becomes full.
        - All remaining drones are set to idle.
        """

        # Helper to get the center of a field
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        # Helper to distance from a drone to a field center
        def dist_to_field(drone, field):
            cx, cy = field_center(field)
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            return math.hypot(getattr(loc, "x", 0.0) - cx, getattr(loc, "y", 0.0) - cy)

        # Gather fields with positive threat level
        fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]

        # If there are no threatened fields, idle all drones
        if not fields:
            for c in components:
                environment.assign_group(c, "idle")
            return

        # Map fields by id for quick lookup
        field_by_id = {f.id: f for f in fields}

        # Current protection counts per field
        current_by_field = {fid: 0 for fid in field_by_id}
        for c in components:
            if getattr(c, "state", "") == "protecting":
                tid = getattr(c, "target_id", None)
                if tid in current_by_field:
                    current_by_field[tid] += 1

        # Determine how many drones each field still needs to reach full protection
        needs_by_field = {}
        for fid, f in field_by_id.items():
            full = int(getattr(f, "drones_for_full_protection", 0))
            needs_by_field[fid] = max(0, full - current_by_field.get(fid, 0))

        # Build movable pool:
        #  - surplus drones from fields (current > full_protection)
        #  - idle drones (not currently protecting any field)
        movable = []
        movable_set = set()

        # Collect surplus drones (from fields where current > full)
        for f in fields:
            fid = f.id
            full = int(getattr(f, "drones_for_full_protection", 0))
            cur = current_by_field.get(fid, 0)
            surplus = max(0, cur - max(0, full))
            if surplus > 0:
                # Drones protecting this field
                protecting = [d for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid]
                cx, cy = field_center(f)
                protecting.sort(key=lambda d: math.hypot(getattr(d.location, "x", 0.0) - cx, getattr(d.location, "y", 0.0) - cy), reverse=True)
                to_move = min(surplus, len(protecting))
                for i in range(to_move):
                    d = protecting[i]
                    if d not in movable_set:
                        movable.append(d)
                        movable_set.add(d)

        # Idle drones (not currently protecting any field)
        for d in components:
            if getattr(d, "state", "") != "protecting" or getattr(d, "target_id", None) is None:
                if d not in movable_set:
                    movable.append(d)
                    movable_set.add(d)

        # Step 1: Greedily fill full protections for fields by threat order
        fields_sorted = sorted(fields, key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        assigned = set()

        for f in fields_sorted:
            fid = f.id
            cur = current_by_field.get(fid, 0)
            full = int(getattr(f, "drones_for_full_protection", 0))
            need = max(0, full - cur)
            if need <= 0:
                # Ensure currently protecting drones stay in their group
                for d in components:
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, f"protecting {fid}")
                        assigned.add(d)
                continue

            if need > 0 and movable:
                cx, cy = field_center(f)
                # Sort movable by distance to this field (closest first)
                movable.sort(key=lambda d: math.hypot(getattr(d.location, "x", 0.0) - cx, getattr(d.location, "y", 0.0) - cy))
                # Move closest drones until full is reached or no movable drones left
                i = 0
                while need > 0 and i < len(movable):
                    d = movable[i]
                    environment.assign_group(d, f"protecting {fid}")
                    assigned.add(d)
                    need -= 1
                    # Remove from movable
                    movable.pop(i)
                    # Do not increment i since we removed current
                    # current_by_field[fid] will be effectively updated in next evaluation
                # Update current_by_field to reflect moves
                cur = sum(1 for d in components if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid)
                current_by_field[fid] = cur

        # Step 2: After full protections, try a single partial protection on the highest not-full field if possible
        not_full = [f for f in fields_sorted if current_by_field.get(f.id, 0) < int(getattr(f, "drones_for_full_protection", 0))]
        if not_full and movable:
            top_field = not_full[0]
            fid = top_field.id
            cx, cy = field_center(top_field)
            movable.sort(key=lambda d: math.hypot(getattr(d.location, "x", 0.0) - cx, getattr(d.location, "y", 0.0) - cy))
            d = movable.pop(0)
            environment.assign_group(d, f"protecting {fid}")
            assigned.add(d)
            current_by_field[fid] = current_by_field.get(fid, 0) + 1

        # Step 3: Assign remaining drones to idle (or their current protecting group if still valid)
        for d in components:
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) in field_by_id:
                # Re-affirm their protecting group
                environment.assign_group(d, f"protecting {getattr(d, 'target_id', None)}")
            else:
                environment.assign_group(d, "idle")