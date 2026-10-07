# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Read MERMAID GeoCSV files into typed pandas DataFrames."""

from .metadata import GeoCSVComment, GeoCSVMetadata
from .read import GeoCSVError, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.7.5"

__all__ = [
    "__version__",
    "read",
    "GeoCSVError",
    "GeoCSVComment",
    "GeoCSVMetadata",
]
