#!/usr/bin/env python3
"""Validate log integrity between decision log and trade results."""

import json
import sys
from integration.logging_utils import load_decisions, load_trade_results


def validate_integrity():
    """Validate integrity between decision log and trade results."""
    print("=== LOG INTEGRITY VALIDATION ===")
    
    # Load data
    decisions = load_decisions()
    results = load_trade_results()
    
    print(f"Loaded {len(decisions)} decisions")
    print(f"Loaded {len(results)} trade results")
    
    # Check decision_id uniqueness in decisions
    decision_ids = [d['decision_id'] for d in decisions]
    unique_decision_ids = set(decision_ids)
    
    if len(decision_ids) != len(unique_decision_ids):
        duplicate_count = len(decision_ids) - len(unique_decision_ids)
        print(f"⚠️  WARNING: {duplicate_count} duplicate decision_ids found")
    else:
        print("✅ All decision_ids are unique")
    
    # Index decisions by ID
    decisions_by_id = {d['decision_id']: d for d in decisions}
    
    # Check each result has corresponding decision
    orphan_results = []
    matched_results = []
    
    for result in results:
        result_id = result['decision_id']
        if result_id not in decisions_by_id:
            orphan_results.append(result_id)
        else:
            matched_results.append(result_id)
    
    # Find unmatched decisions (decisions without results)
    result_ids = {r['decision_id'] for r in results}
    unmatched_decisions = []
    
    for decision_id in unique_decision_ids:
        if decision_id not in result_ids:
            unmatched_decisions.append(decision_id)
    
    # Compute metrics
    decisions_total = len(unique_decision_ids)
    results_total = len(results)
    unmatched_count = len(unmatched_decisions) 
    orphan_count = len(orphan_results)
    
    # Report results
    print(f"\n=== INTEGRITY ANALYSIS ===")
    print(f"Total unique decisions: {decisions_total}")
    print(f"Total trade results: {results_total}")
    print(f"Matched results: {len(matched_results)}")
    print(f"Unmatched decisions: {unmatched_count}")
    print(f"Orphan results: {orphan_count}")
    
    if orphan_count > 0:
        print(f"❌ ORPHAN RESULT IDs: {orphan_results}")
    else:
        print("✅ No orphan results")
        
    if unmatched_count > 0:
        print(f"⏳ UNMATCHED DECISION IDs: {unmatched_decisions[:5]}{'...' if unmatched_count > 5 else ''}")
    else:
        print("✅ All decisions have corresponding results")
    
    # Create output JSON
    integrity_json = {
        "decisions_total": decisions_total,
        "results_total": results_total,
        "unmatched_decisions": unmatched_count,
        "orphan_results": orphan_count,
        "integrity_pass": orphan_count == 0,
        "decisions_unique": len(decision_ids) == len(unique_decision_ids)
    }
    
    print(f"\n=== INTEGRITY JSON ===")
    print(json.dumps(integrity_json, indent=2))
    
    # Exit code: 0 only if no orphan results
    return 0 if orphan_count == 0 else 1


def main():
    """Main validation function."""
    try:
        exit_code = validate_integrity()
        sys.exit(exit_code)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 