def test_null_code(get_contract_with_gas_estimation):
    null_code = """
@public
def foo():
    pass
    """
    c = get_contract_with_gas_estimation(null_code)
    c.foo()


def test_basic_code(get_contract_with_gas_estimation):
    basic_code = """
@public
def foo(x: int128) -> int128:
    return x * 2

    """
    c = get_contract_with_gas_estimation(basic_code)
    assert c.foo(9) == 18


def test_selfcall_code_3(get_contract_with_gas_estimation, keccak):
    selfcall_code_3 = """
@private
def _hashy2(x: bytes[100]) -> bytes32:
    return keccak256(x)

@public
def return_hash_of_cow_x_30() -> bytes32:
    return self._hashy2(b"cowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcowcow")  # noqa: E501

@private
def _len(x: bytes[100]) -> int128:
    return len(x)

@public
def returnten() -> int128:
    return self._len(b"badminton!")
    """

    c = get_contract_with_gas_estimation(selfcall_code_3)
    assert c.return_hash_of_cow_x_30() == keccak(b'cow' * 30)
    assert c.returnten() == 10
