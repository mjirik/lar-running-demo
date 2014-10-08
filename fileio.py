#! /usr/bin/python
# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger(__name__)

import argparse

import time
import pickle

import sys
import os
# """ import modules from lar-cc/lib """
# sys.path.insert(0, os.path.expanduser('~/projects/lar-cc/lib/py'))
# sys.path.insert(0, '/home/mjirik/projects/lar-cc/lib/py')

from larcc import * # noqa


# input of test file nrn100.py (with definetion of V and FV)
# V = vertex coordinates
# FV = lists of vertex indices of every face (1-based, as required by pyplasm)
#
# sys.path.insert(1, '/Users/paoluzzi/Documents/RICERCA/pilsen/ricerca/')
# from nrn100 import *

def writeFilePickle(filename, vertexes, faces):
    pickle.dump([vertexes, faces], open(filename, 'wb'))


def writeFile(filename, vertexes, faces):
    """
    filename
    vertexes
    faces
    """
    with open(filename, "w") as f:
        for vertex in vertexes:
            try:
                f.write("v %s %s %s\n" % (
                    str(vertex[0]),
                    str(vertex[1]),
                    str(vertex[2])
                ))
            except:
                import ipdb; ipdb.set_trace() #  noqa BREAKPOINT


        for face in faces:
            fstr = "f"
            for i in range(0, len(face)):
                fstr += " %i" % (face[i])

            fstr += "\n"

            f.write(fstr)


def triangulateSquares(F,
                       a=[0, 1, 2], b=[2, 3, 0],
                       c=[1, 0, 2], d=[3, 2, 0]
                       ):
    """
    Convert squares to triangles
    """
    FT = []
    for face in F:
        FT.append([face[a[0]], face[a[1]], face[a[2]]])
        FT.append([face[b[0]], face[b[1]], face[b[2]]])
        # FT.append([face[c[0]], face[c[1]], face[c[2]]])
        # FT.append([face[d[0]], face[d[1]], face[d[2]]])
        # FT.append([face[0], face[3], face[2]])
    return FT


def readFile(filename):
    vertexes = []
    faces = []
    with open(filename, "r") as f:
        for line in f.readlines():
            lnarr = line.strip().split(' ')
            if lnarr[0] == 'v':
                vertexes.append([
                    int(lnarr[1]),
                    int(lnarr[2]),
                    int(lnarr[3])
                ])
            if lnarr[0] == 'f':
                face = [0] * (len(lnarr) - 1)
                for i in range(1, len(lnarr)):
                    face[i - 1] = int(lnarr[i])
                faces.append(face)

    return vertexes, faces

# scipy.sparse matrices required
# Computation of Vertex-to-vertex adjacency matrix
#


def adjacencyQuery(V, FV):
    # dim = len(V[0])
    csrFV = csrCreate(FV)
    csrAdj = matrixProduct(csrTranspose(csrFV), csrFV)
    return csrAdj


def adjacencyQuery0(dim, csrAdj, cell):
    nverts = 4
    cellAdjacencies = csrAdj.indices[
        csrAdj.indptr[cell]:csrAdj.indptr[cell + 1]]
    return [
        acell
        for acell in cellAdjacencies
        if dim <= csrAdj[cell, acell] < nverts
    ]


# construction of the adjacency graph of vertices
# returns VV = adjacency lists (list of indices of vertices
# adjacent to a vertex) of vertices
#
def adjVerts(V, FV):
    n = len(V)
    VV = []
    V2V = adjacencyQuery(V, FV)
    V2V = V2V.tocsr()
    for i in range(n):
        dataBuffer = V2V[i].tocoo().data
        colBuffer = V2V[i].tocoo().col
        row = []
        for val, j in zip(dataBuffer, colBuffer):
            if val == 2:
                row += [int(j)]
        VV += [row]
    return VV


def main():

    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    # logger.debug('input params')

    # input parser
    parser = argparse.ArgumentParser(
        description="Laplacian smoothing"
    )
    parser.add_argument(
        '-i', '--inputfile',
        default=None,
        required=True,
        help='input file'
    )
    parser.add_argument(
        '-o', '--outputfile',
        default='smooth.obj',
        help='input file'
    )
    parser.add_argument(
        '-v', '--visualization', action='store_true',
        help='Use visualization')
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Debug mode')

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)

    t0 = time.time()
    V, FV = readFile(args.inputfile)

    t1 = time.time()
    logger.info('Data imported                   %ss. #V: %i, #FV: %i' %
                (str(t1 - t0), len(V), len(FV)))

    csrAdj = adjacencyQuery(V, FV)
    t2 = time.time()
    logger.info('Adjency query                   %ss' %
                (str(t2 - t1)))

# transformation of FV to 0-based indices (as required by LAR)
    FV = [[v - 1 for v in face] for face in FV]
    t3 = time.time()
    logger.info('FV transformation               %ss' %
                (str(t3 - t2)))

    if False:
    # if args.visualization:
        VIEW(STRUCT(MKPOLS((V, FV))))
        VIEW(EXPLODE(1.2, 1.2, 1.2)(MKPOLS((V, FV))))

    t4 = time.time()
    VV = adjVerts(V, FV)
    t5 = time.time()
    logger.info('adj verts                       %ss' %
                (str(t5 - t4)))
# VIEW(STRUCT(MKPOLS((V,CAT([DISTR([VV[v],v ]) for v in range(n)]))))) #
# long time to evaluate

# Iterative Laplacian smoothing
# input V = initial positions of vertices
# output V1 = new positions of vertices
#
    V1 = AA(CCOMB)([[V[v] for v in adjs] for adjs in VV])

    t6 = time.time()
    logger.info('1st iteration                   %ss' %
                (str(t6 - t5)))
# input V1
# output V2 = new positions of vertices
#
    V2 = AA(CCOMB)([[V1[v] for v in adjs] for adjs in VV])
    t7 = time.time()
    logger.info('2st iteration                   %ss' %
                (str(t7 - t6)))

    if args.visualization:
        # FV = triangulateSquares(FV)
        tv1 = time.time()
        logger.info('triangulation               %ss' %
                    (str(tv1 - t7)))
        VIEW(STRUCT(MKPOLS((V2, FV))))

    import ipdb; ipdb.set_trace() #  noqa BREAKPOINT

    writeFilePickle(args.outputfile+'.pkl', V2, FV)
    writeFile(args.outputfile, V2, FV)
    logger.info("Data stored to ' %s" % (args.outputfile))

if __name__ == "__main__":
    main()