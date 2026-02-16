# SlowPathResult.msg — Published after LLM recovery completes.

builtin_interfaces/Time stamp
string frame_id

# Result metadata
string trigger_dhash_hex      # Original hash that caused the miss
string primitive_id           # Selected action primitive
float64 confidence_score      # LLM confidence [0.0, 1.0]
float64 generation_time_ms    # Total LLM generation time

# Promotion status
bool promoted                 # Whether result was promoted to fast path
string skb_json               # Full generated SKB as JSON
