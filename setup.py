from setuptools import setup, find_packages

setup(
    name='mozilla-atmo',
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(exclude=['tests', 'tests/*']),
    description='The code of the Telemetry Analysis Service',
    author='Mozilla Foundation',
    author_email='telemetry-analysis-service@mozilla.org',
    url='https://github.com/mozilla/telemetry-analysis-service',
    license='MPL 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment :: Mozilla',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    zip_safe=False,
)
