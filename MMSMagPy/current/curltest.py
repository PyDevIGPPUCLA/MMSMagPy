from curlometer import curlometer
import numpy


def runTest():
    file = "posmagdata.txt"
    n = 2
    file = "posmag4.txt"
    n = 4
    # set as an array of 16 columns of size n
#   f = open(file, 'r')
    magData = numpy.zeros((16, n))
    posData = numpy.empty((16, n))
#       x = f.readline()
    x = numpy.loadtxt(file)
#   print(x.shape, x)
#   print(magData.shape, posData.shape)
    for i in range(n):
        magData[:, i] = x[i, :16]
        posData[:, i] = x[i, 16:]
#       print(posData[:, i])
    current, curlB, qf = curlometer(magData, posData)
    print(current.shape)
    print(current)
    print(curlB.shape)
    print(qf.shape)

if __name__ == "__main__":
    runTest()
