import numpy as np
#import c2raytools as c2t
from telescope_functions import jansky_2_kelvin, from_antenna_config
import cosmology as cm

def galactic_synch_fg(z, ncells, boxsize, max_baseline=2.):
	"""
	@ Ghara et al. (2017)
	Parameter
	---------
	z           : Redshift observed with 21-cm.
	ncells      : Number of cells on each axis.
	boxsize     : Size of the FOV in Mpc.
	max_baseline: Maximum baseline of the radio telescope in km (Default: 2).
	Return
	------
	A 2D numpy array of brightness temperature in mK.
	"""
	X  = np.random.normal(size=(ncells, ncells))
	Y  = np.random.normal(size=(ncells, ncells))
	nu = cm.z_to_nu(z)
	nu_s,A150,beta_,a_syn,Da_syn = 150,513,2.34,2.8,0.1
	#c_light, m2Mpc = 3e8, 3.24e-23
	#lam   = c_light/(nu*1e6)/1000.
	U_cb  = (np.mgrid[-ncells/2:ncells/2,-ncells/2:ncells/2]+0.5)*cm.z_to_cdist(z)/boxsize
	l_cb  = 2*np.pi*np.sqrt(U_cb[0,:,:]**2+U_cb[1,:,:]**2)
	C_syn = A150*(1000/l_cb)**beta_*(nu/nu_s)**(-2*a_syn-2*Da_syn*np.log(nu/nu_s))
	solid_angle = boxsize**2/cm.z_to_cdist(z)**2
	AA = np.sqrt(solid_angle*C_syn/2)
	T_four = AA*(X+Y*1j)
	T_real = np.abs(np.fft.ifft2(T_four))   #in Jansky
	return jansky_2_kelvin(T_real*1e6, z, boxsize=boxsize, ncells=ncells)

def extragalactic_pointsource_fg(z, ncells, boxsize, S_max=100):
	"""
	@ Ghara et al. (2017)
	Parameter
	---------
	z           : Redshift observed with 21-cm.
	ncells      : Number of cells on each axis.
	boxsize     : Size of the FOV in Mpc.
	S_max       : Maximum flux of the point source to model in muJy (Default: 100).
	Return
	------
	A 2D numpy array of brightness temperature in mK.
	"""
	nu = cm.z_to_nu(z)
	fg = np.zeros((ncells,ncells))
	dS = 0.01
	Ss = np.arange(0.1, S_max, dS)
	solid_angle = boxsize**2/cm.z_to_cdist(z)**2
	N  = int(10**3.75*np.trapz(Ss**(-1.6), x=Ss, dx=dS)*solid_angle)
	x,y = np.random.random_integers(0, high=ncells-1, size=(2,N))
	alpha_ps = 0.7+0.1*np.random.random(size=N)
	S_s  = np.random.choice(Ss, N)
	nu_s = 150
	S_nu = S_s*(nu/nu_s)**(-alpha_ps)
	for p in xrange(S_nu.size): fg[x[p],y[p]] = S_nu[p]
	return jansky_2_kelvin(fg, z, boxsize=boxsize, ncells=ncells)
	
	
	
	 
	
