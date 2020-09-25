
"""
UTM:CSC108, Fall 2020

Major Lab 1

Instructors: Michael Liut, Larry Zhang, Andi Bergen

This code is provided solely for the personal and private use of
students taking the CSC108 course at the University of Toronto.
Copying for purposes other than this use is expressly prohibited.
All forms of distribution of this code, whether as given or with
any changes, are expressly prohibited.
All of the files in this directory and all subdirectories are:
Copyright (c) 2020 Michael Liut, Naaz Sibia, Haocheng Hu
"""


def my_and(a: bool, b: bool) -> bool:
    """
    Return True if <a> and <b> are both True,
    without using 'if' or 'and' statements.
    >>> my_and(True, False)
    False
    >>> my_and(True, True)
    True
    """
    return not((not (a or a)) or not(b or b))


def exists_triangle(x: float, y: float, z: float) -> bool:
    """
    Return True if there exists a proper triangle with sides <x>, <y>, and <z>.

    Do not use 'if' statements.

    >>> exists_triangle(1, 1, 1)
    True
    """
    return not((x + y <= z) or (x + z <= y) or (y + z <= x))


def is_square(num: int) -> bool:
    """
    Returns if <num> is a perfect square.

    That is, whether there exists an integer 'i' such that
    i*i is equal to <num>.

    You may only use arithmetic operations and comparison statements.
    This means no conditionals!

    Precondition: num >= 0

    >>> is_square(5)
    False
    >>> is_square(9)
    True
    """
    return (((num**(0.5)) ** 2) == num)
