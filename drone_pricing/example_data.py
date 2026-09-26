"""Example inputs from the spreadsheet.

Same layout as the starter code, with the missing TPL limits/excesses and the
third drone's serial number (CCC-333) taken from the xlsm. Output placeholders
are omitted: the model creates and fills them.
"""


def get_example_data():
    return {
        "insured": "Drones R Us",
        "underwriter": "Michael",
        "broker": "AON",
        "brokerage": 0.3,
        "max_drones_in_air": 2,
        "drones": [
            {
                "serial_number": "AAA-111",
                "value": 10000,
                "weight": "0 - 5kg",
                "has_detachable_camera": True,
                "tpl_limit": 1_000_000,
                "tpl_excess": 0,
            },
            {
                "serial_number": "BBB-222",
                "value": 12000,
                "weight": "10 - 20kg",
                "has_detachable_camera": False,
                "tpl_limit": 4_000_000,
                "tpl_excess": 1_000_000,
            },
            {
                "serial_number": "CCC-333",
                "value": 15000,
                "weight": "5 - 10kg",
                "has_detachable_camera": True,
                "tpl_limit": 5_000_000,
                "tpl_excess": 5_000_000,
            },
        ],
        "detachable_cameras": [
            {"serial_number": "ZZZ-999", "value": 5000},
            {"serial_number": "YYY-888", "value": 2500},
            {"serial_number": "XXX-777", "value": 1500},
            {"serial_number": "WWW-666", "value": 2000},
        ],
    }
