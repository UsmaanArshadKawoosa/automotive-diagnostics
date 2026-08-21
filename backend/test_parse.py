import ast

code = '''
import json
from typing import Any

class DiagnosticService:
    def _build_prompt(self):
        return \"\"\"Test\"\"\"

    @staticmethod
    def _coerce_string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return []
'''

try:
    ast.parse(code)
    print('Test OK')
except IndentationError as e:
    print(f'Error: {e}')