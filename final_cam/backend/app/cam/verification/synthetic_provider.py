from __future__ import annotations

LACTOSE_CIN = "L15201GJ1991PLC015186"


def lactose_company_master():
    return {
        "_meta": {
            "provider": "Synthetic POC fallback",
            "synthetic": True,
            "verified": False,
            "reason": "Used only when FileSure is unavailable or does not return the requested field.",
        },
        "cin": LACTOSE_CIN,
        "company": "LACTOSE (INDIA) LIMITED",
        "data": {
            "masterData": {
                "companyData": {
                    "cin": LACTOSE_CIN,
                    "companyName": "LACTOSE (INDIA) LIMITED",
                    "companyStatus": "Active",
                    "dateOfIncorporation": "11-Mar-1991",
                    "authorisedCapital": 150000000,
                    "paidupCapital": 125890000,
                    "companyType": "Public Limited Company",
                    "MCAMDSCompanyAddress": [
                        {
                            "addressLine1": "Survey No. 5, 6 & 7A, Village Poicha (Rania)",
                            "addressLine2": "Taluka Savli",
                            "city": "Vadodara",
                            "state": "Gujarat",
                            "pinCode": "391780",
                        }
                    ],
                },
                "directorData": [
                    {"name": "Atul Maheshwari", "designation": "Managing Director", "DIN": "00255202"},
                    {"name": "Sangita Maheshwari", "designation": "Whole Time Director & CFO", "DIN": "00369898"},
                ],
            }
        },
        "poc_additional_verification": {
            "banking_conduct": {
                "source": "synthetic_poc",
                "account_status": "Standard",
                "sma_status": "None",
                "overdue_days": 0,
                "interest_servicing": "Regular",
            },
            "credit_bureau": {
                "source": "synthetic_poc",
                "company_score": "CMR-3",
                "wilful_defaulter": False,
                "suit_filed": False,
            },
            "gst": {
                "source": "synthetic_poc",
                "registration_status": "Active",
                "filing_status": "Regular - test assumption",
            },
            "collateral": {
                "source": "synthetic_poc",
                "title_status": "Clear - test assumption",
                "valuation_status": "Available - test assumption",
            },
        },
    }
