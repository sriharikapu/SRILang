#!/usr/bin/env python3

import pytest

from srilang.cli.srilang_json import TRANSLATE_MAP, get_input_dict_output_formats
from srilang.exceptions import JSONError


def test_no_outputs():
    with pytest.raises(KeyError):
        get_input_dict_output_formats({}, {})


def test_invalid_output():
    input_json = {'settings': {'outputSelection': {'foo.sri': ['abi', 'foobar']}}}
    sources = {'foo.sri': ""}
    with pytest.raises(JSONError):
        get_input_dict_output_formats(input_json, sources)


def test_unknown_contract():
    input_json = {'settings': {'outputSelection': {'bar.sri': ['abi']}}}
    sources = {'foo.sri': ""}
    with pytest.raises(JSONError):
        get_input_dict_output_formats(input_json, sources)


@pytest.mark.parametrize('output', TRANSLATE_MAP.items())
def test_translate_map(output):
    input_json = {'settings': {'outputSelection': {'foo.sri': [output[0]]}}}
    sources = {'foo.sri': ""}
    assert get_input_dict_output_formats(input_json, sources) == {'foo.sri': [output[1]]}


def test_star():
    input_json = {'settings': {'outputSelection': {'*': ['*']}}}
    sources = {'foo.sri': "", 'bar.sri': ""}
    expected = sorted(TRANSLATE_MAP.values())
    result = get_input_dict_output_formats(input_json, sources)
    assert result == {'foo.sri': expected, 'bar.sri': expected}


def test_evm():
    input_json = {'settings': {'outputSelection': {'foo.sri': ['abi', 'evm']}}}
    sources = {'foo.sri': ""}
    expected = ['abi'] + sorted(v for k, v in TRANSLATE_MAP.items() if k.startswith('evm'))
    result = get_input_dict_output_formats(input_json, sources)
    assert result == {'foo.sri': expected}


def test_solc_style():
    input_json = {'settings': {'outputSelection': {'foo.sri': {'': ['abi'], 'foo.sri': ['ir']}}}}
    sources = {'foo.sri': ""}
    assert get_input_dict_output_formats(input_json, sources) == {'foo.sri': ['abi', 'ir']}
