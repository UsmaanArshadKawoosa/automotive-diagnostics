with open('app/services/diagnostic.py', 'rb') as f:
    content = f.read()
    idx = content.find(b'@staticmethod')
    context = content[max(0,idx-40):idx+80]
    for i, b in enumerate(context):
        print(f'{i:3d}: {b:02x} {chr(b) if 32 <= b < 127 else "."}')