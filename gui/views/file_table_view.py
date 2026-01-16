# -*- coding: utf-8 -*-
"""
RenForge File Table View - Model-View Mimarisi

Bu modül, eski QTableWidget tabanlı sistemi QTableView + QAbstractTableModel
mimarisinde çalışacak şekilde yapılandırır.

Değişiklik (UX Redesign Phase 2):
- TableRowData yerine RowData kullanımı
- RowStatus modeline geçiş
"""

import os
from typing import Optional, List, Union, TYPE_CHECKING

from PySide6.QtWidgets import QTableWidget, QTableView, QAbstractItemView, QHeaderView
from PySide6.QtCore import Qt

from renforge_logger import get_logger
from models.parsed_file import ParsedFile, ParsedItem

from gui.models.translation_table_model import (
    TranslationTableModel, TableColumn
)
from gui.models.row_data import RowData, RowStatus
from gui.models.translation_filter_proxy import TranslationFilterProxyModel
from gui.views.translation_table_view import TranslationTableView

if TYPE_CHECKING:
    from gui.renforge_gui import RenForgeGUI

logger = get_logger("gui.views.file_table_view")


# =============================================================================
# FACTORY FONKSİYONLARI
# =============================================================================

def _is_table_perf_enabled() -> bool:
    """
    RENFORGE_TABLE_PERF ortam değişkeni kontrolü.
    0, false, no, off değerlerinden biri ise False döner.
    Varsayılan: True (performans optimizasyonları açık).
    """
    env_val = os.environ.get("RENFORGE_TABLE_PERF", "1").lower().strip()
    return env_val not in ("0", "false", "no", "off")


def apply_large_table_defaults(view: QTableView) -> None:
    """
    Büyük tablolar için performans varsayılanlarını uygula.
    
    Bu fonksiyon, ~10k+ satırlık dosyalarda UI takılmasını önler.
    RENFORGE_TABLE_PERF=0 ile devre dışı bırakılabilir.
    
    Ayarlar:
    - setSortingEnabled(False): Sıralama hesabı yok
    - setWordWrap(False): Kelime sarma yok
    - setUniformRowHeights(True): Tek tip satır yüksekliği
    - setAlternatingRowColors(False): Alternatif renkler kapalı
    - ScrollPerPixel: Pixel bazlı kaydırma
    - Sabit satır yüksekliği (26px)
    - Interactive header resize + stretch last section
    """
    if not _is_table_perf_enabled():
        logger.debug("[apply_large_table_defaults] Disabled via RENFORGE_TABLE_PERF env")
        return
    
    try:
        # Temel performans ayarları
        view.setSortingEnabled(False)
        view.setWordWrap(False)
        view.setAlternatingRowColors(False)
        
        # Scroll modları
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        # Dikey başlık (satır yüksekliği)
        v_header = view.verticalHeader()
        if v_header:
            v_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            v_header.setDefaultSectionSize(26)
        
        # Yatay başlık (sütun genişliği)
        h_header = view.horizontalHeader()
        if h_header:
            h_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            h_header.setStretchLastSection(True)
        
        logger.debug("[apply_large_table_defaults] Applied large table performance defaults")
        
    except Exception as e:
        logger.warning(f"[apply_large_table_defaults] Error applying defaults: {e}")


def create_table_view(main_window: "RenForgeGUI") -> TranslationTableView:
    """TranslationTableView oluştur ve model/proxy bağla."""
    view = TranslationTableView(parent=main_window)
    
    # Büyük tablo performans ayarlarını uygula
    apply_large_table_defaults(view)
    
    # Model oluştur
    model = TranslationTableModel(parent=view)
    
    # Proxy oluştur
    proxy = TranslationFilterProxyModel(parent=view)
    proxy.setSourceModel(model)
    
    # View'a proxy bağla
    view.setModel(proxy)
    
    # Selection model değişince main window'a bildir
    # (Bunu main window içindeki bağlantılar hallediyor olabilir, 
    # ama burada emin olmak için view sinyallerini kullanacağız)
    
    logger.debug("[file_table_view] Initialized table view with model & proxy")
    return view


def get_source_model(view: TranslationTableView) -> Optional[TranslationTableModel]:
    """View'dan ana modeli güvenli şekilde al."""
    if not view:
        return None
    
    current_model = view.model()
    if isinstance(current_model, TranslationFilterProxyModel):
        return current_model.sourceModel()
    elif isinstance(current_model, TranslationTableModel):
        return current_model
    
    return None


# =============================================================================
# VERİ YÜKLEME (POPULATE)
# =============================================================================

def parsed_items_to_table_rows(parsed_items: list, mode_str: str) -> list[RowData]:
    """
    ParsedItem listesini RowData listesine dönüştür. (New Architecture)
    """
    rows = []
    
    for idx, item in enumerate(parsed_items):
        item_type = str(item.item_type) if hasattr(item, 'item_type') else "unknown"
        
        # Tag
        if item_type == "var":
            tag = item.variable_name or "?"
        elif mode_str == "translate":
            tag = item.character_trans or item.character_tag or ""
        else:
            tag = item.character_tag or ""
        
        # Metinler
        original = item.original_text or ""
        translation = item.current_text or ""
        
        # Status Mapping
        status = RowStatus.UNTRANSLATED
        if translation:
            if getattr(item, 'is_modified_session', False):
                status = RowStatus.MODIFIED
            else:
                status = RowStatus.TRANSLATED
        
        # Override with batch markers
        batch_marker = getattr(item, 'batch_marker', None)
        error_message = getattr(item, 'batch_tooltip', None)
        
        if batch_marker == "AI_FAIL":
            status = RowStatus.ERROR
        elif batch_marker == "OK":
            # If OK from AI, keep as TRANSLATED (or upgrade to APPROVED if we decide that)
            if status != RowStatus.MODIFIED:
                status = RowStatus.TRANSLATED
        
        is_flagged = getattr(item, 'has_breakpoint', False)
        
        # Ensure ID is string. ParsedItem doesn't guarantee ID, so we use index if needed,
        # but using index is risky for updates if proxy filters change row count.
        # Ideally ParsedItem has an ID. Assuming 'item' matches parsed file order 
        # and we use index as ID for now like before.
        row_id = str(idx) 
        
        row = RowData(
            id=row_id,
            row_type=item_type,
            tag=tag,
            original_text=original,
            editable_text=translation,
            status=status,
            is_flagged=is_flagged,
            error_message=error_message,
            notes=""
        )
        
        rows.append(row)
    
    return rows


def load_data_to_view(view: TranslationTableView, parsed_file: ParsedFile) -> None:
    """
    ParsedFile verisini view'a yükle.
    """
    model = get_source_model(view)
    if not model:
        logger.error("[file_table_view] No source model found on view")
        return
    
    # ParsedItem -> RowData dönüşümü
    rows = parsed_items_to_table_rows(parsed_file.items, parsed_file.mode)
    
    # Modele yükle
    model.set_rows(rows)
    
    logger.info(f"[file_table_view] Loaded {len(rows)} rows to view")


# =============================================================================
# GÜNCELLEME FONKSİYONLARI
# =============================================================================

def update_rows_by_id(view: TranslationTableView, 
                       updates: dict) -> None:
    """
    ID bazlı toplu güncelleme.
    updates: {row_id: {"editable_text": "...", "status": RowStatus.X, ...}}
    """
    model = get_source_model(view)
    if not model:
        return
    
    # Ensure keys are strings since RowData.id is string
    str_updates = {}
    for k, v in updates.items():
        str_updates[str(k)] = v
        
    model.update_rows_by_id(str_updates)


def update_single_row(view: TranslationTableView, row_id: int, 
                       patch: dict) -> None:
    """Tek satır güncelle."""
    update_rows_by_id(view, {str(row_id): patch})


def sync_parsed_file_to_view(view: TranslationTableView, 
                              parsed_file: ParsedFile) -> None:
    """
    ParsedFile'dan view'a senkronize et.
    """
    load_data_to_view(view, parsed_file)


def resolve_table_widget(main_window, file_path: str = None) -> Optional[TranslationTableView]:
    """
    Verilen dosya için table widget'ı bul.
     Legacy compatibility helper used by gui_action_handler.
    """
    # 1. FluentWindow check
    if hasattr(main_window, 'translate_page'):
        # If file_path is provided, we should ideally find the specific tab
        # For now, we return the current active table view in translate page
        # Assuming the controller switches tabs correctly before calling this
        return main_window.translate_page.table_widget
        
    # 2. Legacy RenForgeGUI check (fallback)
    if hasattr(main_window, 'get_tab_by_file_path'):
        return main_window.get_tab_by_file_path(file_path)
        
    return None
