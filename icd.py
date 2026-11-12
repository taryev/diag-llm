import os

import requests
import streamlit as st

ICD_TOKEN_ENDPOINT = os.getenv(
    "ICD_TOKEN_ENDPOINT", "https://icdaccessmanagement.who.int/connect/token"
)
ICD_CLIENT_ID = os.getenv("ICD_CLIENT_ID", "put-client-id-in-env-file")
ICD_CLIENT_SECRET = os.getenv("ICD_CLIENT_SECRET", "put-client-secret-in-en-file")


@st.cache_data(ttl=3000)
def get_icd_api_token() -> str:
    token_res = requests.post(
        ICD_TOKEN_ENDPOINT,
        data={"grant_type": "client_credentials", "scope": "icdapi_access"},
        auth=(ICD_CLIENT_ID, ICD_CLIENT_SECRET),
        timeout=10,
    )
    if not token_res.ok:
        raise RuntimeError(f"{token_res.status_code}: {token_res.text}")
    return token_res.json()["access_token"]


def get_icd_from_autocode(diagnostic_text: str) -> dict:
    """Looks up candidate ICD-11 code for ONE diagnosis written in
    standard English clinical terminology. Returns the candidate
    code found by the ICD autocode API, or an error.

    Must return code, title and URI to comply with the ICD license.
    """

    token = get_icd_api_token()

    response = requests.get(
        "https://id.who.int/icd/release/11/2024-01/mms/autocode",
        params={"searchText": diagnostic_text},
        headers={
            "Authorization": f"Bearer {token}",
            "API-Version": "v2",
            "Accept-Language": "en",
            "Accept": "application/json",
        },
        timeout=10,
    )
    try:
        response.raise_for_status()

        code = response.json().get("theCode")
        uri = response.json().get("linearizationURI")
        title = get_icd_title(uri)

    except requests.HTTPError as e:
        return {"error": f"ICD API Unavailable: {e}"}

    except requests.JSONDecodeError:
        return {"error": "Unable to decode JSON"}

    except AttributeError:
        return {"error": "Unable to find attribute"}

    return {"code": code, "title": title, "uri": uri}


def get_icd_title(uri: str):
    token = get_icd_api_token()

    response = requests.get(
        uri,
        headers={
            "Authorization": f"Bearer {token}",
            "API-Version": "v2",
            "Accept-Language": "en",
            "Accept": "application/json",
        },
        timeout=10,
    )
    response.raise_for_status()

    title = response.json().get("title").get("@value")

    return title
