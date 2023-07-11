import setuptools

REQUIRED_PACKAGE = [
    'colorama',
    'PyYAML',
]

setuptools.setup(
    name='hierconfig',
    project_name="Hierarchical Configuration",
    version="1.0.0",
    author="Seungjin Yang",
    author_email="slowmoyang@gmail.com",
    url="https://github.com/slowmoyang/hierconfig",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        'License :: OSI Approved :: Apache Software License',
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=REQUIRED_PACKAGE
)
