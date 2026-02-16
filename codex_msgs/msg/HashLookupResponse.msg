# HashLookupResponse.msg — Result from a hash lookup.
# Maps 1:1 to LookupResult dataclass.

string match_type           # EXACT | FUZZY | MISS
string query_hash           # The hash that was queried
string matched_hash         # The hash that matched (empty on MISS)
int32  hamming_distance     # 0 for EXACT, >0 for FUZZY, -1 for MISS
float64 lookup_time_ms      # Lookup duration in milliseconds
string skb_json             # JSON-serialized SKB data (empty on MISS)
