with open('app/services/diagnostic.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.lstrip().startswith('@staticmethod') and i > 0:
        prev_line = lines[i-1].rstrip('\n')
        print(f'Line {i+1}: prev="{prev_line}", curr="{line.rstrip()}"')