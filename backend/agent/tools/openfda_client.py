"""
OpenFDA Drug Adverse Events Client.

Queries the FDA Adverse Event Reporting System (FAERS) API for real-world
pediatric adverse event reports for specified medications.

Includes 5.0s timeout and optional API key support.
"""

import logging
from typing import Any, Optional
import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENFDA_BASE_URL = "https://api.fda.gov/drug/event.json"
DATA_DISCLAIMER = (
    "OpenFDA data is sourced from post-marketing voluntary adverse event reports "
    "(FAERS). Reports do not establish a causal relationship between the drug and the event."
)


class OpenFDAClient:
    """
    Async HTTP client for OpenFDA Drug Adverse Event API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
    ) -> None:
        self.api_key = api_key or getattr(settings, "openfda_api_key", None)
        self.timeout = timeout

    async def lookup_pediatric_adverse_events(self, drug_name: str) -> dict[str, Any]:
        """
        Query OpenFDA for pediatric adverse reaction counts for a medication.

        Args:
            drug_name: Generic or brand medication name (e.g. Tylenol, ibuprofen).

        Returns:
            Dict containing drug_name, total_pediatric_reports, top_reactions list, and disclaimer.
        """
        clean_drug = drug_name.strip().strip("'\"").lower()
        if not clean_drug:
            return {
                "drug_name": drug_name,
                "error": "Empty drug name provided.",
                "top_reactions": [],
                "data_disclaimer": DATA_DISCLAIMER,
            }

        # Build search query for openfda brand_name OR generic_name
        search_query = (
            f'(patient.drug.openfda.brand_name:"{clean_drug}" OR patient.drug.openfda.generic_name:"{clean_drug}")'
            f' AND patient.patientonsetageunit:802 AND patient.patientonsetage:[0 TO 5]'
        )

        params: dict[str, str] = {
            "search": search_query,
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": "5",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        logger.info("Calling OpenFDA API for drug=%r with timeout=%.1fs", clean_drug, self.timeout)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(OPENFDA_BASE_URL, params=params)

            if response.status_code == 404:
                logger.info("OpenFDA returned 404 (no reports found for %r)", clean_drug)
                return {
                    "drug_name": clean_drug,
                    "total_pediatric_reports": 0,
                    "top_reactions": [],
                    "data_disclaimer": DATA_DISCLAIMER,
                }

            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            top_reactions = []
            total_reports = 0

            for item in results[:5]:
                term = item.get("term", "Unknown")
                count = item.get("count", 0)
                total_reports += count
                top_reactions.append({"reaction": term, "count": count})

            return {
                "drug_name": clean_drug,
                "total_pediatric_reports": total_reports,
                "top_reactions": top_reactions,
                "data_disclaimer": DATA_DISCLAIMER,
            }

        except httpx.TimeoutException:
            logger.warning("OpenFDA API request timed out after %.1fs for drug=%r", self.timeout, clean_drug)
            return {
                "drug_name": clean_drug,
                "error": f"OpenFDA request timed out ({self.timeout}s)",
                "top_reactions": [],
                "data_disclaimer": DATA_DISCLAIMER,
            }
        except Exception as exc:
            logger.warning("OpenFDA API lookup failed for drug=%r: %s", clean_drug, exc)
            return {
                "drug_name": clean_drug,
                "error": str(exc),
                "top_reactions": [],
                "data_disclaimer": DATA_DISCLAIMER,
            }
