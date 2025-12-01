from typing import List, Dict, Optional, Tuple
import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    """
    Adaptation strategy for assigning drones to fields:
    - Always fully protect the most threatened field using the closest drones (with slight
      preference for drones already targeting that field).
    - Greedily fully protect other fields in descending threat order if enough drones available.
    - Ensure at least half of the drones are used for protection; if necessary, allocate
      additional drones (possibly resulting in partial protection) to reach that threshold.
    - Do not overprotect fields (never assign more than drones_for_full_protection).
    - Prefer to keep drones on their current target when reasonable to reduce churn.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _field_center(self, field):
        cx = (field.left + field.right) / 2.0
        cy = (field.top + field.bottom) / 2.0
        return cx, cy

    def _distance(self, loc, cx, cy):
        return math.hypot(loc.x - cx, loc.y - cy)

    def assign_drones(self, components, environment, group_ids, step: int):
        # Ensure "idle" is a valid group
        idle_group = "idle"
        if idle_group not in group_ids:
            # fallback: if "idle" isn't present, try to find a group that starts with "idle"
            idle_group = next((g for g in group_ids if g == "idle"), group_ids[0])

        # Build list of fields with threat > 0 sorted by descending threat_level
        threat_fields = [f for f in environment.fields if getattr(f, "threat_level", 0) > 0]
        threat_fields.sort(key=lambda f: (-f.threat_level, f.id))

        n_drones = len(components)
        min_protected = (n_drones + 1) // 2  # at least half (ceiling)

        # Helper: mapping component -> assigned field id (None means idle)
        assigned: Dict[object, Optional[str]] = {c: None for c in components}

        # Available pool of components to assign (list of components not yet assigned)
        available = set(components)

        # Precompute drone info
        drone_info = {}
        for c in components:
            # keep attributes in a small structure for repeated access
            drone_info[c] = {
                "state": getattr(c, "state", None),
                "target_id": getattr(c, "target_id", None),
                "loc": getattr(c, "location", None)
            }

        # Helper to select up to k drones for a field from the available set.
        # Preference order:
        # 1) already targeting this field (target_id == field.id), especially if state == 'protecting'
        # 2) closest by Euclidean distance to the field center
        def select_drones_for_field(field, k, allow_partial=False):
            """
            Select up to k drones for field from 'available' set.
            If allow_partial is False and fewer than k available, returns [] (decline to partially protect).
            If allow_partial is True, returns as many as available (could be < k).
            """
            avail_list = list(available)
            if not avail_list:
                return []

            cx, cy = self._field_center(field)
            scored: List[Tuple[float, int, object]] = []
            for c in avail_list:
                info = drone_info[c]
                loc = info["loc"]
                # If location missing, treat as far away
                if loc is None:
                    dist = float("inf")
                else:
                    dist = self._distance(loc, cx, cy)
                # Priority tie-breaker: prefer drones already targeting this field (0) over others (1)
                priority = 0 if info["target_id"] == field.id else 1
                # Better to keep existing protectors: if state == 'protecting' and target == field, give smallest priority
                if info["state"] == "protecting" and info["target_id"] == field.id:
                    # make it tie-breaker that pushes them earlier when distances similar
                    priority = -1
                scored.append((dist, priority, c))
            # Sort by distance primarily, then by priority (lower priority value preferred)
            scored.sort(key=lambda t: (t[0], t[1]))
            # Decide how many to pick
            if len(scored) < k and not allow_partial:
                return []
            pick_count = min(k, len(scored))
            selected = [t[2] for t in scored[:pick_count]]
            return selected

        # Main assignment logic
        if not threat_fields:
            # No fields to protect -> all idle
            for c in components:
                assigned[c] = None
            # Issue assignments
            for c in components:
                environment.assign_group(c, idle_group)
            return

        # 1) Primary field: highest threat
        primary = threat_fields[0]
        primary_group = f"protecting {primary.id}"
        k_primary = int(primary.drones_for_full_protection)

        # Select for primary: we always fully protect primary (if we don't have enough drones,
        # we still assign as many as available but primary gets priority)
        # We allow partial assignment only if total drones < k_primary; but specification says always fully protect primary.
        # If not enough drones exist at all, we will assign all to primary.
        if k_primary <= 0:
            k_primary = 0

        # Select primary drones: we always try to pick exactly k_primary from all drones (closest ones)
        # If total drones < k_primary, pick all drones.
        primary_needed = min(k_primary, n_drones)
        primary_selected = select_drones_for_field(primary, primary_needed, allow_partial=True)
        # Mark them assigned
        for c in primary_selected:
            assigned[c] = primary.id
            if c in available:
                available.remove(c)

        # 2) Greedily fully protect other fields if possible
        protected_count = sum(1 for v in assigned.values() if v is not None)
        # Iterate other fields (skip primary)
        for field in threat_fields[1:]:
            if not available:
                break
            k = int(field.drones_for_full_protection)
            if k <= 0:
                continue
            # Prefer to fully protect only if we have enough available drones
            if len(available) >= k:
                sel = select_drones_for_field(field, k, allow_partial=False)
                if not sel:
                    continue
                for c in sel:
                    assigned[c] = field.id
                    if c in available:
                        available.remove(c)
                protected_count += len(sel)
            else:
                # Not enough to fully protect this field; skip for now
                continue

        # 3) Ensure at least half of drones are used for protection
        if protected_count < min_protected:
            # Collect remaining candidate fields in threat order (including primary again if it could use more)
            # But do not overprotect fields: compute how many additional each field can still take up to its drones_for_full_protection
            for field in threat_fields:
                if protected_count >= min_protected:
                    break
                k = int(field.drones_for_full_protection)
                # Count how many already assigned to this field
                already_assigned = sum(1 for v in assigned.values() if v == field.id)
                can_take = max(0, k - already_assigned)
                if can_take <= 0 and already_assigned >= k:
                    continue  # field already fully protected
                # If no capacity for full protection but we still need drones, we allow partial (i.e., assign up to can_take or available)
                # Here can_take may be 0; if so, we still allow assigning partial beyond full? No. We will allow assignment up to can_take.
                if not available:
                    break
                take = min(can_take, len(available))
                if take <= 0:
                    continue
                sel = select_drones_for_field(field, take, allow_partial=True)
                for c in sel:
                    assigned[c] = field.id
                    if c in available:
                        available.remove(c)
                protected_count = sum(1 for v in assigned.values() if v is not None)

            # If still below threshold and we have no field capacity left (e.g. all fields have drones_for_full_protection reached
            # or there were fewer fields than required), we'll assign remaining drones to the highest threat field as partial protection
            # (this is a last resort to satisfy the "at least half used" constraint).
            if protected_count < min_protected and available:
                # Next best field (highest threat) to receive partials
                for field in threat_fields:
                    if not available or protected_count >= min_protected:
                        break
                    k = int(field.drones_for_full_protection)
                    already_assigned = sum(1 for v in assigned.values() if v == field.id)
                    # remaining capacity (could be zero)
                    remaining_capacity = max(0, k - already_assigned)
                    # If no remaining capacity, we may still allow extra partial assignment (exceeding drones_for_full_protection) is NOT allowed.
                    # So we can only assign up to remaining_capacity. If remaining_capacity==0, move to next field.
                    if remaining_capacity <= 0:
                        continue
                    need = min(remaining_capacity, min_protected - protected_count, len(available))
                    if need <= 0:
                        continue
                    sel = select_drones_for_field(field, need, allow_partial=True)
                    for c in sel:
                        assigned[c] = field.id
                        if c in available:
                            available.remove(c)
                    protected_count = sum(1 for v in assigned.values() if v is not None)

        # 4) Any drone still unassigned -> idle
        for c in list(available):
            assigned[c] = None
            available.remove(c)

        # 5) Issue final environment.assign_group calls
        # Validate group ids: there should be protecting groups for threatful fields; fallback to idle when missing
        valid_groups = set(group_ids)
        for c in components:
            field_id = assigned.get(c)
            if field_id is None:
                group = idle_group
            else:
                group = f"protecting {field_id}"
                if group not in valid_groups:
                    # fallback to idle if protecting group not present
                    group = idle_group
            environment.assign_group(c, group)