"""Command Line Interface for Soma."""
import argparse
from soma_sdk.governance import Governance

def main():
    parser = argparse.ArgumentParser(description="Soma CLI")
    # Add basic commands if necessary, or just a placeholder for now.
    args = parser.parse_args()
    gov = Governance()
    print("Prism SDK initialized.")

if __name__ == '__main__':
    main()
