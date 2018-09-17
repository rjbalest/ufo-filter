from setuptools import setup

setup(name='ufo-filter',
      version='1.0',
      description='Functional text substitution system',
      url='http://github.com/rjbalest',
      author='Russell Balest',
      author_email='russell@balest.com',
      license='MIT',
      packages=['ufo_filter'],
      scripts=['bin/filter.py'],
      zip_safe=True)