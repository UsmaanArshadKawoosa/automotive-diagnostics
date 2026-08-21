import shutil
import os

# Clear pycache
for root, dirs, files in os.walk('.'):
    for dir_name in dirs:
        if dir_name == '__pycache__':
            shutil.rmtree(os.path.join(root, dir_name), ignore_errors=True)
    for file in files:
        if file.endswith('.pyc'):
            os.remove(os.path.join(root, file), ignore_errors=True)

print('Cache cleared')