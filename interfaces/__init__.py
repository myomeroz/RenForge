# -*- coding: utf-8 -*-
"""
RenForge Interfaces Package

This package contains Protocol interfaces for dependency injection.
Using Protocol from typing allows structural subtyping (duck typing)
without requiring explicit inheritance.
"""

from interfaces.i_view import (
    IMainView,
    IDialogView,
    ITableView,
)
from interfaces.i_controller import (
    IAppController,
    IFileController,
    ITranslationController,
    IBatchController,
    IProjectController,
)
from interfaces.di_container import DIContainer

__all__ = [
    'IMainView',
    'IDialogView',
    'ITableView',
    'IAppController',
    'IFileController',
    'ITranslationController',
    'IBatchController',
    'IProjectController',
    'DIContainer',
]
