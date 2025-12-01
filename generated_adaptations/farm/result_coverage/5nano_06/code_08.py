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
        - Identify all fields with threat_level > 0, sort by threat (desc).
        - Move only surplus drones (drones protecting a field beyond its full_protection) to help other fields.
        - Fully protect as many high-threat fields as possible using surplus drones first, then idle drones.
        - If drones remain after maximizing full protections, provide a single partial protection to the next-highest-threat field.
        - All remaining drones idle.
        """

        # Helpers
        def field_center(field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return cx, cy

        def dist_to_field_from_drone(drone, field):
            cx, cy = field_center(field)
            loc = getattr(drone, "location", None)
            if loc is None:
                return float("inf")
            dx = getattr(loc, "x", 0.0) - cx
            dy = getattr(loc, "y", 0.0) - cy
            return math.hypot(dx, dy)

        # Gather threatened fields
        threatened_fields = [f for f in environment.fields if getattr(f, "threat_level", 0.0) > 0.0]
        if not threatened_fields:
            for d in components:
                environment.assign_group(d, "idle")
            return

        # Sort fields by threat level (high to low)
        threatened_fields.sort(key=lambda f: getattr(f, "threat_level", 0.0), reverse=True)
        field_ids = {f.id for f in threatened_fields}

        # Current protection counts per field
        current_by_field = {fid: 0 for fid in field_ids}
        # Drones currently protecting per field
        drones_by_field = {fid: [] for fid in field_ids}
        for d in components:
            if getattr(d, "state", "") == "protecting":
                tid = getattr(d, "target_id", None)
                if tid in field_ids:
                    current_by_field[tid] += 1
                    drones_by_field[tid].append(d)

        # Full protection requirements per field
        full_by_field = {fid: int(getattr(next(f for f in threatened_fields if f.id == fid), "drones_for_full_protection", 0))
                         for fid in field_ids}

        # Build surplus drones: drones protecting a field beyond its full protection
        surplus_candidates = []  # list of (drone, source_field_id)
        for fid in field_ids:
            cur = current_by_field.get(fid, 0)
            full = full_by_field.get(fid, 0)
            surplus = max(0, cur - full)
            if surplus > 0:
                # Take the surplus drones from this field's current protecting list
                src_list = drones_by_field.get(fid, [])
                # Use the closest ones first (to minimize travel when later reassigning)
                # We'll sort by distance to that field's center (closer first)
                cx, cy = field_center(next(f for f in threatened_fields if f.id == fid))
                src_list.sort(key=lambda dd: math.hypot(getattr(dd.location, "x", 0.0) - cx,
                                                       getattr(dd.location, "y", 0.0) - cy))
                take = min(surplus, len(src_list))
                for i in range(take):
                    surplus_candidates.append((src_list[i], fid))
                # Note: we do not remove from current_by_field here; we'll update as we reassign below

        # Idle drones (not currently protecting any field)
        idle_drones = [d for d in components if getattr(d, "state", "") != "protecting"]

        # We'll maintain a set of drones already assigned in this pass
        assigned = set()

        # Step 1: Fully protect as many high-threat fields as possible using surplus first,
        # moving closest surplus drones to each field in threat order.
        for f in threatened_fields:
            fid = f.id
            cur = current_by_field.get(fid, 0)
            full = full_by_field.get(fid, 0)
            need = max(0, full - cur)
            if need == 0:
                # Ensure drones currently protecting this field stay in place
                for d in components:
                    if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                        environment.assign_group(d, f"protecting {fid}")
                        assigned.add(d)
                continue

            # Recalculate dynamic candidate pools for this target
            # Use surplus candidates first, then idle drones
            # Prepare a distance-sorted view of surplus to this field
            if surplus_candidates:
                # Sort by distance to this target
                cx, cy = field_center(f)
                surplus_candidates.sort(key=lambda pair: math.hypot(
                    getattr(pair[0].location, "x", 0.0) - cx,
                    getattr(pair[0].location, "y", 0.0) - cy
                ))
            # Consume from surplus first
            while need > 0 and surplus_candidates:
                drone, src_field = surplus_candidates.pop(0)
                environment.assign_group(drone, f"protecting {fid}")
                assigned.add(drone)
                # Update current_by_field counts
                current_by_field[src_field] -= 1
                current_by_field[fid] = current_by_field.get(fid, 0) + 1
                # Since this drone moved, it no longer counts as surplus
                need -= 1

            # If still need, use idle drones
            if need > 0 and idle_drones:
                # Sort idle drones by distance to this field
                cx, cy = field_center(f)
                idle_drones.sort(key=lambda dd: math.hypot(getattr(dd.location, "x", 0.0) - cx,
                                                             getattr(dd.location, "y", 0.0) - cy))
                while need > 0 and idle_drones:
                    drone = idle_drones.pop(0)
                    environment.assign_group(drone, f"protecting {fid}")
                    assigned.add(drone)
                    current_by_field[fid] = current_by_field.get(fid, 0) + 1
                    need -= 1

            # After attempts, ensure current protecting drones for this field are in the correct group
            for d in components:
                if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) == fid:
                    environment.assign_group(d, f"protecting {fid}")
                    assigned.add(d)

        # Step 2: If any field still not fully protected and we have any drones left,
        # provide a single level of partial protection to the highest-threat field not yet full.
        not_full_fields = [f for f in threatened_fields if current_by_field.get(f.id, 0) < full_by_field.get(f.id, 0)]
        if not_full_fields:
            top_field = not_full_fields[0]
            fid = top_field.id
            # Collect available drones (surplus candidates may be depleted; use idle_drones)
            # If still not enough, we can reuse any drone not currently protecting a different field
            if idle_drones:
                # Choose the closest idle drone
                cx, cy = field_center(top_field)
                idle_drones.sort(key=lambda dd: math.hypot(getattr(dd.location, "x", 0.0) - cx,
                                                            getattr(dd.location, "y", 0.0) - cy))
                if idle_drones:
                    drone = idle_drones.pop(0)
                    environment.assign_group(drone, f"protecting {fid}")
                    assigned.add(drone)
                    current_by_field[fid] = current_by_field.get(fid, 0) + 1

        # Step 3: Any drones not assigned should be idle
        for d in components:
            if d in assigned:
                continue
            # If drone is still protecting a field that exists, keep it in that group
            if getattr(d, "state", "") == "protecting" and getattr(d, "target_id", None) in field_ids:
                environment.assign_group(d, f"protecting {getattr(d, 'target_id', None)}")
            else:
                environment.assign_group(d, "idle")