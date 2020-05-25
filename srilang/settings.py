import os
from typing import Optional

srilang_COLOR_OUTPUT = os.environ.get('srilang_COLOR_OUTPUT', '0') == '1'
srilang_ERROR_CONTEXT_LINES = int(os.environ.get('srilang_ERROR_CONTEXT_LINES', '1'))
srilang_ERROR_LINE_NUMBERS = os.environ.get('srilang_ERROR_LINE_NUMBERS', '1') == '1'

srilang_TRACEBACK_LIMIT: Optional[int]

_tb_limit_str = os.environ.get('srilang_TRACEBACK_LIMIT')
if _tb_limit_str is not None:
    srilang_TRACEBACK_LIMIT = int(_tb_limit_str)
else:
    srilang_TRACEBACK_LIMIT = None
