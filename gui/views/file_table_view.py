# -*- coding: utf-8 -*-
"""
RenForge File Table View - Model-View Mimarisi

Bu modül, eski QTableWidget tabanlı sistemi QTableView + QAbstractTableModel
mimarisi ile değiştirir. Virtual scrolling sayesinde 11,500+ satır bile
UI donması olmadan gösterilir.

NEDEN DONMA OLMAZ:
1. Virtual scrolling: Sadece görünen ~30 satır render edilir
2. data() O(1): Sadece list[index] erişimi
3. Batch dataChanged: Tüm güncellemeler tek sinyalde
4. ID bazlı güncelleme: Proxy sıralaması değişse bile doğru satır güncellenir
"""

from typing import Optional, List, Union, TYPE_CHECKING

from PyQt6.QtWidgets import QTableWidget, QTableView
from PyQt6.QtCore import Qt

from renforge_logger import get_logger
from models.parsed_file import ParsedFile, ParsedItem

from gui.models.translation_table_model import (
    TranslationTableModel, TableRowData, TableColumn
)
from gui.models.translation_filter_proxy import TranslationFilterProxyModel
from gui.views.translation_table_view import TranslationTableView

if TYPE_CHECKING:
    from gui.renforge_gui import RenForgeGUI

logger = get_logger("gui.views.file_table_view")


# =============================================================================
# FACTORY FONKSİYONLARI
# =============================================================================

def create_table_view(main_window: "RenForgeGUI") -> TranslationTableView:
    """
    Yeni bir tablo view oluştur.
    
    Bu fonksiyon eski create_table_widget'ın yerine geçer.
    
    ÖNEMLI: Selection sinyali setModel() SONRASINDA bağlanmalı!
    Çünkü setModel() çağrıldığında selectionModel değişir.
    
    Returns:
        Yapılandırılmış TranslationTableView instance
    """
    # View oluştur
    view = TranslationTableView(main_window)
    
    # Model oluştur
    model = TranslationTableModel(view)
    
    # Proxy oluştur
    proxy = TranslationFilterProxyModel(view)
    proxy.setSourceModel(model)
    
    # View'a proxy'yi bağla
    view.setModel(proxy)
    
    # Varsayılan sütun genişlikleri
    view.set_default_column_widths()
    
    # Referansları view'a kaydet (kolay erişim için)
    view._source_model = model
    view._proxy_model = proxy
    
    # NOT: Selection sinyali artık TranslationTableView.setModel() içinde bağlanıyor
    # Bu sayede setModel sonrası otomatik olarak selectionModel'e bağlanır
    
    logger.debug("[file_table_view] Created new Model-View table")
    
    return view


def get_source_model(view: TranslationTableView) -> Optional[TranslationTableModel]:
    """View'dan source model al."""
    return getattr(view, '_source_model', None)


def get_proxy_model(view: TranslationTableView) -> Optional[TranslationFilterProxyModel]:
    """View'dan proxy model al."""
    return getattr(view, '_proxy_model', None)


def get_row_count(table) -> int:
    """
    Tablo satır sayısını al - hem QTableWidget hem QTableView için çalışır.
    
    Args:
        table: QTableWidget veya QTableView
        
    Returns:
        Satır sayısı
    """
    if hasattr(table, 'model') and table.model():
        return table.model().rowCount()
    elif hasattr(table, 'rowCount'):
        return table.rowCount()
    return 0


# =============================================================================
# VERİ DÖNÜŞÜM FONKSİYONLARI
# =============================================================================

def parsed_items_to_table_rows(items: List[ParsedItem], mode: str) -> List[TableRowData]:
    """
    ParsedItem listesini TableRowData listesine dönüştür.
    
    Bu dönüşüm O(n) ama sadece bir kez yapılır (ilk yükleme).
    
    Args:
        items: ParsedItem listesi
        mode: "translate" veya "direct" (string veya FileMode enum)
        
    Returns:
        TableRowData listesi
    """
    from renforge_enums import ItemType
    
    # Mode string'e çevir
    mode_str = mode.value if hasattr(mode, 'value') else str(mode)
    
    rows = []
    
    for idx, item in enumerate(items):
        # Satır numarası
        line_idx = item.line_index
        line_num = str(line_idx + 1) if line_idx is not None else "-"
        
        # Tip - enum değerini string'e çevir
        raw_type = item.type
        if raw_type is None:
            item_type = ""
        elif hasattr(raw_type, 'value'):
            # Enum durumunda
            item_type = raw_type.value
        else:
            item_type = str(raw_type)
        
        # variable -> var kısaltması
        if item_type == "variable":
            item_type = "var"
        
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
        
        # Status
        batch_marker = getattr(item, 'batch_marker', None) or ""
        batch_tooltip = getattr(item, 'batch_tooltip', None) or ""
        
        row = TableRowData(
            row_id=idx,  # Benzersiz ID olarak item index kullanıyoruz
            line_num=line_num,
            item_type=item_type,
            tag=tag,
            original=original,
            translation=translation,
            is_modified=item.is_modified_session,
            has_breakpoint=item.has_breakpoint,
            batch_marker=batch_marker,
            batch_tooltip=batch_tooltip
        )
        
        rows.append(row)
    
    return rows


def load_data_to_view(view: TranslationTableView, parsed_file: ParsedFile) -> None:
    """
    ParsedFile verisini view'a yükle.
    
    Bu fonksiyon eski populate_table'ın yerine geçer.
    
    PERFORMANS:
    - Dönüşüm O(n) (sadece bir kez)
    - Model reset O(1)
    - View güncellemesi O(görünen satır sayısı)
    
    Args:
        view: TranslationTableView instance
        parsed_file: Yüklenecek ParsedFile
    """
    model = get_source_model(view)
    if not model:
        logger.error("[file_table_view] No source model found on view")
        return
    
    # ParsedItem -> TableRowData dönüşümü
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
    
    Bu fonksiyon, çeviri sırasında satırları güncellemek için kullanılır.
    Proxy sıralaması değişse bile doğru satırlar güncellenir.
    
    Args:
        view: TranslationTableView instance
        updates: {row_id: {"translation": "...", "is_modified": True, ...}}
    """
    model = get_source_model(view)
    if not model:
        return
    
    model.update_rows_by_id(updates)


def update_single_row(view: TranslationTableView, row_id: int, 
                       patch: dict) -> None:
    """Tek satır güncelle."""
    update_rows_by_id(view, {row_id: patch})


def sync_parsed_file_to_view(view: TranslationTableView, 
                              parsed_file: ParsedFile) -> None:
    """
    ParsedFile'dan view'a senkronize et.
    
    Bu fonksiyon, çeviri tamamlandıktan sonra tüm verileri senkronize eder.
    
    Args:
        view: TranslationTableView instance
        parsed_file: Güncel ParsedFile
    """
    model = get_source_model(view)
    if not model:
        return
    
    # Her item için patch oluştur
    updates = {}
    for idx, item in enumerate(parsed_file.items):
        updates[idx] = {
            "translation": item.current_text or "",
            "is_modified": item.is_modified_session,
            "has_breakpoint": item.has_breakpoint,
            "batch_marker": getattr(item, 'batch_marker', "") or "",
            "batch_tooltip": getattr(item, 'batch_tooltip', "") or ""
        }
    
    # Toplu güncelleme
    if updates:
        # Debug: İlk birkaç güncellemeyi logla
        sample_updates = {k: v for k, v in list(updates.items())[:3]}
        logger.info(f"[sync] Sample updates: {sample_updates}")
    
    model.update_rows_by_id(updates)
    
    # NOT: proxy.invalidate() KULLANILMAMALI - sıralamayı bozuyor!
    # dataChanged sinyali zaten proxy tarafından otomatik iletilir
    
    # View'ı manuel olarak yenile
    view.viewport().update()
    
    logger.info(f"[file_table_view] Synced {len(updates)} rows from ParsedFile")


# =============================================================================
# FİLTRELEME FONKSİYONLARI
# =============================================================================

def set_search_filter(view: TranslationTableView, text: str, 
                      column: int = -1) -> None:
    """Arama filtresi ayarla."""
    proxy = get_proxy_model(view)
    if proxy:
        proxy.set_search_text(text, column)


def set_status_filter(view: TranslationTableView, status: str) -> None:
    """Status filtresi ayarla."""
    proxy = get_proxy_model(view)
    if proxy:
        proxy.set_status_filter(status)


def clear_filters(view: TranslationTableView) -> None:
    """Tüm filtreleri temizle."""
    proxy = get_proxy_model(view)
    if proxy:
        proxy.clear_filters()


# =============================================================================
# SEÇİM FONKSİYONLARI
# =============================================================================

def get_selected_row_ids(view: TranslationTableView) -> List[int]:
    """Seçili satırların row_id'lerini döndür."""
    return view.get_selected_row_ids()


def get_selected_indices(view_or_widget) -> List[int]:
    """
    Seçili satır indekslerini al.
    
    Geriye dönük uyumluluk için hem QTableWidget hem de 
    TranslationTableView desteklenir.
    """
    if isinstance(view_or_widget, TranslationTableView):
        return view_or_widget.get_selected_row_ids()
    elif isinstance(view_or_widget, QTableWidget):
        # Eski API uyumluluğu
        return sorted(list(set(index.row() for index in view_or_widget.selectedIndexes())))
    return []


# =============================================================================
# GERİYE DÖNÜK UYUMLULUK
# =============================================================================

def resolve_table_widget(main_window: "RenForgeGUI", 
                          file_path: str) -> Union[QTableWidget, TranslationTableView, None]:
    """
    Tab'dan tablo widget/view bul.
    
    Geriye dönük uyumluluk için hem QTableWidget hem de 
    TranslationTableView döndürülebilir.
    """
    for i in range(main_window.tab_widget.count()):
        if main_window.tab_data.get(i) == file_path:
            widget = main_window.tab_widget.widget(i)
            # Yeni view veya eski widget
            if isinstance(widget, (TranslationTableView, QTableWidget)):
                return widget
    return None


def update_row_text(main_window, table_widget, row_index: int, 
                    column_index: int, new_text: str) -> None:
    """
    Satır metnini güncelle.
    
    Geriye dönük uyumluluk için iki mod desteklenir:
    1. Yeni: TranslationTableView + Model
    2. Eski: QTableWidget + table_manager
    """
    if isinstance(table_widget, TranslationTableView):
        # Yeni API: ID bazlı güncelleme
        if column_index == TableColumn.EDITABLE:
            update_single_row(table_widget, row_index, {"translation": new_text})
    else:
        # Eski API
        import gui.gui_table_manager as table_manager
        table_manager.update_table_item_text(main_window, table_widget, row_index, column_index, new_text)


def update_row_style(table_widget, row_index: int, item_data) -> None:
    """
    Satır stilini güncelle.
    
    Yeni Model-View mimarisinde stil model'den geliyor,
    ayrıca güncellemeye gerek yok.
    """
    if isinstance(table_widget, TranslationTableView):
        # Yeni API: Model zaten stili yönetiyor
        # Sadece data değişikliği emit edilmeli
        model = get_source_model(table_widget)
        if model:
            is_modified = getattr(item_data, 'is_modified_session', False)
            has_breakpoint = getattr(item_data, 'has_breakpoint', False)
            batch_marker = getattr(item_data, 'batch_marker', "") or ""
            batch_tooltip = getattr(item_data, 'batch_tooltip', "") or ""
            
            model.update_rows_by_id({row_index: {
                "is_modified": is_modified,
                "has_breakpoint": has_breakpoint,
                "batch_marker": batch_marker,
                "batch_tooltip": batch_tooltip
            }})
    else:
        # Eski API
        import gui.gui_table_manager as table_manager
        table_manager.update_table_row_style(table_widget, row_index, item_data)
