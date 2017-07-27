'''
Created on 12 April 2017
@author: Sambit Giri
Setup script
'''

#from setuptools import setup, find_packages
from distutils.core import setup


setup(name='tools21cm',
      version='0.1',
      author='Sambit Giri',
      author_email='sambit.giri@astro.su.se',
      package_dir = {'tools21cm' : 'src'},
      packages=['tools21cm'],
      package_data={'share':['*'],},
      #include_package_data=True,
)
