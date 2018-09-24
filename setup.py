from setuptools import setup

setup(name='ufo-filter',
      version='1.1',
      description='Functional text substitution system',
      url='https://github.com/rjbalest/ufo-filter.git',
      author='Russell Balest',
      author_email='russell@balest.com',
      license='MIT',
      packages=['ufo_filter'],
      scripts=['bin/filter.py'],
      zip_safe=True)
