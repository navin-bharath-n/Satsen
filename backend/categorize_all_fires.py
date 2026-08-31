import json, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open('fire_results.json', encoding='utf-8'))

regions = defaultdict(list)
for i, e in enumerate(d, 1):
    state = e.get('state', 'Unknown')
    regions[state].append((i, e.get('lat'), e.get('lon'), e.get('severity')))

print(f"Total events in DB: {len(d)}\n")
print(f"Breakdown across {len(regions)} distinct global sub-regions:\n")

for reg, items in sorted(regions.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"📍 {reg} ({len(items)} events):")
    for idx, lat, lon, sev in items[:5]:  # show up to 5 examples per region
        print(f"   - #{idx:<3} ({lat}, {lon}) | Sev: {sev}")
    if len(items) > 5:
        print(f"   ... and {len(items)-5} more events in this area.")
    print()
