# SlowPathTrigger.msg — Published on MISS, consumed by slow path node.

builtin_interfaces/Time stamp
string frame_id

# Trigger context
string dhash_hex              # Hash that missed
string trigger_event          # e.g. "hash_miss"
string workspace_zone         # Active workspace zone
string end_effector           # Active end-effector
string failure_context        # Human-readable failure description
string image_path             # Path to source image (optional)

# Optional prior context
string previous_action        # Last action primitive attempted
string[] available_objects    # Objects in workspace
