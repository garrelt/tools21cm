import numpy as np
from glob import glob
from .helper_functions import print_msg
from . import const
from . import conv

class Halo:
	'''
	A simple struct to hold info about a single halo
	'''
	def __init__(self):
		self.pos = [0.0, 0.0, 0.0]		# Position in grid points
		self.pos_cm = [0.0, 0.0, 0.0]	# Center of mass position in grid points
		self.vel = [0.0, 0.0, 0.0]		# Velocity in simulation units
		self.l = [0.0, 0.0, 0.0]		# Angular momentum in simulation units
		self.vel_disp = 0.0				# Velocity dispersion in simulation units
		self.r = 0.0					# Virial radius in grid units
		self.m = 0.0					# Grid mass
		self.mp = 0						# Number of particles
		self.solar_masses = 0.0			# Mass in solar masses


class HaloRockstar:
	'''
	A class that holds information about a large number of halos, as read from Rockstar halo list file.
	Contains methods to select halos based on different criteria. This file is very slow if you need to read a large number of halos.
	'''
	def __init__(self, filename=None, mass_def='vir', max_select_number=-1, startline = 0):
		'''
		Initialize the object. If filename is given, read the file. Otherwise, do nothing.
		'''
		self.halos = []
		self.mass_def = mass_def

		if filename:
			self.read_from_file(filename, max_select_number)

	def read_from_file(self, filename, max_select_number=-1):
		'''
		Read a Rockstar halo list.
		
		Parameters:
			filename (string): The file to read from
			max_select_number = -1 (int): The max number of halos to read. If -1, there is no limit.
		Returns:
			True if all the halos were read. False otherwise.
		'''

		print_msg('Reading Rockstar Halo Catalog %s...' % filename)
		self.filename = filename
		
		import fileinput
		from astropy import units as U

		#Read the file line by line, since it's large
		for linenumber, line in enumerate(fileinput.input(filename)):
			if(linenumber == 0):
				# Store the variable from the file header
				header = line.split()
				idx_pos = header.index('X')
				idx_vel = header.index('VX')
				idx_l = header.index('JX')
				idx_vrms = header.index('Vrms')
				idx_r = header.index('R'+self.mass_def)
				idx_m = header.index('M'+self.mass_def)
			elif(linenumber == 1):
				# Store the redshift from the file header
				a = float(line.split()[-1])
				self.z = 1./a - 1.
			elif(linenumber == 2):
				# Store cosmology quanity from the file header
				cosm = line.split()
				self.Om, self.Ol, self.h = float(cosm[2][:-1]), float(cosm[5][:-1]), float(cosm[-1])
			elif(linenumber == 5):
				# Store particle mass from the file header
				self.part_mass = float(line.split()[2]) #* U.Msun/self.h
			elif(linenumber > 15):
				vals = line.split()
				
				#Create a halo and add it to the list
				if(len(self.halos) > max_select_number):
					halo = Halo()
					halo.pos = np.array(vals[idx_pos:idx_pos+3]).astype(float) #* U.Mpc/self.h
					halo.vel = np.array(vals[idx_vel:idx_vel+3]).astype(float) #* U.km/U.s
					halo.pos_cm = halo.pos
					halo.l = np.array(vals[idx_l:idx_l+3]).astype(float) #* U.Msun/self.h*U.Mpc/self.h*U.km/U.s
					halo.vel_disp = float(vals[idx_vrms]) #*U.km/U.s
					halo.r = float(vals[idx_r]) #* U.kpc/self.h
					halo.m = float(vals[idx_m]) #* U.Msun/self.h
					halo.mp = int(round(halo.m / self.part_mass, 0))
					halo.solar_masses = halo.m
					self.halos.append(halo)
				else:
					break
		
		self.nhalo = len(halo)		# Number or haloes
		fileinput.close()

		return True


class HaloCube3PM:
	'''
	A CubeP3M Halo cataloge files have the following structure:

		Column 1-3:		hpos(:) (halo position (cells))
		Column 4,5:		mass_vir, mass_odc (mass calculated on the grid (in grid masses))
		Column 6,7:		r_vir, r_odc (halo radius, virial and overdensity based)
		Column 8-11:	x_mean(:) (centre of mass position)
		Column 11-14:	v_mean(:) (bulk velocity)
		Column 15-18:	l_CM(:) (angular momentum)
		Column 19-21:	v2_wrt_halo(:) (velocity dispersion)
		Column 21-23:	var_x(:) (shape-related quantity(?))
		Column 17 :		pid_halo
	
	Some useful attributes of this class are:

		nhalo (int): total number of haloes
		z (float): the redshift of the file
		a (float): the scale factor of the file

	'''
	
	def __init__(self, filespath=None, z=None, node=None, mass_def='vir', pid_flag=True):
		'''
		Initialize the file. If filespath is given, read data. Otherwise, do nothing.
		'''

		self.halos = []
		if not z:
			raise NameError('Redshift value not specified, please define.')

		if filespath:
			filespath += '/' if filespath[-1] != '/' else ''
			self.read_from_file(filespath, z, node, mass_def, pid_flag)
		else:
			raise NameError('Files path not specified, please define.')


	def _get_header(self, file):
		# Internal use. Read header for xv.dat and PID.dat
		nhalo = np.fromfile(file, count=1, dtype='int32')[0]
		halo_vir, halo_odc = np.fromfile(file, count=2, dtype='float32')
		return nhalo, halo_vir, halo_odc


	def read_from_file(self, filespath, z, node, mass_def, pid_flag):
		'''
		Read Cube3PM halo catalog from file.
		
		Parameters:
			filespath (string): the path to the nodes directories containing the xv.dat files.
			z = None (float) : redshift value.
			node = None (float) : if specified will return only the output of the specified node
			mass_def = 'vir' (string) : the mass devinition used, can be 'vir' (viral mass) or 'odc' (overdensity)
			pid_flag = True (bool): whether to use the PID-style file format.

		Returns:
			Nothing
		'''

		self.filespath = filespath
		self.z = z

		# if else statement to read halo file for one redshift and one node or all togheter
		if(node == None):
			print_msg('Reading Cube3PM Halo Catalog from all nodes...')
			filesname = ['%snode%d/%.3fhalo%d.dat' %(filespath, i, self.z, i) for i in range(len(glob(filespath+'node*')))]
		else:
			print_msg('Reading Cube3PM Halo Catalog from node = %d...' %node)
			filesname = ['%snode%d/%.3fhalo%d.dat' %(filespath, node, self.z, node)]

		self.nhalo = 0

		for fn in filesname:
			f = open(fn, 'rb')
			nhalo_node, halo_vir, halo_odc = self._get_header(f)				
			self.nhalo += nhalo_node
			
			for i in range(nhalo_node):
				halo = Halo()
				halo.pos = np.fromfile(f, count=3, dtype='float32') #* U.Mpc/self.h
				
				mass_vir, mass_odc, r_vir, r_odc = np.fromfile(f, count=4, dtype='float32') 
				if(mass_def == 'vir'):
					halo.m = mass_vir #* U.Msun/self.h
					halo.r = r_vir #* U.kpc/self.h
					halo.mp = 0		# TODO: DOUBLE CHEKC THIS QUANITTY
				else:
					halo.m = mass_odc #* U.Msun/self.h
					halo.r = r_odc #* U.kpc/self.h
					halo.mp = 0		# TODO: DOUBLE CHEKC THIS QUANITTY

				halo.pos_cm = np.fromfile(f, count=3, dtype='float32') #* U.Mpc/self.h
				halo.vel = np.fromfile(f, count=3, dtype='float32') #* U.km/U.s
				halo.l = np.fromfile(f, count=3, dtype='float32') #* U.Msun/self.h*U.Mpc/self.h*U.km/U.s
				halo.vel_disp = np.linalg.norm(np.fromfile(f, count=3, dtype='float32'))  #* U.km/U.s
				var_x = np.fromfile(f, count=3, dtype='float32')	#shape-related quantity(?)
				
				if(pid_flag):
					pid_halo_node = np.fromfile(f, count=50, dtype='int64')
					xv_halo_node = np.fromfile(f, count=50*6, dtype='float32').reshape((50,6), order='C')
				
				halo.solar_masses = halo.m*conv.M_grid*const.solar_masses_per_gram
				self.halos.append(halo)
		
		return True




class HaloList:
	'''
	A class that holds information about a large number of halos, as read from a 
	halo list file.
	Contains methods to select halos based on different criteria. This file is very slow
	if you need to read a large number of halos.
	
	TODO: write a better implementation of this class.
	'''
	def __init__(self, filename=None, min_select_mass = 0.0, max_select_mass = None, 
			max_select_number=-1, startline = 0):
		'''
		Initialize the object. If filename is given, read the file. Otherwise,
		do nothing.
		
		Parameters:
			* filename = None (string): The file to read from
			* min_select_mass = 0.0 (float): The lower threshold mass in solar masses.
				Only halos above this mass will be read.
			* max_select_mass = None (float): The upper threshold mass in solar masses.
				Only halos below this mass will be read. If None, there is no limit.
			* max_select_number = -1 (int): The max number of halos to read. If -1, there
				is no limit.
			* startline = 0 (int): The line in the file where reading will start.
		Returns:
			Nothing
		'''
		self.halos = []

		if filename:
			self.read_from_file(filename, min_select_mass, max_select_mass, max_select_number, 
					startline)

	def read_from_file(self,filename, min_select_mass = 0.0, max_select_mass = None, max_select_number=-1, 
			startline=0):
		'''
		Read a halo list.
		
		Parameters:
			* filename (string): The file to read from
			* min_select_mass = 0.0 (float): The lower threshold mass in solar masses.
				Only halos above this mass will be read.
			* max_select_mass = None (float): The upper threshold mass in solar masses.
				Only halos below this mass will be read. If None, there is no limit.
			* max_select_number = -1 (int): The max number of halos to read. If -1, there
				is no limit.
			* startline = 0 (int): The line in the file where reading will start.
		Returns:
			True if all the halos were read. False otherwise.
		'''

		self.halos = []

		print_msg('Reading halo file %s...' % filename)
		self.filename = filename
		import fileinput

		#Store the redshift from the filename
		import os.path
		name = os.path.split(filename)[1]
		self.z = float(name.split('halo')[0])

		#Read the file line by line, since it's large
		linenumber = 1
		min_select_grid_mass = min_select_mass/(conv.M_grid*const.solar_masses_per_gram)
		if max_select_mass:
			print_msg('Max_select_mass: %g' % max_select_mass)
			max_select_grid_mass = max_select_mass/(conv.M_grid*const.solar_masses_per_gram)

		for line in fileinput.input(filename):
			if linenumber < startline: #If you want to read from a particular line
				linenumber += 1
				continue
			if max_select_number >= 0 and len(self.halos) >= max_select_number:
				fileinput.close()
				return False
			if linenumber % 100000 == 0:
				print_msg('Read %d lines' % linenumber)
			linenumber += 1

			vals = line.split()			
			grid_mass = float(vals[-3])

			#Create a halo and add it to the list
			if grid_mass > min_select_grid_mass and (max_select_mass == None or grid_mass < max_select_grid_mass):
				halo = Halo()
                                # The following lines used the map() function to convert
                                # parts of the vals list into floats before putting them
                                # into an array. In Python 3 map() returns an iterable,
                                # not a list, so changed this to a list operation.
                                # GM/200601
				halo.pos = np.array([float(i) for i in vals[:3]])
				halo.pos_cm = np.array([float(i) for i in vals[3:6]])
				halo.vel = np.array([float(i) for i in vals[6:9]])
				halo.l = np.array([float(i) for i in vals[9:12]])
				halo.vel_disp = float(vals[12])
				halo.r = float(vals[13])
				halo.m = float(vals[14])
				halo.mp = float(vals[15])
				halo.solar_masses = grid_mass*conv.M_grid*const.solar_masses_per_gram
				self.halos.append(halo)

		fileinput.close()

		return True
