# -*- coding: utf-8 -*-
"""
RenForge Packaging Page

MVP Implementation (v2):
- Export/Import cards with clear descriptions
- Generate Ren'Py Output (functional status preview)
- File statistics summary
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    SubtitleLabel, PushButton, CardWidget, 
    FluentIcon as FIF, BodyLabel, TitleLabel, InfoBar, InfoBarPosition
)

from renforge_logger import get_logger

logger = get_logger("gui.pages.packaging")


class PackagingPage(QWidget):
    """Packaging page - MVP with export preview."""
    
    # Signal to request translation file generation
    generate_requested = Signal()
    export_pack_requested = Signal()
    import_pack_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PackagingPage")
        
        self._open_files = []
        self._total_rows = 0
        self._translated_rows = 0
        self._approved_rows = 0
        
        self._setup_ui()
        logger.debug("PackagingPage v2 initialized")
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header = TitleLabel("Paketleme ve Dışa Aktarım")
        layout.addWidget(header)
        
        # Info Description
        info_label = BodyLabel(
            "Çevirilerinizi paketleyin, paylaşın veya doğrudan Ren'Py oyununa aktarın."
        )
        info_label.setStyleSheet("color: #888888;")
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Stats Card
        self.stats_card = CardWidget(self)
        stats_layout = QVBoxLayout(self.stats_card)
        stats_layout.setContentsMargins(16, 16, 16, 16)
        
        stats_title = SubtitleLabel("📊 Proje Durumu")
        stats_layout.addWidget(stats_title)
        
        self.stats_label = BodyLabel("Dosya yok. Önce bir dosya açın.")
        self.stats_label.setStyleSheet("color: #aaaaaa;")
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(self.stats_card)
        
        # Row 1: Export / Import Cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)
        
        # Export Card
        self.export_card = self._create_action_card(
            "📦 Dışa Aktar (.rfpack)",
            "Çevirilerinizi paylaşılabilir .rfpack dosyası olarak paketleyin. "
            "Başka kullanıcılarla paylaşmak veya yedeklemek için idealdir.",
            "Paketi Dışa Aktar",
            FIF.SHARE,
            self._on_export_pack
        )
        cards_layout.addWidget(self.export_card)
        
        # Import Card
        self.import_card = self._create_action_card(
            "📥 İçe Aktar (.rfpack)",
            "Başka birinin gönderdiği .rfpack dosyasını projenize yükleyin. "
            "Mevcut çeviriler birleştirilir.",
            "Paketi İçe Aktar",
            FIF.DOWNLOAD,
            self._on_import_pack
        )
        cards_layout.addWidget(self.import_card)
        
        layout.addLayout(cards_layout)
        
        # Row 2: Ren'Py Output
        self.output_card = CardWidget(self)
        output_layout = QVBoxLayout(self.output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)
        
        out_title = SubtitleLabel("🎮 Ren'Py Çıktısı Oluştur")
        out_desc = BodyLabel(
            "Çevirileri oyunun 'game/tl/turkish/' klasörüne yazarak "
            "oyunda test edilebilir hale getirin. Onaylanmış satırlar öncelikli olarak işlenir."
        )
        out_desc.setWordWrap(True)
        out_desc.setStyleSheet("color: #888888;")
        
        btn_layout = QHBoxLayout()
        self.generate_btn = PushButton("Ren'Py Dosyalarını Oluştur")
        self.generate_btn.setIcon(FIF.CODE)
        self.generate_btn.setToolTip("Çevirileri .rpy formatında oluşturur")
        self.generate_btn.clicked.connect(self._on_generate)
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addStretch()
        
        output_layout.addWidget(out_title)
        output_layout.addWidget(out_desc)
        output_layout.addSpacing(10)
        output_layout.addLayout(btn_layout)
        
        layout.addWidget(self.output_card)
        layout.addStretch()
    
    def _create_action_card(self, title, desc, btn_text, icon, on_click):
        """Create an action card with button."""
        card = CardWidget(self)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title_lbl = SubtitleLabel(title)
        desc_lbl = BodyLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #888888;")
        
        btn = PushButton(btn_text)
        btn.setIcon(icon)
        btn.clicked.connect(on_click)
        
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addSpacing(15)
        layout.addWidget(btn)
        layout.addStretch()
        
        return card
    
    # =========================================================================
    # ACTIONS
    # =========================================================================
    
    def _on_export_pack(self):
        """Handle export pack button."""
        if not self._open_files:
            InfoBar.warning(
                title="Dosya Yok",
                content="Önce en az bir dosya açın.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        self.export_pack_requested.emit()
        InfoBar.info(
            title="Dışa Aktarım",
            content="Bu özellik yakında eklenecek.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
    
    def _on_import_pack(self):
        """Handle import pack button."""
        self.import_pack_requested.emit()
        InfoBar.info(
            title="İçe Aktarım",
            content="Bu özellik yakında eklenecek.",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
    
    def _on_generate(self):
        """Handle generate Ren'Py files button."""
        if not self._open_files:
            InfoBar.warning(
                title="Dosya Yok",
                content="Önce en az bir dosya açın.",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        self.generate_requested.emit()
        InfoBar.success(
            title="Oluşturma",
            content=f"Ren'Py çıktısı oluşturulacak: {len(self._open_files)} dosya",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
    
    # =========================================================================
    # PUBLIC API
    # =========================================================================
    
    def update_stats(self, open_files: list, total: int, translated: int, approved: int):
        """Update statistics display."""
        self._open_files = open_files
        self._total_rows = total
        self._translated_rows = translated
        self._approved_rows = approved
        
        if not open_files:
            self.stats_label.setText("Dosya yok. Önce bir dosya açın.")
            return
        
        percent_done = (translated / total * 100) if total > 0 else 0
        percent_approved = (approved / total * 100) if total > 0 else 0
        
        stats_text = (
            f"📄 Açık Dosya: {len(open_files)}\n"
            f"📝 Toplam Satır: {total:,}\n"
            f"✓ Çevrilmiş: {translated:,} ({percent_done:.1f}%)\n"
            f"✔ Onaylı: {approved:,} ({percent_approved:.1f}%)"
        )
        self.stats_label.setText(stats_text)
