from setuptools import find_packages, setup

setup(
    name="iqe-sample-plugin",
    packages=find_packages(),
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
)
