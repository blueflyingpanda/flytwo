from setuptools import setup, find_packages

setup(
    name='flytwo',  # Name of your library
    version='0.1.0',  # Library version
    author='Ilya Sagaidac',
    author_email='m.s.v.inkognito@gmail.com',
    description='Flyone HTTP Client',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/blueflyingpanda/flytwo',  # Your library URL
    packages=find_packages(),  # Automatically find packages in the directory
    install_requires=['aiohttp'],  # Dependencies
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
            'console_scripts': [
                'flytwo=flytwo.cli:cli',  # Now it points to the 'cli' group
            ],
        },
    python_requires='>=3.10',  # Minimum Python version requirement
)
