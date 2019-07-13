import os

from petlib.bn import Bn

from zkbuilder.consts import DEFAULT_GROUP
from zkbuilder.exceptions import InvalidExpression


def get_random_point(group=None, random_bits=256):
    """
    Generate some random group generators.

    Args:
        num: Number of generators to generate.
        group: Group
        random_bits: Number of bits of a random string to create a point.

    >>> from petlib.ec import EcPt
    >>> a = get_random_point()
    >>> b = get_random_point()
    >>> isinstance(a, EcPt)
    True
    >>> isinstance(b, EcPt)
    True
    >>> a != b
    True
    """
    if group is None:
        group = DEFAULT_GROUP
    return group.hash_to_point(os.urandom(random_bits))


def make_generators(num, group=None, random_bits=256):
    """
    Create some random group generators.

    .. WARNING ::

        There is a negligible chance that some generators will be the same.

    Args:
        num: Number of generators to generate.
        group: Group
        random_bits: Number of bits of a random number used to create a generator.

    >>> from petlib.ec import EcPt
    >>> generators = make_generators(3)
    >>> len(generators) == 3
    True
    >>> isinstance(generators[0], EcPt)
    True
    """
    if group is None:
        group = DEFAULT_GROUP
    generators = [get_random_point(group, random_bits) for _ in range(num)]
    return generators


def get_random_num(bits):
    """
    Draws a random number of given bitlength.
    """
    order = Bn(2).pow(bits)
    return order.random()


def sum_bn_array(arr, modulus):
    """
    Sum an array of `petlib.bn.Bn` under a modulus.
    """
    if not isinstance(modulus, Bn):
        modulus = Bn(modulus)
    res = Bn(0)
    for elem in arr:
        if not isinstance(elem, Bn):
            elem = Bn(elem)
        res = res.mod_add(elem, modulus)
    return res
