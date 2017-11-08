#!/opt/bin/python3
# leel 2016 Jun 09
"""curlometer calculate current and curlB from
   four points
   python version for cal_curometer1.pro
"""


from math import pi
import numpy
from numpy.core.umath_tests import inner1d
from numpy import transpose, cross, sqrt
from numpy.linalg import norm


def normalize(matrix):
    """ return normalized matrix """
    norml = sqrt(inner1d(matrix, matrix))
    if norml == 0:
        return matrix
    return matrix / norml


def printMatrix(mess, matrix):
    print("    ", mess)
    for m in matrix:
        print("    ", m[:])


def printMag(mess, mags):
    print("    ", mess)
    npts = len(mags[0])
    for i in range(npts):
        print(mags[:, i])


def printVectors2(mess, v1, v2):
    print("    ", mess)
    print("    ", v1[:])
    print("    ", v2[:])


def printVectors3(mess, v1, v2, v3):
    print("    ", mess)
    print("    ", v1[:])
    print("    ", v2[:])
    print("    ", v3[:])


def curlometer(magData, posData):
    """ calculate current from magnetic fields at four points
        magData -> magnetic fields for the four spacecraft
                   magdata=array(16,n)
        posData -> position  fields for the four spacecraft
                   posdata=array(16,n)
        returns ->current, curlB
    """
    #  magData 16 column array of bfields
    #  posData 16 column array of positions
    miu3 = (10.0 ** -4) * 4.0 * pi
    np = len(magData[0])
    normj = numpy.empty((3, np))
    normdirect = numpy.empty((3,  np, 3))
    combos = [[0, 1, 2], [0, 2, 3], [0, 3, 1]]
    for count in range(3):
        i, j, k = combos[count]
        mag0 = magData[i * 4: i * 4 + 3, :]
        mag1 = magData[j * 4: j * 4 + 3, :]
        mag2 = magData[k * 4: k * 4 + 3, :]
        pos0 = posData[i * 4: i * 4 + 3, :]
        pos1 = posData[j * 4: j * 4 + 3, :]
        pos2 = posData[k * 4: k * 4 + 3, :]
        magd1 = transpose(mag1 - mag0)
        magd2 = transpose(mag2 - mag0)
        r10 = transpose(pos1 - pos0)
        r20 = transpose(pos2 - pos0)
        if count == 5:
            print(r10.shape)
            printVectors2("r10", r10[0, :], r10[1, :])
            printVectors2("r20", r20[0, :], r20[1, :])
        #  normal direction, normn
        normn = cross(r10, r20)
        norml = sqrt(inner1d(normn, normn))
        for i in range(np):
            normn[i, :] = normalize(normn[i, :])
        # calculate current density along normal direction
        tcurrent = ((magd1 * r20).sum(axis=1) - (magd2 * r10).sum(axis=1)) / (norml * miu3)
        normdirect[count, :, :] = normn
        normj[count, :] = tcurrent
    normat = [0] * np
    invmat = [0] * np
    current = numpy.empty((4, np))
    for i in range(np):
        matrix = numpy.matrix(normdirect[:, i, :])
        normat[i] = matrix.T
        invmat[i] = normat[i].I
        current[0:3, i] = normj[:, i] * invmat[i]
        C_Total = sqrt((current[0:3, i] * current[0:3, i]).sum())
        current[3, i] = C_Total
    curlB = current * miu3
    ql = cal_qlFactor(posData, np)
    return current, curlB, ql


def cal_qlFactor(posData, np):
    volm = [0] * np          # volume
#   surf = [0] * np          # surface area
    leng = numpy.array([1.0] * np)         # length
    pos0 = posData[0:3]
    pos1 = posData[4:7]
    pos2 = posData[8:11]
    pos3 = posData[12:15]
    for i in range(np):
        refpos = pos0[:, i]
        first = pos1[:, i] - refpos
        crs = transpose(cross(pos2[:, i] - refpos, pos3[:, i] - refpos))
        volm[i] = abs(sum(first * crs) / 6.0)
        r10 = pos1[:, i] - pos0[:, i]
        r20 = pos2[:, i] - pos0[:, i]
        r30 = pos3[:, i] - pos0[:, i]
        r21 = pos2[:, i] - pos1[:, i]
        r31 = pos3[:, i] - pos1[:, i]
        r32 = pos3[:, i] - pos2[:, i]
#       print("norm", norm(r10), norm(r20), norm(r30), norm(r21), norm(r31), norm(r32))
        leng[i] = norm(r10) + norm(r20) + norm(r30) + \
            norm(r21) + norm(r31) + norm(r32)
#       print("leng ", leng[i])
    idealvol = ((leng / 6.0) ** 3) * 0.117851
    qlfactor = volm / idealvol
#   return surf, leng, idealvol, qlfactor
    return qlfactor


def curlB(current):
    """ calculate the curlB from current """
    miu3 = (10.0 ** -4) * 4.0 * pi
    curlB = current * miu3
    return curlB
