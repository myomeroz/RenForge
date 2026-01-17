
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from core.error_explainer import ErrorExplainer

def test_auth_error():
    print("Testing AUTH error...")
    errs = ["401 Unauthorized", "API key not valid"]
    summary = ErrorExplainer.analyze(errs)
    assert summary['category'] == "AUTH"
    assert "Kimlik Doğrulama" in summary['title']
    print("✅ AUTH passed")

def test_rate_limit_error():
    print("Testing RATE_LIMIT error...")
    errs = ["429 Too Many Requests", "Quota exceeded for gemini"]
    summary = ErrorExplainer.analyze(errs)
    assert summary['category'] == "RATE_LIMIT"
    assert "Sınırı Aşıldı" in summary['title']
    print("✅ RATE_LIMIT passed")

def test_network_error():
    print("Testing NETWORK error...")
    errs = ["Connection timed out", "Failed to connect to host"]
    summary = ErrorExplainer.analyze(errs)
    assert summary['category'] == "NETWORK"
    assert "Ağ Bağlantı" in summary['title']
    print("✅ NETWORK passed")

def test_server_error():
    print("Testing SERVER error...")
    errs = ["500 Internal Server Error", "Bad Gateway"]
    summary = ErrorExplainer.analyze(errs)
    assert summary['category'] == "SERVER"
    assert "Sunucu Hatası" in summary['title']
    print("✅ SERVER passed")

def test_complex_error():
    print("Testing Complex error priority...")
    # Auth should beat unknown
    errs = ["Unknown error occurred", "401 Unauthorized detected"]
    summary = ErrorExplainer.analyze(errs)
    assert summary['category'] == "AUTH"
    print("✅ Priority passed")

if __name__ == "__main__":
    try:
        test_auth_error()
        test_rate_limit_error()
        test_network_error()
        test_server_error()
        test_complex_error()
        print("\nAll ErrorExplainer logic tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
