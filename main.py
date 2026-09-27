from pprint import pprint

from drone_pricing.example_data import get_example_data
from drone_pricing.data_structure import Submission
from drone_pricing.pricing import price_submission


def main():
    submission = price_submission(Submission.from_dict(get_example_data()))
    pprint(submission.to_dict(), sort_dicts=False)
    for warning in submission.warnings:
        print(f"WARNING: {warning}")


if __name__ == "__main__":
    main()
