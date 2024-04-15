import os
from distutils.command.build import build

#from django.core import management
from setuptools import find_packages, setup

from pretix_automated_orders import __version__


try:
    with open(
        os.path.join(os.path.dirname(__file__), "README.rst"), encoding="utf-8"
    ) as f:
        long_description = f.read()
except Exception:
    long_description = ""


class CustomBuild(build):
    def run(self):
#        management.call_command("compilemessages", verbosity=1)
        build.run(self)


cmdclass = {"build": CustomBuild}


setup(
    name="pretix-automated-orders",
    version=__version__,
    description="Plugin for Pretix software that allows automated orders.",
    long_description=long_description,
    url="https://evolutio.pt/",
    author="Joao Pires",
    author_email="jpires@evolutio.pt",
    license="Apache",
    install_requires=["Django==4.2"],
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    cmdclass=cmdclass,
    entry_points="""
[pretix.plugin]
pretix_automated_orders=pretix_automated_orders:PretixPluginMeta
""",
)
