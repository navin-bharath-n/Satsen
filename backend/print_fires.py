import json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(open('fire_results.json', encoding='utf-8'))
print(f'Total fire events in DB: {len(d)}')
print()
for i, e in enumerate(d):
    print(f"  {i+1:2}. Lat={e.get('lat'):<10} Lon={e.get('lon'):<10} Sev={e.get('severity'):<8} "
          f"CNN={e.get('cnn_probability','?'):<6} State={e.get('state','?')} / {e.get('district','?')}")
