import srilang


def test_basic_init_function(get_contract):
    code = """
val: public(uint256)

@public
def __init__(a: uint256):
    self.val = a
    """

    c = get_contract(code, *[123])

    assert c.val() == 123

    # Make sure the init signature has no unecessary CALLDATLOAD copy.
    opcodes = srilang.compile_code(code, ['opcodes'])['opcodes'].split(' ')
    lll_return_idx = opcodes.index('JUMP')

    assert 'CALLDATALOAD' in opcodes
    assert 'CALLDATALOAD' not in opcodes[:lll_return_idx]
