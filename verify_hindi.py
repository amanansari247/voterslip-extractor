import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('test_hindi.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Polling Station:', data.get('pollingStation'))
print('Total Voters:', len(data.get('voters', [])))

if data.get('voters'):
    for v in data['voters'][:5]:
        print(f"Serial {v['serial']}: {v['name']} | Relative: {v['relativeName']} | Age: {v['age']} | Gender: {v['gender']} | VoterID: {v['voterId']} | House: {v['houseNumber']}")
