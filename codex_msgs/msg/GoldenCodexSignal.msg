# GoldenCodexSignal.msg — Primary SKB transport
# Top-level routing fields extracted for fast filtering.
# Full SKB carried as JSON-LD string.

# Header
builtin_interfaces/Time stamp
string frame_id

# Routing fields (extracted for fast DDS filtering)
string dhash_hex            # 64-bit dHash, 16 hex chars
string match_type           # EXACT | FUZZY | MISS
string pipeline_status      # NOMINAL | DEGRADED | RECOVERY

# Lookup metadata
string matched_hash         # Hash that matched (empty on MISS)
int32  hamming_distance     # 0 for EXACT, >0 for FUZZY, -1 for MISS
float64 lookup_time_ms      # Fast-path lookup duration

# Full SKB payload
string skb_json_ld          # SpatialKinematicBlueprint.to_json_ld() serialized
