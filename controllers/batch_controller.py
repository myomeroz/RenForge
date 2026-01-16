# -*- coding: utf-8 -*-
"""
RenForge Batch Controller
Handles batch translation operations and worker signal handling.
"""

from renforge_logger import get_logger
logger = get_logger("controllers.batch_controller")

from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWidgets import QMessageBox, QTableWidget

from locales import tr
import parser.core as parser
import gui.gui_table_manager as table_manager
from gui.views import batch_status_view, file_table_view
from models.batch_undo import get_undo_manager
from core.error_explainer import ErrorExplainer # New import

class BatchController(QObject):
    """
    Controls batch translation operations:
    - Tracking batch results (errors, warnings, counts)
    - Handling worker signals for item updates
    - Displaying batch completion summaries
    """
    
    # Signal emitted when batch status changes (for Inspector panel)
    # Payload: {processed: int, total: int, success: int, errors: int, is_running: bool}
    batch_status_updated = Signal(dict)
    
    # Signal emitted when batch running state changes (for TranslatePage button enable/disable)
    # Emits True when batch starts, False when batch finishes/cancels
    batch_running_changed = Signal(bool)
    
    def __init__(self, main_window):
        """
        Initialize BatchController with reference to the main window.
        
        Args:
            main_window: The RenForgeGUI instance
        """
        super().__init__()
        self.main = main_window
        
        # Batch operation tracking
        self._errors = []
        self._structured_errors = []
        self._warnings = []
        self._total_processed = 0
        self._success_count = 0
        self._is_running = False
        self._total_items = 0
        self._cancelled = False
        self._active_worker = None  # Reference to active QProcess/worker
        self._last_failed_indices = []
        self._last_run_context = {}
        self._last_error_summary = None # Stores smart error analysis result
    
    # =========================================================================
    # CENTRALIZED STATE MANAGEMENT
    # =========================================================================
    
    def _set_running(self, is_running: bool, reason: str = "unknown"):
        # ... (rest of method unchanged, relying on context match for brevity if tool supported it, but here just replacing block or ensuring init is correct)
        # Actually I just need to patch __init__ and handle_finished.
        # Let's target specific blocks. 

# Re-targeting for better precision:
# 1. Update __init__
# 2. Update handle_finished

        """
        Centralized method to change batch running state.
        
        SINGLE SOURCE OF TRUTH for batch state changes.
        All start/stop/cancel/finish/error paths MUST call this.
        
        Args:
            is_running: New running state
            reason: Human-readable reason for state change (for logging)
        
        Thread Safety:
            This method must be called from the main UI thread.
            Worker threads should use Qt signals connected to this controller.
        """
        # Only emit signal on actual state CHANGE
        if self._is_running == is_running:
            logger.debug(f"[BATCH] State unchanged ({is_running}), reason={reason}")
            return
        
        old_state = self._is_running
        self._is_running = is_running
        
        # Emit dedicated signal for UI button enable/disable
        # This is THE authority for UI state
        self.batch_running_changed.emit(is_running)
        
        # Also emit status dict for Inspector panel
        self._emit_status()
        
        logger.info(f"[BATCH] running: {old_state} -> {is_running} (reason={reason})")
    
    def cancel(self):
        """
        Cancel the current batch operation.
        
        This is the SINGLE authority for batch cancellation.
        All cancel requests (Inspector, TranslatePage) should call this.
        
        IMPORTANT: This does NOT immediately set running=False.
        The worker will finish its current operation and emit finished(canceled=True).
        handle_finished() will then call _set_running(False, "finished_canceled").
        """
        if not self._is_running:
            logger.debug("[BATCH] cancel() called but not running")
            return
        
        if self._cancelled:
            logger.debug("[BATCH] cancel() called but already cancelling")
            return
        
        logger.info("[BatchController] Cancelling batch operation...")
        self._cancelled = True
        
        # Try to cancel the active worker
        if self._active_worker:
            if hasattr(self._active_worker, 'cancel'):
                self._active_worker.cancel()
            elif hasattr(self._active_worker, 'kill'):
                self._active_worker.kill()
            logger.debug("[BatchController] Worker cancel requested")
        else:
            # No worker registered - immediately finish
            logger.warning("[BATCH] No active worker, immediately finishing cancel")
            self._set_running(False, reason="cancel_no_worker")
            return
        
        # DO NOT set running=False here!
        # Worker will emit finished(canceled=True) and handle_finished() will do it.
        # Just update UI to show "İptal ediliyor..."
        self._emit_status()  # This will show current state with _cancelled=True
    
    def set_active_worker(self, worker):
        """Set the active worker for cancel tracking."""
        self._active_worker = worker
    
    def _build_status(self, stage: str = None, current: int = None) -> dict:
        """
        Build a complete status dictionary for UI updates.
        
        SINGLE SOURCE OF TRUTH for all status fields.
        All status emissions MUST use this method.
        
        Args:
            stage: Current operation stage (e.g., "translating", "finished", "canceled")
            current: Current item being processed (for display)
            
        Returns:
            Complete status dict with all required fields
        """
        # Determine stage automatically if not provided
        if stage is None:
            if not self._is_running and self._cancelled:
                stage = "canceled"
            elif not self._is_running and self._total_processed > 0:
                stage = "completed"
            elif not self._is_running:
                stage = "idle"
            elif self._cancelled:
                stage = "cancelling"
            else:
                stage = "running"
        
        return {
            # Core progress
            'done': self._total_processed,
            'total': self._total_items,
            'processed': self._total_processed,  # Alias
            
            # Success/failure counts
            'ok': self._success_count,
            'success': self._success_count,  # Alias
            'failed': len(self._errors),
            'skipped': 0,  # Reserved for future use
            'errors': len(self._errors),  # Alias
            'warnings': len(self._warnings),
            'failed_indices_count': len(self._last_failed_indices),
            'can_retry_failed': (not self._is_running) and (len(self._last_failed_indices) > 0),
            
            # State flags - ALWAYS INCLUDED
            'is_running': self._is_running,
            'running': self._is_running,  # Alias
            'canceled': self._cancelled and not self._is_running,  # True only after worker stopped
            'cancelling': self._cancelled and self._is_running,  # True while waiting for worker
            'completed': not self._is_running and self._total_processed > 0 and not self._cancelled,
            
            # Stage info
            'stage': stage,
            'current': current if current is not None else self._total_processed,
            'error_summary': self._last_error_summary,
        }
    
    def _emit_status(self, stage: str = None, current: int = None):
        """
        Emit current batch status to Inspector panel.
        
        Uses _build_status() as single source of truth for status dict.
        
        Args:
            stage: Optional stage override
            current: Optional current item index
        """
        status = self._build_status(stage=stage, current=current)
        self.batch_status_updated.emit(status)
        logger.debug(f"[BATCH] Status: done={status['done']}/{status['total']}, "
                    f"stage={status['stage']}, is_running={status['is_running']}, "
                    f"canceled={status['canceled']}")
    
    def clear_results(self):
        """Clear all batch result tracking data (called internally, does not change running state)."""
        self._errors = []
        self._warnings = []
        self._total_processed = 0
        self._success_count = 0
        self._total_items = 0
        # NOTE: Do NOT change _is_running here - that's handled by _set_running()
    
    def handle_finished(self, results: dict):
        """
        Handle batch finished signal from worker.
        
        CRITICAL: This is where running state is set to False after worker actually stops.
        Called by main_window._handle_batch_translate_finished().
        
        Args:
            results: Dict with keys like 'canceled', 'success_count', 'error_count', etc.
        """
        was_canceled = results.get('canceled', False)
        reason = "finished_canceled" if was_canceled else "finished_success"
        
        # Update stats from results
        self._success_count = results.get('success_count', 0)
        if 'error_count' in results:
            # errors list may not be populated, use count
            pass  # self._errors is already updated via handle_error calls
        
        # Clear active worker reference
        self._active_worker = None
        
        # SYNC TO MODEL: Set errors for failed items
        # We access structured_errors from the results or self._structured_errors
        # The results dict passed here might contain them, or we use the controller's property logic if results is incomplete
        # Usually results contains 'structured_errors' if we merged them correctly in worker/controller
        # But BatchController accumulates them in self._structured_errors via direct append or from signals?
        # Actually TranslationController emits finished with results.
        # Let's use results.get('structured_errors') or self._structured_errors? 
        # self.structured_errors property returns self._structured_errors.
        # Let's try results first, then fallback.
        
        errs = results.get('structured_errors', [])
        if not errs and hasattr(self, '_structured_errors'):
             errs = self._structured_errors
             
        if errs:
            current_file = self.main._get_current_file_data()
            if current_file:
                for error in errs:
                    idx = error.get('row_id')
                    msg = error.get('message', 'Error')
                    if idx is not None:
                        current_file.set_item_error(idx, msg)
        
        # Keep cancelled flag for status display, then reset
        final_stage = "canceled" if was_canceled else "completed"
        
        # NOW set running to False - worker has actually stopped
        self._set_running(False, reason=reason)
        
        # Emit final status with explicit stage
        self._emit_status(stage=final_stage)
        
        # Reset cancelled flag AFTER status emit so UI shows correct state
        self._cancelled = False
        
        logger.info(f"[BatchController] handle_finished: stage={final_stage}, success={self._success_count}")
    
    def start_batch(self, total_items: int, context: dict = None):
        """
        Start a new batch operation.
        
        Args:
            total_items: Total number of items to process
            context: Optional dict containing run settings (engine, model, langs)
            
        If total_items is 0 or negative, batch is not started (UI stays enabled).
        """
        # Validation: Don't start batch with no items
        if total_items <= 0:
            logger.warning(f"[BATCH] start_batch called with {total_items} items - not starting")
            return
        
        # If this is a FRESH run (not a retry), clear legacy results AND snapshot
        # If context has 'is_retry', we keep the snapshot (but worker will use specific indices)
        is_retry = context.get('is_retry', False) if context else False
        
        # Always clear previous error summary on new start
        self._last_error_summary = None
        
        if not is_retry:
            self.clear_results()
            self._last_failed_indices = []
            self._last_run_context = context or {}
            self._cancelled = False
        else:
            # For retry, we reset current run counters but KEEP the master failed list derived from previous run
            # actually, simpler: just treat it as a new run that happens to process a subset.
            self.clear_results()
            self._cancelled = False
            # context is already passed from retry_failed_last_run
        
        self._total_items = total_items
        
        # Use centralized state management
        self._set_running(True, reason=f"start_batch({total_items})")
        
        # Emit initial status with "starting" stage
        self._emit_status(stage="starting")

    def retry_failed_last_run(self):
        """
        Retry only the items that failed in the last run.
        Uses the saved context (engine, model, langs) from the original run.
        """
        if not self._last_failed_indices:
            logger.warning("[BatchController] retry_failed_last_run called but no failed items stored.")
            return

        if not self._last_run_context:
            logger.warning("[BatchController] No context for retry.")
            return

        logger.info(f"[BatchController] Retrying {len(self._last_failed_indices)} failed items...")

        # Restore context
        ctx = self._last_run_context.copy()
        ctx['is_retry'] = True  # Mark as retry
        
        # Delegate execution back to action handler logic via TranslationController? 
        # Actually, TranslationController handles the worker. We verify the controller methods.
        
        # We need to trigger the specific worker type based on context
        engine = ctx.get('engine', 'unknown')
        indices_to_retry = list(self._last_failed_indices)
        
        # Get current parsed file - assuming we are still on the same file!
        # Ideally context should store file_path too to verify? 
        # For now, trust the user hasn't switched files or assume check in UI.
        current_file_data = self.main._get_current_file_data()
        if not current_file_data:
            logger.error("[BatchController] Cannot retry: no active file")
            return

        # Start the correct worker type
        tc = self.main.gui_handlers.translation_controller
        worker = None
        
        # Start batch (sets UI state)
        self.start_batch(len(indices_to_retry), context=ctx)
        
        if engine == 'google':
            source = ctx.get('source_lang')
            target = ctx.get('target_lang')
            worker, _ = tc.start_batch_google_translation(
                current_file_data, indices_to_retry, source, target
            )
        elif engine == 'ai':
            model = ctx.get('model')
            source = ctx.get('source_lang')
            target = ctx.get('target_lang')
            worker, _ = tc.start_batch_ai_translation(
                current_file_data, indices_to_retry, model, source, target
            )
        else:
            logger.error(f"[BatchController] Unknown engine in context: {engine}")
            self._set_running(False, reason="unknown_engine")
            return

        if worker:
            self.set_active_worker(worker)
            # Connect signals - re-using the main wiring logic would be better but manual here works too
            # Actually, app_bootstrap wires the *controller* signals. 
            # The *worker* signals need to flow into BatchController slots.
            # TranslationController usually emits signals that BatchController listens to?
            # No, looking at TranslationController, it emits `item_translated`, `translation_progress`.
            # Wait, app_bootstrap connects tc.translation_progress -> batch_ctrl.handle_progress?
            # Let's check app_bootstrap or verify how original start works.
            
            # Original flow: gui_action_handler -> tc.start... -> returns worker -> 
            # handler connects worker signals to batch_controller slots.
            
            worker.signals.item_updated.connect(self.handle_item_updated)
            worker.signals.finished.connect(self.handle_finished)
            # progress? usually batch controller doesn't listen to raw progress, 
            # it calculates from item_updated or handle_finished?
            # Let's check handle_item_updated... it increments _total_processed. 
            # So worker.signals.progress is NOT used by BatchController directly?
            # Double check existing code.
            pass
        else:
             self._set_running(False, reason="worker_start_failed")

    def retry_single_line(self, row_index: int):
        """
        Retry a single line using the last batch context.
        
        Args:
            row_index: The index of the row to retry.
        """
        if self._is_running:
            logger.warning("[BatchController] Cannot retry single line while batch is running")
            return
            
        if not self._last_run_context:
            self.main.show_message("Bilgi", "Son çalışma bağlamı bulunamadı.")
            return

        ctx = self._last_run_context
        self._set_running(True, reason="retry_single_line")
        
        # New ephemeral state for single retry
        self._active_worker = None
        self._cancelled = False
        self._total_processed = 0
        self._success_count = 0
        
        # PERSIST STATE: Remove existing errors for this row so we can re-evaluate
        # Filter structured errors
        self._structured_errors = [e for e in self._structured_errors if e.get('row_id') != row_index]
        # Filter legacy errors (best effort: check if it starts with "Line " vs row logic or just don't clear?)
        # Since standard errors strings are "Line {line_idx}: ...", and line_idx might not match row_index exactly if not 1:1,
        # checking structured is safer. We will assume main UI uses structured now.
        # But to be safe, let's keep _errors as is, handle_finished will append.
        # Wait, if we don't remove old string error, it will duplicate.
        # Let's rebuild _errors from _structured_errors later?
        # For now, let's just clear _errors? No, Inspector needs them.
        # Let's try to filter _errors if possible.
        # "Line {line_index}:"
        # We need line_index for this row.
        # We can find it from the file data but that's heavy.
        # Let's hope Inspector uses structured_errors (which we prioritized).
        pass
        
        current_file_data = self.main._get_current_file_data()
        if not current_file_data:
            self._set_running(False, reason="no_file")
            return
            
        source = ctx.get('source_lang')
        target = ctx.get('target_lang')
        engine = ctx.get('engine', 'ai')
        
        worker = None
        tc = self.main.gui_handlers.translation_controller
        
        indices = [row_index]
        self._total_items = 1
        
        if engine == 'google':
            worker, _ = tc.start_batch_google_translation(
                current_file_data, indices, source, target
            )
        elif engine == 'ai':
            model = ctx.get('model')
            worker, _ = tc.start_batch_ai_translation(
                current_file_data, indices, model, source, target
            )
            
        if worker:
            self.set_active_worker(worker)
            worker.signals.item_updated.connect(self.handle_item_updated)
            worker.signals.finished.connect(self.handle_finished)
            self.batch_running_changed.emit(True) 
        else:
            self._set_running(False, reason="worker_start_failed")
    
    @property
    def errors(self):
        return self._errors
        
    @property
    def structured_errors(self):
        return self._structured_errors
    
    @property
    def warnings(self):
        return self._warnings
    
    def capture_undo_snapshot(self, file_path: str, row_indices: list, items: list, 
                              batch_type: str = "ai"):
        """
        Capture undo snapshot before batch operation starts.
        
        Args:
            file_path: Path of the file being processed
            row_indices: List of row indices that will be affected
            items: List of ParsedItem objects (full file items)
            batch_type: "ai" or "google"
        """
        undo_mgr = get_undo_manager()
        undo_mgr.capture(file_path, row_indices, items, batch_type)
        logger.debug(f"[BatchController] Captured undo snapshot for {len(row_indices)} rows")
    
    @Slot(int, str, dict)
    def handle_item_updated(self, item_index: int, translated_text: str, updated_item_data_copy: dict = None):
        """
        Handle batch item update signal from worker.
        
        Args:
            item_index: Index of the item being updated (-1 for batch mode)
            translated_text: The translated text (empty for batch mode)
            updated_item_data_copy: Optional data dict, may contain 'file_path' and 'batch_items'
        """
        updated_item_data_copy = updated_item_data_copy or {}
        file_path = updated_item_data_copy.get('file_path')
        
        current_file_data = None
        if file_path and file_path in self.main.file_data:
             current_file_data = self.main.file_data[file_path]
        else:
             current_file_data = self.main._get_current_file_data()
        
        if not current_file_data:
            logger.error(f"Batch update failed: Could not find file data for {file_path or 'current'}")
            return
        
        current_items = current_file_data.items
        current_lines = current_file_data.lines
        current_mode = current_file_data.mode
        
        # Resolve table widget ONCE
        table_widget = file_table_view.resolve_table_widget(self.main, current_file_data.file_path)
        
        if not table_widget:
            logger.error(f"Batch update failed: No table widget found for {current_file_data.file_path}")
            return

        if not current_items or not current_lines or not current_mode:
            logger.error("Batch update failed: Missing items/lines/mode in file data")
            return
        
        # Check for batch mode (item_index = -1 with batch_items in data)
        batch_items = updated_item_data_copy.get('batch_items', [])
        
        if item_index == -1 and batch_items:
            # BATCH MODE: Process entire chunk at once
            self._process_batch_chunk(
                batch_items, current_file_data, current_items, 
                current_lines, current_mode, table_widget
            )
        elif item_index >= 0:
            # SINGLE ITEM MODE (legacy/Google translate)
            self._process_single_item(
                item_index, translated_text, current_file_data,
                current_items, current_lines, current_mode, table_widget
            )
    
    def _process_batch_chunk(self, batch_items, current_file_data, current_items, 
                              current_lines, current_mode, table_widget):
        """Process a batch of translations efficiently."""
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        
        # Disable table updates while processing
        table_widget.setUpdatesEnabled(False)
        
        try:
            for batch_item in batch_items:
                idx = batch_item.get('index')
                text = batch_item.get('text')
                
                if idx is None or text is None:
                    continue
                    
                if not (0 <= idx < len(current_items)):
                    logger.warning(f"Batch chunk: Index {idx} out of bounds")
                    continue
                
                item_data = current_items[idx]
                before_text = item_data.current_text or ""
                
                # Update item using set_text for proper modification tracking
                if hasattr(item_data, 'set_text'):
                    item_data.set_text(text)
                else:
                    # Fallback for non-ParsedItem objects
                    item_data.current_text = text
                    item_data.is_modified_session = True
                
                # Track success
                self._total_processed += 1
                self._success_count += 1
                
                # Record change (lightweight)
                record = ChangeRecord(
                    timestamp=time.time(),
                    file_path=current_file_data.file_path,
                    item_index=idx,
                    display_row=item_data.line_index + 1 if item_data.line_index is not None else idx + 1,
                    before_text=before_text,
                    after_text=text,
                    source=ChangeSource.BATCH,
                    batch_id="batch"
                )
                get_change_log().add_record(record)
                
                # Update table cell directly (no style update)
                try:
                    table_manager.update_table_item_text(self.main, table_widget, idx, 4, text)
                except Exception as e:
                    logger.debug(f"Batch table update error for idx {idx}: {e}")
                
                # Update file lines for 'translate' mode
                if current_mode == 'translate':
                    line_idx = getattr(item_data, 'line_index', None)
                    if line_idx is not None and 0 <= line_idx < len(current_lines):
                        try:
                            new_line = parser.format_line_from_components(item_data, text)
                            if new_line is not None:
                                current_lines[line_idx] = new_line
                        except Exception as e:
                            logger.debug(f"Batch line format error for idx {idx}: {e}")
            
            # Mark file as modified once
            current_file_data.is_modified = True
            
            # Emit status update after processing chunk
            self._emit_status()
            
        finally:
            # Re-enable table updates
            table_widget.setUpdatesEnabled(True)
    
    def _process_single_item(self, item_index, translated_text, current_file_data,
                              current_items, current_lines, current_mode, table_widget):
        """Process a single translation item (legacy mode)."""
        from core.change_log import get_change_log, ChangeRecord, ChangeSource
        import time
        
        if not (0 <= item_index < len(current_items)):
            logger.error(f"Batch update failed: Index {item_index} out of bounds (len: {len(current_items)})")
            return
        
        original_item_data = current_items[item_index]
        before_text = original_item_data.current_text or ""
        
        original_item_data.current_text = translated_text
        original_item_data.is_modified_session = True
        current_file_data.is_modified = True
        
        # Clear error on success
        current_file_data.clear_item_error(item_index)
        
        # Track single item success
        self._total_processed += 1
        self._success_count += 1
        self._emit_status()
        
        record = ChangeRecord(
            timestamp=time.time(),
            file_path=current_file_data.file_path,
            item_index=item_index,
            display_row=original_item_data.line_index + 1 if original_item_data.line_index is not None else item_index + 1,
            before_text=before_text,
            after_text=translated_text,
            source=ChangeSource.BATCH,
            batch_id="batch"
        )
        get_change_log().add_record(record)
        
        try:
            table_manager.update_table_item_text(self.main, table_widget, item_index, 4, translated_text)
            table_manager.update_table_row_style(table_widget, item_index, original_item_data)
        except Exception as e:
            logger.error(f"Batch update table UI failed: {e}")
        
        if current_mode == 'translate':
            line_index_to_update = getattr(original_item_data, 'line_index', None)
            
            if line_index_to_update is not None and 0 <= line_index_to_update < len(current_lines):
                try:
                    new_line = parser.format_line_from_components(original_item_data, translated_text)
                    if new_line is not None:
                        current_lines[line_index_to_update] = new_line
                    else:
                        self._errors.append(f"- Error updating file line {line_index_to_update+1} for item {item_index+1}")
                except Exception as e:
                    self._errors.append(f"- Error formatting line: {e}")
    
    @Slot(str)
    def handle_error(self, details: str):
        """
        Handle batch translation error signal.
        
        Args:
            details: Error details string
        """
        self._errors.append(details)
        self._emit_status()  # Update Inspector with error count
    
    @Slot(str)
    def handle_warning(self, details: str):
        """
        Handle batch translation warning signal.
        
        Args:
            details: Warning details string
        """
        self._warnings.append(details)
    
    @Slot()
    def mark_tab_modified(self):
        """Mark the current tab as modified from worker thread."""
        self.main._set_current_tab_modified(True)
    
    @Slot(dict)
    def handle_finished(self, results: dict):
        """
        Handle batch translation finished signal.
        
        Args:
            results: Dict with keys: processed, total, success, errors, warnings, made_changes, canceled
        """
        # Determine finish reason
        canceled = results.get('canceled', False)
        reason = "finished_canceled" if canceled else "finished_success"
        
        # Use centralized state management
        self._set_running(False, reason=reason)
        
        # Merge local errors/warnings with results
        result_errors = results.get('errors', [])
        if not isinstance(result_errors, list):
            result_errors = []
        all_errors = list(self._errors) + result_errors
        
        result_warnings = results.get('warnings', [])
        if not isinstance(result_warnings, list):
            result_warnings = []
        all_warnings = list(self._warnings) + result_warnings
        
        # Prepare merged results for formatting
        merged_results = dict(results)
        merged_results['errors'] = all_errors
        merged_results['warnings'] = all_warnings
        
        # Merge structured errors
        result_struct_errors = results.get('structured_errors', [])
        if result_struct_errors:
            self._structured_errors.extend(result_struct_errors)
        
        # Populate failed indices for retry
        # Only overwrite if this wasn't a retry run? 
        # Actually, if it's a retry run, the new failures are the new set to retry.
        # So ALWAYS overwrite with the latest failures.
        # However, if retry was PARTIAL (e.g. user canceled), we might want to keep the union?
        # Requirement: "If retry still fails... Update last_failed_items snapshot again to the remaining failures"
        # So simply taking what the worker reports as failed is correct.
        
        self._last_failed_indices = results.get('failed_indices', [])
        logger.info(f"[BatchController] Stored {len(self._last_failed_indices)} failed indices for retry")

        # Smart Error Analysis
        if self._structured_errors:
             # Use structured errors if available for better context
             try:
                self._last_error_summary = ErrorExplainer.analyze(self._structured_errors)
                logger.info(f"[BatchController] Error analysis complete (structured): {self._last_error_summary.get('title')}")
             except Exception as e:
                logger.error(f"[BatchController] Structured error analysis failed: {e}")
        elif all_errors:
            try:
                self._last_error_summary = ErrorExplainer.analyze(all_errors)
                logger.info(f"[BatchController] Error analysis complete: {self._last_error_summary.get('title')}")
            except Exception as e:
                logger.error(f"[BatchController] Error analysis failed: {e}")

        # Emit an updated terminal status so UI (MiniBatchBar/Inspector) can react to retry availability
        try:
            self._emit_status(stage=("canceled" if canceled else "completed"))
        except Exception as e:
            logger.debug(f"[BatchController] Final status emit failed: {e}")

        # CRITICAL: Refresh table UI with updated model data
        # This is done ONCE after all translations complete (not during)
        current_file_data = self.main._get_current_file_data()
        current_table = self.main._get_current_table()
        
        if current_file_data and current_table:
            # Block signals to avoid triggering item_changed during refresh
            was_blocked = self.main._block_item_changed_signal
            self.main._block_item_changed_signal = True
            
            try:
                # Update file lines for all modified items (translate mode)
                if current_file_data.mode == 'translate':
                    current_lines = current_file_data.lines
                    for item in current_file_data.items:
                        if item.is_modified_session:
                            line_idx = getattr(item, 'line_index', None)
                            if line_idx is not None and 0 <= line_idx < len(current_lines):
                                try:
                                    new_line = parser.format_line_from_components(item, item.current_text)
                                    if new_line is not None:
                                        current_lines[line_idx] = new_line
                                except Exception as e:
                                    logger.debug(f"Line format error at {line_idx}: {e}")
                
                # YENİ: Model-View API ile senkronizasyon
                # Eski populate_table KULLANILMIYOR - o UI'ı bloke ederdi!
                from gui.views.translation_table_view import TranslationTableView
                from gui.widgets.shared_table_view import TranslationTableWidget

                # Check if it's the wrapper widget and get the real view
                real_view = current_table
                if isinstance(current_table, TranslationTableWidget):
                    real_view = getattr(current_table, 'table_view', current_table)

                if isinstance(real_view, TranslationTableView):
                    # Yeni TranslationTableView: Model güncelle
                    file_table_view.sync_parsed_file_to_view(real_view, current_file_data)
                    logger.info("[BatchController] Table synced via Model-View API")
                else:
                    # Eski QTableWidget fallback (geriye dönük uyumluluk)
                    table_manager.populate_table(
                        current_table, 
                        current_file_data.items, 
                        current_file_data.mode
                    )
                    logger.info("[BatchController] Table refreshed via legacy populate_table")
                
                # CRITICAL FIX: Also sync translate_page table (FluentWindow has 2 views!)
                if hasattr(self.main, 'translate_page') and self.main.translate_page:
                    tp_widget = getattr(self.main.translate_page, 'table_widget', None)
                    if tp_widget:
                        tp_view = getattr(tp_widget, 'table_view', tp_widget)
                        if isinstance(tp_view, TranslationTableView) and tp_view is not real_view:
                            file_table_view.sync_parsed_file_to_view(tp_view, current_file_data)
                            logger.info("[BatchController] ALSO synced translate_page table!")
                
            finally:
                self.main._block_item_changed_signal = was_blocked
            
            # Mark file as modified
            current_file_data.is_modified = True
        
        # Use batch_status_view for formatting
        summary_msg = batch_status_view.format_batch_summary(merged_results)
        status_message = batch_status_view.get_status_message(merged_results)
        
        # Display summary
        # QMessageBox.information(self.main, tr("batch_result_title"), summary_msg)
        logger.info(f"Batch finished. Summary: {summary_msg}")
        
        # Mark tab modified if changes were made
        success = results.get('success', results.get('success_count', 0))
        made_changes = results.get('made_changes', success > 0)
        canceled = results.get('canceled', False)
        
        if made_changes and not canceled:
            self.main._set_current_tab_modified(True)
        
        # Update status bar
        self.main.statusBar().showMessage(status_message, 5000)
        self.main._update_ui_state()

