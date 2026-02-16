# HashLookupRequest.msg — Trigger a hash lookup in the registry.
# Maps to CodexRegistry.lookup() parameters.

string dhash_hex              # 64-bit dHash to look up (16 hex chars)
int32  max_hamming_distance 5 # Fuzzy match threshold (default 5)
