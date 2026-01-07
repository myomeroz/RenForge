# -*- coding: utf-8 -*-
"""
RenForge GUI Controllers Package

DEPRECATED: These controllers have been moved to the top-level 'controllers' package.
Please use:
    from controllers import BatchController, ProjectController
instead of:
    from gui.controllers import BatchController, ProjectController

This module is kept for backward compatibility and will be removed in a future version.
"""

import warnings
warnings.warn(
    "Importing from 'gui.controllers' is deprecated. "
    "Use 'from controllers import BatchController, ProjectController' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from controllers.project_controller import ProjectController
from controllers.batch_controller import BatchController

__all__ = ['ProjectController', 'BatchController']
