# -*- coding: utf-8 -*-
"""
RenForge Views Package

This package contains the View layer components of MVC/MVP architecture.
Views are responsible for UI rendering and emitting signals - NOT business logic.
"""

from views.main_view import MainView
from views.table_view import TranslationTableView

__all__ = ['MainView', 'TranslationTableView']
