from curlmeter import curlometer
import numpy
from numpy import sin, pi


def runTest():
    n = 2
    # set as an array of 16 columns of size n
    magData = numpy.zeros((16, n))
    posData = numpy.empty((16, n))
#   for i in range(n):   # set values in a columns as constant
#       magData[:, i] = numpy.array(range(16))
#       posData[:, i] = numpy.array(range(16))
#   for i in range(n):   # set values in a rows as a constant
#       magData[:, i].fill(i)
#       posData[:, i].fill(i)
    dr = pi / 16
    for i in range(4):   # space craft
        A = 100
        c = i * 3
        d = i * 2
        for j in range(4):  # bx,by,bz,bt
            B = 10
            index = i * 4 + j
            for k in range(n):   # time
                magData[index, k] = A * i + B * j + k
                posData[index, k] = c * i + d * j + k
    for i in range(16):
        posData[i, 0] = 20 * sin(i * dr)
        posData[i, 1] = 10 * sin(i * dr)
#       print(i, i * dr,  sin(i * dr))
#   print("MAG DATA 0", magData)
    curlometer(magData, posData)

if __name__ == "__main__":
    runTest()
