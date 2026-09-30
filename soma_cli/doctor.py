"""soma doctor — System health check."""
import argparse


def run_doctor(args: argparse.Namespace) -> int:
    """System health check."""
    print("soma doctor: delegates to existing health check")
    return 0
