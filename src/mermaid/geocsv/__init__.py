# Bathymetrix®
# https://bathymetrix.com
# © 2026 Bathymetrix, LLC
# Author: Joel D. Simon <jdsimon@bathymetrix.com>
# SPDX-License-Identifier: MIT

"""Read MERMAID GeoCSV files into typed pandas DataFrames."""

from .read import GeoCSVComment, GeoCSVError, GeoCSVMetadata, read

__author__ = "Joel D. Simon <jdsimon@bathymetrix.com>"
__license__ = "MIT"
__copyright__ = "© 2026 Bathymetrix, LLC"
__version__ = "0.9.0"

__all__ = [
    "__version__",
    "read",
    "GeoCSVError",
    "GeoCSVComment",
    "GeoCSVMetadata",
]
