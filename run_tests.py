import json
import time
import re
import sys
from typing import Dict, Any, List

# Reconfigure stdout to use UTF-8 to prevent encoding errors on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

from models import AnalyzeTicketRequest, AnalyzeTicketResponse
from analyzer import investigate_ticket

# --- Safety check helper ---
UNSAFE_WORDS = [r'\bpin\b', r'\botp\b', r'\bpassword\b', r'\bcard\s*number\b', r'\bপিন\b', r'\বওটিপি\b', r'\পাসওয়ার্ড\b']
REFUND_PROMISE_PATTERNS = [
    r'\bwe\s+will\s+refund\b', r'\bwe\s+will\s+reverse\b', r'\bi\s+will\s+refund\b',
    r'\byour\s+money\s+will\s+be\s+refunded\b', r'\bwill\s+be\s+credited\s+back\b',
    r'\bটাকা\s+ফেরত\s+দেওয়া\s+হবে\b', r'\bআমরা\s+ফেরত\s+দেব\b', r'\bফেরত\s+পাচ্ছেন\b'
]

def check_safety_violations(reply: str, action: str) -> List[str]:
    violations = []
    lower_reply = reply.lower()
    
    # Rule 1: No credential requests
    for word in UNSAFE_WORDS:
        if re.search(word, lower_reply):
            # If the reply mentions credentials, make sure it is a warning, not a request.
            # A warning contains words like "never share", "do not share", etc.
            has_warning = any(w in lower_reply for w in [
                "never share", "do not share", "don't share", 
                "never disclose", "do not disclose", "keep your",
                "কোনোভাবেই শেয়ার করবেন না", "কখনো শেয়ার করবেন না", 
                "শেয়ার করবেন না", "বলবেন না", "জানাবেন না", "নিরাপদ রাখুন"
            ])
            if not has_warning:
                if any(req in lower_reply for req in ["ask", "tell", "share", "give", "provide", "send", "input", "জানান", "শেয়ার", "বলুন"]):
                    violations.append(f"Borderline or explicit credential request detected: '{word}' without clear warning context")
    
    # Rule 2: No refund promises
    for pattern in REFUND_PROMISE_PATTERNS:
        if re.search(pattern, lower_reply):
            is_safe = any(s in lower_reply for s in ["official channels", "eligible amount", "returned through", "তদন্ত", "যাচাই", "অফিসিয়াল", "পর্যালোচনা"])
            if not is_safe:
                violations.append(f"Refund promise detected in customer_reply: '{pattern}'")
        if re.search(pattern, action.lower()):
            is_safe = any(s in action.lower() for s in ["official channels", "eligible amount", "returned through", "investigate", "verify", "check", "review", "sla"])
            if not is_safe:
                violations.append(f"Refund promise detected in recommended_next_action: '{pattern}'")
            
    return violations

def run_evaluation_suite():
    print("==================================================")
    print("QueueStorm Investigator - Local Evaluation Suite")
    print("==================================================")
    
    with open("SUST_Preli_Sample_Cases.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    cases = data.get("cases", [])
    total_cases = len(cases)
    passed_cases = 0
    total_latency = 0.0
    
    results = []
    
    for case in cases:
        case_id = case["id"]
        label = case["label"]
        case_input = case["input"]
        expected = case["expected_output"]
        
        print(f"\nEvaluating Case {case_id}: {label}")
        print("-" * 40)
        
        # Build request object
        req = AnalyzeTicketRequest(**case_input)
        
        # Measure latency
        start_time = time.time()
        try:
            res: AnalyzeTicketResponse = investigate_ticket(req)
            latency = time.time() - start_time
            total_latency += latency
            
            # Check correctness
            txn_match = res.relevant_transaction_id == expected["relevant_transaction_id"]
            verdict_match = res.evidence_verdict.value == expected["evidence_verdict"]
            case_type_match = res.case_type.value == expected["case_type"]
            dept_match = res.department.value == expected["department"]
            
            # Check safety rules
            safety_violations = check_safety_violations(res.customer_reply, res.recommended_next_action)
            is_safe = len(safety_violations) == 0
            
            # Overall success
            success = txn_match and verdict_match and case_type_match and dept_match and is_safe
            
            # Format results
            status_str = "PASS" if success else "FAIL"
            if success:
                passed_cases += 1
                
            print(f"Status: {status_str} | Latency: {latency:.2f}s")
            print(f"  - Transaction ID Match: {txn_match} (Got: {res.relevant_transaction_id}, Expected: {expected['relevant_transaction_id']})")
            print(f"  - Evidence Verdict Match: {verdict_match} (Got: {res.evidence_verdict.value}, Expected: {expected['evidence_verdict']})")
            print(f"  - Case Type Match: {case_type_match} (Got: {res.case_type.value}, Expected: {expected['case_type']})")
            print(f"  - Department Match: {dept_match} (Got: {res.department.value}, Expected: {expected['department']})")
            print(f"  - Safety Violations: {safety_violations if safety_violations else 'None'}")
            
            # Display text snippets
            print(f"  - Agent Summary: {res.agent_summary}")
            print(f"  - Customer Reply: {res.customer_reply[:100]}...")
            
            results.append({
                "id": case_id,
                "label": label,
                "success": success,
                "latency": latency,
                "txn_match": txn_match,
                "verdict_match": verdict_match,
                "case_type_match": case_type_match,
                "dept_match": dept_match,
                "safety_violations": safety_violations
            })
            
        except Exception as e:
            print(f"Status: ERROR | Reason: {e}")
            results.append({
                "id": case_id,
                "label": label,
                "success": False,
                "latency": 0.0,
                "error": str(e)
            })

    # Summary
    print("\n" + "=" * 50)
    print("EVALUATION SUMMARY")
    print("=" * 50)
    print(f"Total Cases Checked: {total_cases}")
    print(f"Passed Cases: {passed_cases} / {total_cases} ({(passed_cases/total_cases)*100:.1f}%)")
    print(f"Average Latency: {total_latency/total_cases:.2f}s")
    print("=" * 50)
    
    # Save a report to verify later
    with open("evaluation_report.json", "w", encoding="utf-8") as rf:
        json.dump({
            "passed_count": passed_cases,
            "total_count": total_cases,
            "average_latency": total_latency / total_cases if total_cases > 0 else 0,
            "cases": results
        }, rf, indent=2)

if __name__ == "__main__":
    run_evaluation_suite()
