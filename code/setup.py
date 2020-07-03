from pathlib import Path

import setuptools

description = "Code needed for Covid19 testing and sequence tracking"

# NOTE: this is not compatible with a sdist installation of covidhub.
requirements_file = Path(__file__).parent.parent / "requirements.txt"
with requirements_file.open("r") as fh:
    requirement_lines = fh.readlines()

setuptools.setup(
    name="covidhub",
    version="0.0.2",
    author="Aaron McGeever",
    author_email="aaron.mcgeever@czbiohub.org",
    description=description,
    long_description=description,
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "qpcr_processing = qpcr_processing.__main__:main",
            "fetch_barcodes = qpcr_processing.scripts.fetch:main",
            "make_layout_pdf = qpcr_processing.scripts.make_layout_pdf:main",
            "cliadb = covid_database.scripts.cliadb:cliadb",
            "comet = comet.__main__:main",
        ]
    },
    include_package_data=True,
    install_requires=requirement_lines,
    extras_require={
        "dev": [
            "black==19.10b0",
            "flake8==3.7.9",
            "ipython==7.15.0",
            "isort @ git+https://github.com/timothycrosley/isort.git@cd9c2f6e70196bd429d0179635e0fac2d034ac5e",
            "pre-commit==2.2.0",
            "pytest==5.4.1",
            "pytest-xdist==1.31.0",
        ],
    },
)
