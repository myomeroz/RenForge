"""
RenForge Project Utilities
Handles RPA extraction and RPYC decompilation for Ren'Py projects.
"""
import os
import sys
import subprocess
import time
import shutil
import runpy
from pathlib import Path
from typing import List, Tuple
import io 

import renforge_config as config
from renforge_logger import get_logger

logger = get_logger("core.utils")


def _is_tool_available(name):
    """Check if a command-line tool is available in PATH."""
    return shutil.which(name) is not None


# Check for unrpa availability
UNRPA_COMMAND = None
if _is_tool_available("unrpa"):
    UNRPA_COMMAND = "unrpa"
    logger.info("'unrpa' komutu sistem PATH'inde bulundu.")
else:
    try:
        result = subprocess.run([sys.executable, "-m", "unrpa", "--version"], capture_output=True, text=True, check=False, timeout=5)
        if result.returncode == 0 or "usage: unrpa" in result.stderr.lower() or "usage: __main__.py" in result.stderr.lower(): 
            UNRPA_COMMAND = [sys.executable, "-m", "unrpa"] 
            logger.info("'unrpa' modülü 'python -m unrpa' ile kullanılabilir.")
        else:
            logger.warning("'unrpa' komutu PATH'te bulunamadı ve 'python -m unrpa' ile erişilemiyor. *.rpa çıkarma kullanılamayacak.")
            logger.warning("         'unrpa' kurulumunu (pip install unrpa) ve PATH değişkenini kontrol edin.")
            logger.warning(f"         (python -m unrpa --version dönüş kodu: {result.returncode}, stderr: {result.stderr[:100]}...)")
    except FileNotFoundError:
         logger.warning(f"Python yorumlayıcısı '{sys.executable}' bulunamadı. 'python -m unrpa' kontrol edilemiyor.")
    except subprocess.TimeoutExpired:
         logger.warning("'python -m unrpa' kontrolü çok uzun sürdü.")
    except Exception as e:
         logger.warning(f"'python -m unrpa' kontrol hatası: {e}")

UNRPA_AVAILABLE = UNRPA_COMMAND is not None

# Check for unrpyc availability
_CURRENT_DIR = Path(__file__).parent
UNRPYC_LIB_DIR = _CURRENT_DIR / "unrpyc_lib" 
UNRPYC_SCRIPT_PATH = UNRPYC_LIB_DIR / "unrpyc.py" 

if UNRPYC_SCRIPT_PATH.is_file():
    UNRPYC_AVAILABLE = True
    if not (UNRPYC_LIB_DIR / "decompiler").is_dir():
         logger.warning(f"'{UNRPYC_SCRIPT_PATH.name}' betiği bulundu, ancak 'decompiler' klasörü '{UNRPYC_LIB_DIR}' içinde yok.")
         logger.warning("         unrpyc'nin TÜM içeriğini 'unrpyc_lib' klasörüne kopyaladığınızdan emin olun.")
    else:
         logger.info(f"Dekompile betiği '{UNRPYC_SCRIPT_PATH.name}' ve 'decompiler' klasörü '{UNRPYC_LIB_DIR}' içinde bulundu.")
else:
    UNRPYC_AVAILABLE = False
    logger.warning(f"Dekompile betiği '{UNRPYC_SCRIPT_PATH.name}' '{UNRPYC_LIB_DIR}' içinde bulunamadı.")
    logger.warning("         *.rpyc dekompilasyonu kullanılamayacak.")
    logger.warning("         unrpyc kütüphanesini (decompiler klasörü dahil) 'utils/unrpyc_lib' klasörüne yerleştirin.")


def _extract_single_rpa(rpa_path: Path, project_path: Path, force_extract: bool = False) -> Tuple[bool, str]:
    """Extract a single RPA archive."""
    if not UNRPA_AVAILABLE:
        return False, "unrpa komutu kullanılamıyor."

    marker_file = rpa_path.with_suffix(rpa_path.suffix + '.extracted_by_renforge')

    if not force_extract and marker_file.exists():
        return True, f"'{rpa_path.name}' arşivi daha önce çıkarılmış (işaretçi bulundu)."

    game_dir = project_path / "game"
    if not game_dir.is_dir():
        logger.warning(f"'game' klasörü {project_path} içinde bulunamadı. Çıkarma CWD={project_path} ile yapılacak.")
        target_cwd = project_path
    else:
        target_cwd = game_dir

    logger.info(f"Arşiv çıkarma deneniyor: {rpa_path} (CWD: {target_cwd})")

    command_base = []
    if isinstance(UNRPA_COMMAND, list):
        command_base.extend(UNRPA_COMMAND)
    else:
        command_base.append(UNRPA_COMMAND)
    command = command_base + [str(rpa_path)]

    logger.debug(f"Komut çalıştırılıyor: {' '.join(map(str, command))}")
    logger.debug(f"CWD dizini: {target_cwd}") 

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            cwd=str(target_cwd), 
            timeout=300
        )

        if result.returncode == 0:
             stderr_lower = result.stderr.lower()
             stdout_lower = result.stdout.lower()
             if "no such file" in stderr_lower or "no such file" in stdout_lower:
                   error_message = f"unrpa '{rpa_path.name}' için 'No such file' hatası verdi.\n--- STDERR ---\n{result.stderr.strip()}\n--- STDOUT ---\n{result.stdout.strip()}"
                   logger.error(error_message)
                   return False, f"unrpa '{rpa_path.name}' için 'No such file' hatası. Konsolu kontrol edin."
             elif "error:" in stderr_lower or "error:" in stdout_lower or "failed" in stderr_lower or "failed" in stdout_lower:
                  error_message = f"unrpa '{rpa_path.name}' için kod 0 döndürdü, ancak çıktıda hata var:\n--- STDERR ---\n{result.stderr.strip()}\n--- STDOUT ---\n{result.stdout.strip()}"
                  logger.warning(error_message)
                  return False, f"unrpa '{rpa_path.name}' için hata (Kod: 0, ancak çıktıda hata var). Konsolu kontrol edin."
             else:
                  logger.info(f"'{rpa_path.name}' arşivi {target_cwd} klasöründe başarıyla işlendi.")
                  try:
                      marker_file.touch()
                  except OSError as e:
                      logger.warning(f"İşaretçi dosyası oluşturulamadı {marker_file}: {e}")
                  return True, f"'{rpa_path.name}' arşivi başarıyla işlendi."
        else:
            error_message = f"'{rpa_path.name}' çıkarılırken hata (Kod: {result.returncode}):\n--- STDERR ---\n{result.stderr.strip()}\n--- STDOUT ---\n{result.stdout.strip()}"
            logger.error(error_message)
            return False, f"unrpa '{rpa_path.name}' için hata (Kod: {result.returncode}). Konsolu kontrol edin."

    except subprocess.TimeoutExpired:
        error_message = f"'{rpa_path.name}' çıkarma işlemi çok uzun sürdü (>5 dakika)."
        logger.error(error_message)
        return False, error_message
    except FileNotFoundError:
        error_message = f"'{command[0]}' komutu bulunamadı."
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"'{rpa_path.name}' için beklenmeyen hata: {e}"
        logger.error(error_message)
        return False, error_message


def _decompile_single_rpyc(rpyc_path: Path, force_decompile: bool = False) -> Tuple[bool, str]:
    """Decompile a single RPYC file."""
    if not UNRPYC_AVAILABLE:
        return False, "unrpyc dekompile betiği bulunamadı."

    rpy_path = rpyc_path.with_suffix(".rpy")

    if not force_decompile and rpy_path.exists():
        return True, f"'{rpyc_path.name}' zaten dekompile edilmiş ('{rpy_path.name}' bulundu)."

    logger.info(f"runpy ile dekompilasyon deneniyor: {rpyc_path} (klasör: {rpyc_path.parent})")
    logger.info(f"runpy ile dekompilasyon deneniyor: {rpyc_path} (klasör: {rpyc_path.parent})")

    args_for_unrpyc = [
        str(UNRPYC_SCRIPT_PATH), 
        str(rpyc_path),         
        "--clobber"             
    ]

    original_argv = sys.argv
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    redirected_stdout = io.StringIO()
    redirected_stderr = io.StringIO()
    exit_code = 0
    runpy_error = None
    original_cwd = os.getcwd()
    rpyc_dir = rpyc_path.parent

    unrpyc_lib_path_str = str(UNRPYC_LIB_DIR.resolve()) 
    path_added = False
    if unrpyc_lib_path_str not in sys.path:
        sys.path.insert(0, unrpyc_lib_path_str) 
        path_added = True
        logger.debug(f"sys.path'e geçici olarak eklendi: {unrpyc_lib_path_str}")

    os.chdir(str(rpyc_dir))
    logger.debug(f"CWD geçici olarak değiştirildi: {rpyc_dir}")

    try:
        sys.argv = args_for_unrpyc
        sys.stdout = redirected_stdout
        sys.stderr = redirected_stderr

        logger.debug(f"runpy.run_path('{str(UNRPYC_SCRIPT_PATH)}') çalıştırılıyor, argv: {sys.argv}")
        runpy.run_path(str(UNRPYC_SCRIPT_PATH), run_name='__main__')

    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
        logger.debug(f"runpy SystemExit ile sonlandı, kod: {exit_code}")
    except Exception as e:
        exit_code = 1
        runpy_error = e
        logger.error(f"{rpyc_path.name} için runpy çalıştırılırken istisna: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if path_added and unrpyc_lib_path_str in sys.path:
            try:
                 sys.path.remove(unrpyc_lib_path_str)
                 logger.debug(f"sys.path'ten kaldırıldı: {unrpyc_lib_path_str}")
            except ValueError: 
                 logger.warning(f"sys.path'ten kaldırılamadı: {unrpyc_lib_path_str}")

        sys.argv = original_argv
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        os.chdir(original_cwd)
        logger.debug(f"CWD geri yüklendi: {original_cwd}")

    stdout_content = redirected_stdout.getvalue()
    stderr_content = redirected_stderr.getvalue()
    if stdout_content: logger.debug(f"[runpy stdout] {stdout_content.strip()}")
    if stderr_content: logger.debug(f"[runpy stderr] {stderr_content.strip()}")

    if exit_code == 0 and runpy_error is None:
        if rpy_path.exists():
             logger.info(f"{rpyc_path.name} başarıyla dekompile edildi -> {rpy_path.name}")
             return True, f"'{rpyc_path.name}' başarıyla dekompile edildi."
        else:
             warning_message = f"runpy '{rpyc_path.name}' için başarılı (Kod 0), ancak {rpy_path.name} bulunamadı. Dosya boş veya sadece python bloğu içeriyor olabilir."
             logger.warning(warning_message)
             return True, warning_message
    else:
        error_detail = stderr_content.strip() if stderr_content else stdout_content.strip()
        if runpy_error: error_detail = f"{error_detail}\nPython İstisnası: {runpy_error}"
        error_message = f"'{rpyc_path.name}' dekompilasyon hatası (Kod: {exit_code}): {error_detail}"
        logger.error(error_message)
        short_error = f"unrpyc(runpy) '{rpyc_path.name}' için hata (Kod: {exit_code}). Konsolu kontrol edin."
        return False, short_error


def prepare_project_files(project_path_str: str, settings: dict) -> dict:
    """Prepare project files by extracting RPA archives and decompiling RPYC files."""
    project_path = Path(project_path_str)

    results = {
        "rpa_processed": 0, "rpa_skipped": 0, "rpa_errors": 0, "rpa_error_details": [],
        "rpyc_processed": 0, "rpyc_skipped": 0, "rpyc_errors": 0, "rpyc_error_details": [],
        "unrpa_available": UNRPA_AVAILABLE, "unrpyc_available": UNRPYC_AVAILABLE,
        "preparation_skipped_by_setting": False 
    }

    if not project_path.is_dir():
        results["error"] = f"Proje yolu bulunamadı veya klasör değil: {project_path_str}"
        return results

    auto_prepare_enabled = settings.get("auto_prepare_project", config.DEFAULT_AUTO_PREPARE_PROJECT)
    if not auto_prepare_enabled:
        logger.info("Otomatik proje hazırlama ayarlarda kapalı.")
        results["preparation_skipped_by_setting"] = True
        return results 

    logger.info("-" * 20)
    logger.info(f"Proje dosya hazırlama başlıyor: {project_path}")

    # Process RPA files
    rpa_files = list(project_path.rglob("*.rpa"))
    if rpa_files:
        if UNRPA_AVAILABLE:
            logger.info(f"{len(rpa_files)} *.rpa dosyası bulundu. İşleniyor...")
            for rpa_file in rpa_files:
                success, message = _extract_single_rpa(rpa_file, project_path)
                if "daha önce çıkarılmış" in message:
                    results["rpa_skipped"] += 1
                elif success:
                    results["rpa_processed"] += 1
                else:
                    results["rpa_errors"] += 1
                    results["rpa_error_details"].append(f"{rpa_file.name}: {message}")
        else:
            logger.warning(f"{len(rpa_files)} *.rpa dosyası bulundu, ancak unrpa kullanılamıyor. Çıkarma atlandı.")
            results["rpa_errors"] = len(rpa_files) 
            results["rpa_error_details"].append("unrpa kütüphanesi kurulu değil.")

    # Process RPYC files
    rpyc_files = [p for p in project_path.rglob("*.rpyc") if "__pycache__" not in p.parts]

    if rpyc_files:
        if UNRPYC_AVAILABLE:
            logger.info(f"{len(rpyc_files)} *.rpyc dosyası (__pycache__ dışında) bulundu. İşleniyor...")
            for rpyc_file in rpyc_files:
                success, message = _decompile_single_rpyc(rpyc_file)
                if "zaten dekompile edilmiş" in message:
                    results["rpyc_skipped"] += 1
                elif success:
                    results["rpyc_processed"] += 1
                else:
                    results["rpyc_errors"] += 1
                    results["rpyc_error_details"].append(f"{rpyc_file.name}: {message}")
        else:
            logger.warning(f"{len(rpyc_files)} *.rpyc dosyası bulundu, ancak dekompile betiği bulunamadı. Dekompilasyon atlandı.")
            results["rpyc_errors"] = len(rpyc_files) 
            results["rpyc_error_details"].append(f"{UNRPYC_SCRIPT_PATH.name} betiği bulunamadı.")

    logger.info("Proje dosya hazırlama tamamlandı.")
    logger.info(f"  RPA: işlendi={results['rpa_processed']}, atlandı={results['rpa_skipped']}, hata={results['rpa_errors']}")
    logger.info(f"  RPYC: işlendi={results['rpyc_processed']}, atlandı={results['rpyc_skipped']}, hata={results['rpyc_errors']}")
    logger.info("-" * 20)
    return results


if __name__ == "__main__":
    test_project_dir = input("Test için Ren'Py proje klasör yolunu girin: ")
    if Path(test_project_dir).is_dir():
        prep_results = prepare_project_files(test_project_dir, {"auto_prepare_project": True})
        logger.info("\nHazırlık Sonuçları:")
        logger.info(f"  unrpa kullanılabilir: {prep_results['unrpa_available']}")
        logger.info(f"  unrpyc kullanılabilir: {prep_results['unrpyc_available']}")
        logger.info(f"  RPA İşlendi: {prep_results['rpa_processed']}")
        logger.info(f"  RPA Atlandı: {prep_results['rpa_skipped']}")
        logger.info(f"  RPA Hata: {prep_results['rpa_errors']}")
        if prep_results['rpa_error_details']:
            logger.error("    RPA Hata Detayları:")
            for detail in prep_results['rpa_error_details']: logger.error(f"      - {detail}")
        logger.info(f"  RPYC İşlendi: {prep_results['rpyc_processed']}")
        logger.info(f"  RPYC Atlandı: {prep_results['rpyc_skipped']}")
        logger.info(f"  RPYC Hata: {prep_results['rpyc_errors']}")
        if prep_results['rpyc_error_details']:
            logger.error("    RPYC Hata Detayları:")
            for detail in prep_results['rpyc_error_details']: logger.error(f"      - {detail}")
    else:
        logger.error("Belirtilen yol bir klasör değil.")