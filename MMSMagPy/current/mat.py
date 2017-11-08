import numpy
from numpy import matrix
from numpy import array
b = array([1,2,3])
x = array([[1, 2, 3], [0, 2, 1], [1, 1, 1]])
m = matrix(x)
print(" MATRIX INVERSE")
print(m.I)
print(" MATRIX CHECKING")
print(m * m.I)
inv = numpy.linalg.inv(m)
print(" MATRIX INVERSE")
print(inv)
print(" MATRIX CHECKING")
print(m * inv)
print("b x m", b * x)
print("mI x b", m.I * b)
