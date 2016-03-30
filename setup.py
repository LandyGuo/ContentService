from setuptools import setup, find_packages

def file_content(path):
    try:
        with open(path) as f:
            return f.read()
    except IOError:
        return ''

setup(
    name='contentservice',
    version='1.0',
    packages=find_packages(),
    license=file_content('LICENSE'),
    long_description=file_content('README'),
    author='Yu Xia',
    author_email='',
    maintainer='Yu Xia',
    url=''
)
