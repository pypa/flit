"""A sample package"""

__version__ = '0.1'
__flit_module__ = 'package1'
__author__ = 'Sir Robin'
__author_email__ = 'robin@camelot.uk'
__home_page__ = 'http://github.com/sirrobin/package1'
__scripts__ = {
        'pkg-script': 'package1:main'
        }

def main():
    print("package1 main")
