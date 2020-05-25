def test_test_length(get_contract_with_gas_estimation):
    test_length = """
y: bytes[10]

@public
def foo(inp: bytes[10]) -> int128:
    x: bytes[5] = slice(inp,1, 5)
    self.y = slice(inp, 2, 4)
    return len(inp) * 100 + len(x) * 10 + len(self.y)
    """

    c = get_contract_with_gas_estimation(test_length)
    assert c.foo(b"badminton") == 954, c.foo(b"badminton")
    print('Passed length test')
