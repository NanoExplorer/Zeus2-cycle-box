import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="zhklib-NanoExplorer", 
    version="1.0.1",
    author="Christopher Rooney",
    author_email="ctr44@cornell.edu",
    description="Library for interfacing with the Zeus 2 Cycle Box housekeeping program",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/NanoExplorer/Zeus2-cycle-box",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    scripts= ['zhklib/live_plots.py',
              'zhklib/live_table.py',
              'zhklib/settings_upload.py'
        ],
    python_requires='>=3.6',
    include_package_data=True,
    install_requires=[
        "numpy>=1.13",
        "scipy",
        "pymongo",
        "tabulate",
        "dnspython",
        "matplotlib"
    ]
)
