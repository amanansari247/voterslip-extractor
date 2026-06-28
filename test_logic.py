import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

block_lines = [
    'नपम: ',
    'ललग: ',
    'मकपन सनखखप: ',
    'पनत कप नपम:',
    'आखप:  37',
    'सर',
    '0',
    'ज़ररनप बपनय',
    'रमरद खपन',
    'ALC1761949',
    '1',
    'Photo is ',
    'Available'
]

age = ""
gender = ""
house = ""
name = ""
relative = ""
voter_id = ""
serial = ""

data_lines = []
for bl in block_lines:
    bl_stripped = bl.strip()
    if not bl_stripped: continue
    if 'नपम:' in bl_stripped or 'नपम :' in bl_stripped: continue
    if 'ललग:' in bl_stripped or 'ललग :' in bl_stripped: continue
    if 'मकपन सनखखप:' in bl_stripped or 'मकपन सनखखप :' in bl_stripped: continue
    if 'कप नपम:' in bl_stripped: continue
    if 'आखप' in bl_stripped: continue
    if 'Photo is' in bl_stripped or 'Available' in bl_stripped: continue
    data_lines.append(bl_stripped)

for dl in data_lines:
    if re.match(r'^[A-Z]{2,3}\d{5,}$', dl) or re.match(r'^[A-Z]{2,3}/\d+/\d+/\d+$', dl):
        voter_id = dl
    elif not name and not dl.isdigit() and len(dl) > 1:
        if dl in ['सर', 'पपरष', '0', '00', '01', '02']:
            continue
        if re.match(r'^[\d/\-]+$', dl) or (len(dl) <= 5 and any(c.isdigit() for c in dl)):
            if not house: house = dl
            continue
        name = dl
    elif name and not relative and not dl.isdigit() and len(dl) > 1:
        if dl in ['सर', 'पपरष', '0', '00', '01', '02']:
            continue
        if re.match(r'^[\d/\-]+$', dl) or (len(dl) <= 5 and any(c.isdigit() for c in dl)):
            if not house: house = dl
            continue
        relative = dl
    elif voter_id and dl.isdigit() and 1 <= int(dl) <= 2000:
        serial = dl
    elif not house and re.match(r'^[\d/\-]+$', dl):
        house = dl

print(f"Loop finished. serial={serial}, house={house}, name={name}, voter_id={voter_id}")

if not serial:
    for dl in reversed(data_lines):
        if dl.isdigit() and 1 <= int(dl) <= 2000:
            serial = dl
            break

print(f"Final. serial={serial}, house={house}, name={name}, voter_id={voter_id}")
