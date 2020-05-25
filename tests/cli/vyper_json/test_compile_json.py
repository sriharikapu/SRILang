#!/usr/bin/env python3

import json
from copy import deepcopy

import pytest

from srilang.cli.srilang_json import compile_from_input_dict, compile_json
from srilang.exceptions import JSONError

FOO_CODE = """
import contracts.bar as Bar

@public
def foo(a: address) -> bool:
    return Bar(a).bar(1)
"""

BAR_CODE = """
@public
def bar(a: uint256) -> bool:
    return True
"""

BAR_ABI = [{
    'name': 'bar',
    'outputs': [{'type': 'bool', 'name': 'out'}],
    'inputs': [{'type': 'uint256', 'name': 'a'}],
    'constant': False,
    'payable': False,
    'type': 'function',
    'gas': 313
}]

INPUT_JSON = {
    'language': "srilang",
    'sources': {
        'contracts/foo.sri': {'content': FOO_CODE},
        'contracts/bar.sri': {'content': BAR_CODE},
    },
    'interfaces': {
        'contracts/bar.json': {'abi': BAR_ABI}
    },
    'settings': {
        'outputSelection': {'*': ["*"]}
    }
}


def test_input_formats():
    assert compile_json(INPUT_JSON) == compile_json(json.dumps(INPUT_JSON))


def test_bad_json():
    with pytest.raises(JSONError):
        compile_json("this probably isn't valid JSON, is it")


def test_keyerror_becomes_jsonerror():
    input_json = deepcopy(INPUT_JSON)
    del input_json['sources']
    with pytest.raises(KeyError):
        compile_from_input_dict(input_json)
    with pytest.raises(JSONError):
        compile_json(input_json)
