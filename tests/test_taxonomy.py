from email.message import Message
from unittest.mock import patch

import pytest

from taxonomy import EXPECTED_ROLE_COUNT, Taxonomy, TaxonomyFetchError, fetch_official_taxonomy


ROLES = [
    "Conceptualization", "Data curation", "Formal analysis", "Funding acquisition", "Investigation",
    "Methodology", "Project administration", "Resources", "Software", "Supervision", "Validation",
    "Visualization", "Writing – original draft", "Writing – review & editing",
]


def official_html() -> str:
    return "<html><body>" + "".join(
        f'<p><a href="https://credit.niso.org/contributor-roles/{index}/">{role}</a> – Description {index}.</p>'
        for index, role in enumerate(ROLES)
    ) + "</body></html>"


class Response:
    status = 200

    def __init__(self, body: str) -> None:
        self.body = body.encode()
        self.headers = Message()
        self.headers.set_param("charset", "utf-8", header="content-type")

    def read(self) -> bytes:
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_fetches_roles_and_descriptions_from_mocked_niso_response() -> None:
    with patch("taxonomy.urlopen", return_value=Response(official_html())):
        taxonomy = fetch_official_taxonomy()
    assert len(taxonomy.roles) == EXPECTED_ROLE_COUNT
    assert taxonomy.roles[0] == "Conceptualization"
    assert taxonomy.descriptions["Writing – review & editing"] == "Description 13."


def test_invalid_response_is_reported() -> None:
    with patch("taxonomy.urlopen", return_value=Response("<p>not a taxonomy</p>")):
        with pytest.raises(TaxonomyFetchError, match="Unable to retrieve valid"):
            fetch_official_taxonomy()


def test_network_error_is_reported() -> None:
    with patch("taxonomy.urlopen", side_effect=OSError("offline")):
        with pytest.raises(TaxonomyFetchError, match="offline"):
            fetch_official_taxonomy()


@pytest.mark.parametrize(
    ("roles", "descriptions", "message"),
    [
        (ROLES[:-1], {role: "description" for role in ROLES[:-1]}, "Expected 14"),
        ([*ROLES[:-1], ROLES[-2]], {role: "description" for role in ROLES}, "duplicate"),
        ([*ROLES[:-1], "Not a CRediT role"], {role: "description" for role in [*ROLES[:-1], "Not a CRediT role"]}, "invalid role"),
        (ROLES, {role: "" for role in ROLES}, "non-empty description"),
    ],
)
def test_taxonomy_validation_rejects_missing_duplicate_invalid_roles_and_descriptions(roles, descriptions, message) -> None:
    with pytest.raises(ValueError, match=message):
        Taxonomy(tuple(roles), descriptions).validate()


@pytest.mark.parametrize(
    "html",
    [
        "<html><p><a href='https://credit.niso.org/contributor-roles/0/'>Conceptualization</a>",
        "<p><a href='https://credit.niso.org/contributor-roles/0/'>Conceptualization</a> – </p>",
    ],
)
def test_malformed_or_missing_description_response_is_reported(html: str) -> None:
    with patch("taxonomy.urlopen", return_value=Response(html)):
        with pytest.raises(TaxonomyFetchError, match="Unable to retrieve valid"):
            fetch_official_taxonomy()
