
from setuptools import setup  # distutils removed in Python 3.12+
import py2exe  # type: ignore

# Keep console entry so logs are visible
setup(
    console=[{
        'script': 'src/Server/server.py',
        'dest_base': 'PrometheanProxy',
    }],
    zipfile=None,
    options={
        'py2exe': {
            'bundle_files': 3,  # avoid over-bundling of system DLLs
            'includes': [
                'engineio.async_drivers.threading',
            ],
            'optimize': 2,
            'compressed': True,
            'dist_dir': 'dist',
        }
    }
)
