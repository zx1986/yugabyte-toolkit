import sys
import argparse

from .log_analyzer import analyze_log
from .rule_parser import parse_rules


def main():
    parser = argparse.ArgumentParser(description="YugabyteDB Insert Trace Verifier")
    parser.add_argument("--rules", required=True, help="Path to trace_rules.yaml")
    parser.add_argument("--log-file", required=True, help="Path to trace.log to analyze")
    args = parser.parse_args()

    config = parse_rules(args.rules)
    print(f"=== Verifying: {config.name} ===")
    print(config.description)
    print("-" * 40)

    results = analyze_log(args.log_file, config.stages)

    all_passed = True
    for stage in config.stages:
        passed = results[stage.id]
        if passed:
            print(f"[✔] {stage.name}")
        elif stage.required:
            print(f"[✖] {stage.name} (Missing)")
            all_passed = False
        else:
            print(f"[-] {stage.name} (Missing, Optional)")

    print("-" * 40)
    if not all_passed:
        print("❌ VERIFICATION FAILED: One or more required stages were missing.")
        sys.exit(1)

    print("✅ VERIFICATION PASSED: All expected stages recorded.")
    sys.exit(0)


if __name__ == "__main__":
    main()
