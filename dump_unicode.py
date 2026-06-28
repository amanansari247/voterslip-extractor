import io
text = 'जपवमद हससन'
with io.open('unicode_dump.txt', 'w', encoding='utf-8') as f:
    for c in text:
        f.write(f'{c}: {hex(ord(c))}\n')
