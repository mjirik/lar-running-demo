# -*- coding: utf-8 -*-

from lar import *
from scipy import *
import json
import scipy
import numpy as np
import time as tm
import gc
from pngstack2array3d import *
import struct
import getopt, sys
import traceback
#
import matplotlib.pyplot as plt

# ------------------------------------------------------------
# Logging & Timer
# ------------------------------------------------------------

logging_level = 0;

# 0 = no_logging
# 1 = few details
# 2 = many details
# 3 = many many details

def log(n, l):
	if __name__=="__main__" and n <= logging_level:
		for s in l:
			print "Log:", s;

timer = 1;

timer_last =  tm.time()

def timer_start(s):
	global timer_last;
	if __name__=="__main__" and timer == 1:
		log(3, ["Timer start:" + s]);
	timer_last = tm.time();

def timer_stop():
	global timer_last;
	if __name__=="__main__" and timer == 1:
		log(3, ["Timer stop :" + str(tm.time() - timer_last)]);

# ------------------------------------------------------------
# Configuration parameters
# ------------------------------------------------------------

PNG_EXTENSION = ".png"
BIN_EXTENSION = ".bin"

# ------------------------------------------------------------
# Utility toolbox
# ------------------------------------------------------------

def countFilesInADir(directory):
	return len(os.walk(directory).next()[2])

def isArrayEmpty(arr):
	return all(e == 0 for e in arr)

# ------------------------------------------------------------
def writeOffsetToFile(file, offsetCurr):
	file.write( struct.pack('>I', offsetCurr[0]) )
	file.write( struct.pack('>I', offsetCurr[1]) )
	file.write( struct.pack('>I', offsetCurr[2]) )
# ------------------------------------------------------------

def computeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,bordo3, colors,pixelCalc,centroidsCalc, INPUT_DIR,DIR_O):
	beginImageStack = 0
	endImage = beginImageStack
	MAX_CHAINS = colors
	count = 0

	LISTA_VETTORI = {}
	LISTA_VETTORI2 = {}
	LISTA_OFFSET = {}

	fileName = "selettori-"
	if (calculateout == True):
		fileName = "output-"

	saveTheColors = centroidsCalc
	saveTheColors = sorted(saveTheColors.reshape(1,colors)[0])

	OUTFILES = {}
	for currCol in saveTheColors:
		OUTFILES.update( { str(currCol): open(DIR_O+'/'+fileName+str(currCol)+BIN_EXTENSION, "wb") } )

	for zBlock in range(imageDepth/imageDz):
		startImage = endImage
		endImage = startImage + imageDz
		xEnd, yEnd = 0,0
		theImage,colors,theColors = pngstack2array3d(INPUT_DIR, startImage, endImage, colors, pixelCalc, centroidsCalc)

		# TODO: test this reshape for 3 colors
		theColors = theColors.reshape(1,colors)
		if (sorted(theColors[0]) != saveTheColors):
			log(1, [ "Error: colors have changed"] )
			sys.exit(2)

		for xBlock in range(imageHeight/imageDx):

			for yBlock in range(imageWidth/imageDy):

				xStart, yStart = xBlock * imageDx, yBlock * imageDy
				xEnd, yEnd = xStart+imageDx, yStart+imageDy

				image = theImage[:, xStart:xEnd, yStart:yEnd]
				nz,nx,ny = image.shape

				count += 1

				# Compute a quotient complex of chains with constant field
				# ------------------------------------------------------------

				chains3D_old = {};
				chains3D = {};

				for currCol in saveTheColors:
					chains3D_old.update({str(currCol): []})
					if (calculateout != True):
						chains3D.update({str(currCol): np.zeros(nx*ny*nz,dtype=int32)})

				zStart = startImage - beginImageStack;

				def addr(x,y,z): return x + (nx) * (y + (ny) * (z))


				hasSomeOne = {}
				for currCol in saveTheColors:
					hasSomeOne.update(str(currCol), False)

				if (calculateout == True):
					for x in range(nx):
						for y in range(ny):
							for z in range(nz):
								for currCol in saveTheColors:
									if (image[z,x,y] == currCol):
										tmpChain = chains3D_old[str(currCol)]
										tmpChain.append(addr(x,y,z))
										chains3D_old.update({str(currCol): tmpChain})
				else:
					for x in range(nx):
						for y in range(ny):
							for z in range(nz):
								for currCol in saveTheColors:
									if (image[z,x,y] == currCol):
										tmpChain = chains3D[str(currCol)]
										tmpChain[addr(x,y,z)] = 1
										chains3D.update({str(currCol): tmpChain})
										hasSomeOne.update(str(currCol), True)

				# Compute the boundary complex of the quotient cell
				# ------------------------------------------------------------
				objectBoundaryChain = {}
				if (calculateout == True):
					for currCol in saveTheColors:
						if (len(chains3D_old[str(currCol)]) > 0):
							objectBoundaryChain.update( {str(currCol): larBoundaryChain(bordo3,chains3D_old[str(currCol)])} )
						else:
							objectBoundaryChain.update( {str(currCol): None} )
				# Save
				for currCol in saveTheColors:
					if (calculateout == True):
						if (objectBoundaryChain[str(currCol)] != None):
							writeOffsetToFile( OUTFILES[colorLenStr], np.array([zStart,xStart,yStart], dtype=int32) )
							OUTFILES[colorLenStr].write( bytearray( np.array(objectBoundaryChain[str(currCol)].toarray().astype('b').flatten()) ) )
					else:
						if (hasSomeOne[str(currCol)] != False):
							writeOffsetToFile( OUTFILES[colorLenStr], np.array([zStart,xStart,yStart], dtype=int32) )
							OUTFILES[colorLenStr].write( bytearray( np.array(chains3D[str(currCol)], dtype=np.dtype('b')) ) )

	for currCol in saveTheColors:
		OUTFILES[str(currCol)].flush()
		OUTFILES[str(currCol)].close()

def runComputation(imageDx,imageDy,imageDz, colors,calculateout, V,FV, INPUT_DIR,BEST_IMAGE,BORDER_FILE,DIR_O):
	bordo3 = None

	if (calculateout == True):
		with open(BORDER_FILE, "r") as file:
			bordo3_json = json.load(file)
			ROWCOUNT = bordo3_json['ROWCOUNT']
			COLCOUNT = bordo3_json['COLCOUNT']
			ROW = np.asarray(bordo3_json['ROW'], dtype=np.int32)
			COL = np.asarray(bordo3_json['COL'], dtype=np.int32)
			DATA = np.asarray(bordo3_json['DATA'], dtype=np.int8)
			bordo3 = csr_matrix((DATA,COL,ROW),shape=(ROWCOUNT,COLCOUNT));

	imageHeight,imageWidth = getImageData(INPUT_DIR+str(BEST_IMAGE)+PNG_EXTENSION)
	imageDepth = countFilesInADir(INPUT_DIR)

	Nx,Ny,Nz = imageHeight/imageDx, imageWidth/imageDx, imageDepth/imageDz
	try:
		pixelCalc, centroidsCalc = centroidcalc(INPUT_DIR, BEST_IMAGE, colors)
		computeChains(imageHeight,imageWidth,imageDepth, imageDx,imageDy,imageDz, Nx,Ny,Nz, calculateout,bordo3, colors,pixelCalc,centroidsCalc, INPUT_DIR,DIR_O)
	except:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
		log(1, [ "Error: " + ''.join('!! ' + line for line in lines) ])  # Log it or whatever here
		sys.exit(2)

def main(argv):
	ARGS_STRING = 'Args: -r -b <borderfile> -x <borderX> -y <borderY> -z <borderZ> -i <inputdirectory> -c <colors> -o <outputdir> -q <bestimage>'

	try:
		opts, args = getopt.getopt(argv,"rb:x:y:z:i:c:o:q:")
	except getopt.GetoptError:
		print ARGS_STRING
		sys.exit(2)

	nx = ny = nz = imageDx = imageDy = imageDz = 64
	colors = 2

	mandatory = 5
	calculateout = False
	#Files
	BORDER_FILE = 'bordo3.json'
	BEST_IMAGE = ''
	DIR_IN = ''
	DIR_O = ''

	for opt, arg in opts:
		if opt == '-x':
			nx = ny = nz = imageDx = imageDy = imageDz = int(arg)
			mandatory = mandatory - 1
		elif opt == '-y':
			ny = nz = imageDy = imageDz = int(arg)
		elif opt == '-z':
			nz = imageDz = int(arg)
		elif opt == '-r':
			calculateout = True
		elif opt == '-i':
			DIR_IN = arg + '/'
			mandatory = mandatory - 1
		elif opt == '-b':
			BORDER_FILE = arg
			mandatory = mandatory - 1
		elif opt == '-o':
			mandatory = mandatory - 1
			DIR_O = arg
		elif opt == '-c':
			mandatory = mandatory - 1
			colors = int(arg)
		elif opt == '-q':
			BEST_IMAGE = int(arg)

	if mandatory != 0:
		print 'Not all arguments where given'
		print ARGS_STRING
		sys.exit(2)

	def ind(x,y,z): return x + (nx+1) * (y + (ny+1) * (z))

	def invertIndex(nx,ny,nz):
		nx,ny,nz = nx+1,ny+1,nz+1
		def invertIndex0(offset):
			a0, b0 = offset / nx, offset % nx
			a1, b1 = a0 / ny, a0 % ny
			a2, b2 = a1 / nz, a1 % nz
			return b0,b1,b2
		return invertIndex0

	chunksize = nx * ny + nx * nz + ny * nz + 3 * nx * ny * nz
	V = [[x,y,z] for z in range(nz+1) for y in range(ny+1) for x in range(nx+1) ]

	v2coords = invertIndex(nx,ny,nz)

	FV = []
	for h in range(len(V)):
		x,y,z = v2coords(h)
		if (x < nx) and (y < ny): FV.append([h,ind(x+1,y,z),ind(x,y+1,z),ind(x+1,y+1,z)])
		if (x < nx) and (z < nz): FV.append([h,ind(x+1,y,z),ind(x,y,z+1),ind(x+1,y,z+1)])
		if (y < ny) and (z < nz): FV.append([h,ind(x,y+1,z),ind(x,y,z+1),ind(x,y+1,z+1)])

	runComputation(imageDx, imageDy, imageDz, colors, calculateout, V, FV, DIR_IN, BEST_IMAGE, BORDER_FILE, DIR_O)

if __name__ == "__main__":
	main(sys.argv[1:])
