import math
from collections import defaultdict
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    ZERO_THREAT_COOLDOWN = 3  # steps a field must be at 0 threat before releasing drones
    REASSIGN_COOLDOWN = 2     # minimum steps between reassigning a drone
    PARTIAL_PROTECTION_RATIO = 0.5  # allocate up to 50% of remaining drones for partial protection

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._drone_last_assign_step = {}  # drone_id -> step it was last assigned
        self._field_zero_since = {}        # field_id -> step when threat first went to 0
        self._drone_current_field = {}     # drone_id -> field_id it's currently assigned to

    def _field_center(self, field):
        return (field.left + field.right) / 2.0, (field.top + field.bottom) / 2.0

    def _dist_to_field(self, loc, field):
        cx, cy = self._field_center(field)
        return math.sqrt((loc.x - cx) ** 2 + (loc.y - cy) ** 2)

    def assign_drones(self, components, environment, group_ids, step: int):
        # --- Update zero-threat tracking ---
        active_field_ids = set()
        for field in environment.fields:
            fid = field.id
            if field.threat_level > 0:
                active_field_ids.add(fid)
                self._field_zero_since.pop(fid, None)
            else:
                if fid not in self._field_zero_since:
                    self._field_zero_since[fid] = step

        # --- Classify drones into: committed (already protecting a valid active field), or available ---
        # A drone is "locked" if it was recently assigned (cooldown) or is protecting an active field
        committed_by_field = defaultdict(list)  # field_id -> [drones]
        available_drones = []  # (drone, field_id or None)

        for drone in components:
            did = id(drone)
            last_step = self._drone_last_assign_step.get(did, -999)
            current_field = self._drone_current_field.get(did)

            can_reassign = (step - last_step) >= self.REASSIGN_COOLDOWN

            # Determine if this drone should stay where it is
            should_stay = False
            stay_field = None

            if current_field is not None:
                field_obj = next((f for f in environment.fields if f.id == current_field), None)
                if field_obj is not None and field_obj.threat_level > 0:
                    should_stay = True
                    stay_field = current_field
                elif field_obj is not None and field_obj.threat_level <= 0:
                    # Check if cooldown for field release has passed
                    zero_since = self._field_zero_since.get(current_field, step)
                    if step - zero_since < self.ZERO_THREAT_COOLDOWN:
                        # Field was just recently safe - keep drone as a "reserve" there
                        should_stay = True
                        stay_field = current_field
                    elif can_reassign:
                        should_stay = False  # release drone
                    else:
                        should_stay = True  # can't reassign yet, stay temporarily
                        stay_field = current_field
                elif field_obj is None:
                    # Field disappeared or bad target
                    should_stay = False
            else:
                should_stay = False

            if should_stay and stay_field is not None:
                committed_by_field[stay_field].append(drone)
                self._drone_current_field[did] = stay_field
            else:
                available_drones.append(drone)

        # --- Sort active fields by threat level descending ---
        active_fields = sorted(
            [f for f in environment.fields if f.threat_level > 0],
            key=lambda f: f.threat_level,
            reverse=True
        )

        # --- Determine full-protection needs vs. what's already committed ---
        field_needs = {}  # field_id -> additional drones needed for full protection
        field_overcommitted = {}  # field_id -> excess drones that can be released

        for field in active_fields:
            fid = field.id
            needed = field.drones_for_full_protection
            have = len(committed_by_field.get(fid, []))
            field_needs[fid] = max(0, needed - have)
            if have > needed:
                field_overcommitted[fid] = have - needed
                # Release excess drones
                excess_list = committed_by_field[fid][needed:]
                committed_by_field[fid] = committed_by_field[fid][:needed]
                for d in excess_list:
                    available_drones.append(d)
                    self._drone_current_field.pop(id(d), None)

        # --- Release drones from safe fields (threat == 0) that have passed cooldown ---
        for fid in list(committed_by_field.keys()):
            if fid not in active_field_ids:
                # This field is no longer active; check cooldown
                zero_since = self._field_zero_since.get(fid, step)
                if step - zero_since >= self.ZERO_THREAT_COOLDOWN:
                    for d in committed_by_field[fid]:
                        available_drones.append(d)
                        self._drone_current_field.pop(id(d), None)
                    del committed_by_field[fid]

        # --- Sort available drones by proximity to highest-threat fields (greedy) ---
        # We'll assign available drones to fields in priority order, picking closest drones
        assigned_new = {}  # drone_id -> field_id

        for field in active_fields:
            fid = field.id
            deficit = field_needs[fid]
            if deficit <= 0:
                continue

            # Sort available drones by distance to this field
            available_drones.sort(key=lambda d: self._dist_to_field(d.location, field))
            to_assign = available_drones[:deficit]
            available_drones = available_drones[deficit:]

            for d in to_assign:
                did = id(d)
                assigned_new[did] = fid
                self._drone_current_field[did] = fid
                self._drone_last_assign_step[did] = step
                committed_by_field[fid].append(d)

        # --- Handle partial protection with remaining drones ---
        # Sort remaining fields by threat level; assign remaining drones as partial protection
        if available_drones and active_fields:
            # Fields still under-protected
            remaining_deficits = []
            for field in active_fields:
                fid = field.id
                still_need = field.drones_for_full_protection - len(committed_by_field.get(fid, []))
                if still_need > 0:
                    remaining_deficits.append((field, still_need))

            for field, need in remaining_deficits:
                if not available_drones:
                    break
                fid = field.id
                # Assign up to `need` drones (partial is still better than none)
                available_drones.sort(key=lambda d: self._dist_to_field(d.location, field))
                to_assign = available_drones[:need]
                available_drones = available_drones[need:]

                for d in to_assign:
                    did = id(d)
                    self._drone_current_field[did] = fid
                    self._drone_last_assign_step[did] = step
                    # Don't add to committed (it's already in field_needs tracking)

        # --- Final assignment: build the assignment map ---
        drone_to_group = {}

        # Committed drones
        for fid, drones in committed_by_field.items():
            group_name = f"protecting {fid}"
            for d in drones:
                drone_to_group[id(d)] = group_name
                # Don't update last_assign_step for committed drones (they're staying)

        # Newly assigned drones
        for did, fid in assigned_new.items():
            group_name = f"protecting {fid}"
            drone_to_group[did] = group_name

        # Partially assigned drones (from partial protection pass)
        for d in components:
            did = id(d)
            if did not in drone_to_group:
                fid = self._drone_current_field.get(did)
                if fid is not None and fid in active_field_ids:
                    drone_to_group[did] = f"protecting {fid}"

        # --- Assign all drones ---
        for drone in components:
            did = id(drone)
            group_name = drone_to_group.get(did, "idle")
            if group_name not in group_ids:
                group_name = "idle"
            environment.assign_group(drone, group_name)
            if group_name != "idle":
                self._drone_last_assign_step.setdefault(did, step)