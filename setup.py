import os.path
from setuptools import setup, find_packages

root_dir = os.path.dirname(os.path.abspath(__file__))
requirements_fname = os.path.join(root_dir, 'requirements.txt')

with open(requirements_fname) as fp:
    install_requires = [i.strip() for i in fp.readlines()]

setup(
    name="PyVISA-mock",
    version="0.53",
    packages=find_packages(include=['pyvisa_mock', 'pyvisa_mock.*']),
    python_requires='>=3.6',
    install_requires=install_requires,
)
