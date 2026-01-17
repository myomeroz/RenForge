
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.qc_engine import check_quality

def run_test_cases():
    test_cases = [
        {
            "id": 1,
            "desc": "Missing Placeholder",
            "source": "Hello [player]!",
            "target": "Merhaba!",
            "expected_code": "PLACEHOLDER_MISSING",
            "expected_severity": "ERROR"  # Assuming PLACEHOLDER_MISSING is ERROR
        },
        {
            "id": 2,
            "desc": "Unchanged (Casefold)",
            "source": "  Foo Bar  ",
            "target": "Foo   bar",
            "expected_code": "UNCHANGED",
            "expected_severity": "WARN"
        },
        {
            "id": 3,
            "desc": "Empty Translation",
            "source": "X",
            "target": "",
            "expected_code": "EMPTY_TRANSLATION",
            "expected_severity": "ERROR"
        },
        {
            "id": 4,
            "desc": "Length Anomaly (Long)",
            "source": "Very short text",
            "target": "This translation is extremely long and definitely an anomaly.",
            "expected_code": "LENGTH_LONG",
            "expected_severity": "WARN"
        },
        {
            "id": 5,
            "desc": "Escape Mismatch (Newline)",
            "source": "Line 1\\nLine 2",
            "target": "Line 1 Line 2",
            "expected_code": "ESCAPE_MISMATCH",
            "expected_severity": "WARN"
        }
    ]
    
    print("=== QC Engine Verification ===\n")
    
    all_passed = True
    
    for case in test_cases:
        print(f"Test Case {case['id']}: {case['desc']}")
        print(f"  Source: '{case['source']}'")
        print(f"  Target: '{case['target']}'")
        
        result = check_quality(case['source'], case['target'])
        
        passed = False
        message = ""
        
        issues = check_quality(case['source'], case['target'])
        
        passed = False
        message = ""
        
        if issues:
            # Check if expected code is present
            codes = [i.code for i in issues]
            if case['expected_code'] in codes:
                passed = True
                message = f"PASS - Found {case['expected_code']}"
            else:
                message = f"FAIL - Expected {case['expected_code']}, got {codes}"
        else:
             if case['expected_code'] == "NONE": # If we had negative tests
                 passed = True
             else:
                 message = f"FAIL - Expected issue {case['expected_code']}, got Valid"
        
        print(f"  Result: {message}")
        if not passed:
            all_passed = False
        print("-" * 40)
        
    if all_passed:
        print("\nAll QC test cases PASSED.")
        sys.exit(0)
    else:
        print("\nSome QC test cases FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_test_cases()
