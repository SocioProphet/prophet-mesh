"""Tests for the prophet-workspace → PKG adapters (real record shapes)."""
from __future__ import annotations

from prophet_mesh.pkg import load_spec, seed_graph, validate
from prophet_mesh.pkg_workspace import (
    adapt_contact,
    adapt_event,
    adapt_message,
    ingest_workspace,
)

SPEC = load_spec()

CONTACT_MOM = {
    "schemaVersion": "v0.1", "contactId": "c-mom", "accountRef": "acct-1",
    "contactClass": "person", "displayName": "Mom", "givenName": "Ada",
    "labels": ["family"], "sourceAdapter": "google_contacts",
    "externalId": "people/c123", "updatedAt": "2026-06-28T14:22:00Z",
    "socialProfiles": [{"platform": "linkedin", "handle": "ada", "url": "https://linkedin.com/in/ada"}],
}
CONTACT_JAMIE = {
    "schemaVersion": "v0.1", "contactId": "c-jamie", "accountRef": "acct-1",
    "contactClass": "person", "displayName": "Jamie", "organizationRef": "Acme Music",
    "labels": ["bandmate"], "sourceAdapter": "carddav", "updatedAt": "2026-06-01T00:00:00Z",
}
EVENT_PRACTICE = {
    "schemaVersion": "v0.1", "eventId": "e-practice", "calendarRef": "cal-1",
    "title": "Band practice", "status": "confirmed", "organizerRef": "me@x.com",
    "start": {"dateTime": "2026-07-15T18:00:00"}, "end": {"dateTime": "2026-07-15T20:00:00"},
    "sourceAdapter": "google_calendar", "updatedAt": "2026-07-10T00:00:00Z",
    "attendees": [
        {"email": "me@x.com", "isSelf": True, "isOrganizer": True},
        {"email": "jamie@x.com", "name": "Jamie", "contactRef": "c-jamie", "responseStatus": "accepted"},
    ],
}
MAIL_FROM_JAMIE = {
    "schemaVersion": "v0.1", "messageId": "m-1", "accountRef": "acct-mail-1", "threadId": "t-1",
    "from": {"email": "jamie@x.com", "name": "Jamie", "contactRef": "c-jamie"},
    "to": [{"email": "me@x.com", "isSelf": True}], "subject": "setlist",
    "receivedAt": "2026-06-28T09:45:00Z", "routingState": "imbox", "inboxSlot": "primary",
}
ARTIFACT_SETLIST = {
    "schemaVersion": "v0.1", "artifactId": "a-setlist", "workroomId": "wr-band",
    "artifactType": "document", "title": "Setlist", "format": "docx", "status": "approved",
    "createdAt": "2026-06-20T00:00:00Z",
}


def test_contact_family_hint_becomes_relatedTo():
    g = seed_graph()
    nid = adapt_contact(g, CONTACT_MOM)
    rel = {(e.src, e.dst): e.rel for e in g.edges}[("self", nid)]
    assert rel == "relatedTo"
    # sourceAdapter flows into provenance; social profile is a reference-only link
    n = g.nodes[nid]
    assert n.provenance.source == "workspace:contacts:google_contacts"
    assert n.provenance.captured_at == "2026-06-28T14:22:00Z"
    assert n.external[0].target_kg == "social_network"
    assert validate(g, SPEC) == []


def test_contact_with_org_makes_worksAt():
    g = seed_graph()
    nid = adapt_contact(g, CONTACT_JAMIE)
    rels = {(e.src, e.dst): e.rel for e in g.edges}
    assert rels[("self", nid)] == "knows"
    assert rels[(nid, "org:Acme Music")] == "worksAt"
    assert g.nodes["org:Acme Music"].type == "Organization"
    assert validate(g, SPEC) == []


def test_event_attendee_with_contactRef_participates():
    g = seed_graph()
    adapt_event(g, EVENT_PRACTICE)
    rels = {(e.src, e.dst): e.rel for e in g.edges}
    assert rels[("self", "event:e-practice")] == "participatedIn"
    assert rels[("person:c-jamie", "event:e-practice")] == "participatedIn"  # attendee, not self
    assert validate(g, SPEC) == []


def test_mail_from_contact_is_communicatedWith():
    g = seed_graph()
    pid = adapt_message(g, MAIL_FROM_JAMIE)
    assert pid == "person:c-jamie"
    e = g.edges[-1]
    assert (e.src, e.dst, e.rel) == ("self", "person:c-jamie", "communicatedWith")
    assert e.provenance.captured_at == "2026-06-28T09:45:00Z"  # receivedAt
    assert validate(g, SPEC) == []


def test_full_workspace_export_ingests_and_validates():
    g = seed_graph()
    ingest_workspace(
        g,
        contacts=[CONTACT_MOM, CONTACT_JAMIE],
        events=[EVENT_PRACTICE],
        messages=[MAIL_FROM_JAMIE],
        artifacts=[ARTIFACT_SETLIST],
    )
    assert validate(g, SPEC) == []
    types = sorted({n.type for n in g.nodes.values()})
    assert types == ["Document", "Event", "Organization", "Person", "Self"]
    # mail resolved onto the SAME Jamie node created from contacts (no dup)
    assert sum(1 for n in g.nodes.values() if n.label == "Jamie") == 1
