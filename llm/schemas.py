from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisResponse(BaseModel):
    class Diagnosis(BaseModel):
        llm_diagnosis: str
        icd_11_code: str | None
        icd_11_text: str | None
        icd_11_uri: str | None

        model_config = ConfigDict(extra="forbid")

    status: Literal["found", "inconclusive"]
    diagnoses: list[Diagnosis] = Field(max_length=10)

    model_config = ConfigDict(extra="forbid")


class ICDAutocodeArgs(BaseModel):
    """
    Arguments for the get_icd_from_autocode() function.
    """

    diagnostic_text: str = Field(
        min_length=1, description="A single diagnosis in English."
    )

    model_config = ConfigDict(extra="forbid")
