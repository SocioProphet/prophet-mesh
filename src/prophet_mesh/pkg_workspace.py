"""prophet-workspace → PKG adapters.

Maps real prophet-workspace records into the Personal Knowledge Graph, one
adapter per contract:

    contact.schema.json        → Person (+ worksAt Organization, social sameAs)
    calendar-event.schema.json → Event + participatedIn (Self + attendees)
    mail-message.schema.json   → communicatedWith (Self ↔ the correspondent)
    office-artifact.schema.json→ Document + authored

Every emitted node/edge carries workspace provenance: source =
``workspace:<surface>:<adapter>``, method ``ingested``, captured_at from the
record's own timestamp (updatedAt / receivedAt / createdAt). External identities
(socialProfiles) become reference-only links to the social_network KG — never a
data copy. These consume the canonical records; they do not invent shape.
"""
from __future__ import annotations

from typing import Any

from prophet_mesh.pkg import PKG, Edge, ExternalLink, Node, Provenance, link_external

# Contact.labels / groupRefs hints that reclassify knows → relatedTo (family).
FAMILY_HINTS = {
    "family", "mom", "dad", "mother", "father", "sister", "brother",
    "parent", "child", "sibling", "spouse", "wife", "husband", "son", "daughter",
}


def _prov(rec: dict[str, Any], surface: str, when_key: str = "updatedAt") -> Provenance:
    adapter = rec.get("sourceAdapter") or rec.get("accountRef") or rec.get("workroomId") or "unknown"
    captured = rec.get(when_key) or rec.get("createdAt") or ""
    return Provenance(source=f"workspace:{surface}:{adapter}", method="ingested", captured_at=captured)


def _person_id(ref: str) -> str:
    return f"person:{ref}"


# ── contact.schema.json → Person ──────────────────────────────────────────────
def adapt_contact(g: PKG, rec: dict[str, Any]) -> str:
    if rec.get("contactClass") == "organization":
        return adapt_organization(g, rec)
    cid = rec["contactId"]
    nid = _person_id(cid)
    label = rec.get("displayName") or " ".join(
        p for p in (rec.get("givenName"), rec.get("familyName")) if p
    ) or cid
    prov = _prov(rec, "contacts")
    g.add_node(Node(id=nid, type="Person", label=label, provenance=prov))

    hints = {h.lower() for h in (rec.get("labels") or [])} | {h.lower() for h in (rec.get("groupRefs") or [])}
    rel = "relatedTo" if hints & FAMILY_HINTS else "knows"
    g.add_edge(Edge(src=g.self_id, dst=nid, rel=rel, provenance=prov))

    if rec.get("organizationRef"):
        oid = f"org:{rec['organizationRef']}"
        if oid not in g.nodes:
            g.add_node(Node(id=oid, type="Organization", label=rec["organizationRef"], provenance=prov))
        g.add_edge(Edge(src=nid, dst=oid, rel="worksAt", provenance=prov))

    for sp in rec.get("socialProfiles") or []:
        target = sp.get("url") or f"{sp.get('platform')}:{sp.get('handle')}"
        link_external(g, nid, ExternalLink(
            target_kg="social_network", target_id=target,
            confidence=0.6, trust_class="platform",
        ))
    return nid


def adapt_organization(g: PKG, rec: dict[str, Any]) -> str:
    oid = f"org:{rec['contactId']}"
    prov = _prov(rec, "contacts")
    g.add_node(Node(id=oid, type="Organization", label=rec.get("displayName") or rec["contactId"], provenance=prov))
    return oid


# ── calendar-event.schema.json → Event + participatedIn ───────────────────────
def adapt_event(g: PKG, rec: dict[str, Any]) -> str:
    eid = rec["eventId"]
    nid = f"event:{eid}"
    prov = _prov(rec, "calendar")
    g.add_node(Node(id=nid, type="Event", label=rec.get("title") or eid, provenance=prov))
    g.add_edge(Edge(src=g.self_id, dst=nid, rel="participatedIn", provenance=prov))

    for att in rec.get("attendees") or []:
        if att.get("isSelf"):
            continue
        cref = att.get("contactRef")
        if not cref:
            continue
        pid = _person_id(cref)
        if pid not in g.nodes:
            g.add_node(Node(id=pid, type="Person", label=att.get("name") or cref, provenance=prov))
        g.add_edge(Edge(src=pid, dst=nid, rel="participatedIn", provenance=prov))
    return nid


# ── mail-message.schema.json → communicatedWith ───────────────────────────────
def adapt_message(g: PKG, rec: dict[str, Any]) -> str | None:
    """A message → a communicatedWith edge Self↔correspondent (the `from` party)."""
    prov = _prov(rec, "mail", when_key="receivedAt")
    frm = rec.get("from") or {}
    if frm.get("isSelf"):
        return None  # outbound; the correspondent is on `to` — kept simple for now
    cref = frm.get("contactRef")
    if cref:
        pid = _person_id(cref)
        label = frm.get("name") or cref
    else:
        email = frm.get("email", "unknown")
        pid = _person_id(f"email:{email}")
        label = frm.get("name") or email
    if pid not in g.nodes:
        g.add_node(Node(id=pid, type="Person", label=label, provenance=prov))
    g.add_edge(Edge(src=g.self_id, dst=pid, rel="communicatedWith", provenance=prov))
    return pid


# ── office-artifact.schema.json → Document + authored ─────────────────────────
def adapt_artifact(g: PKG, rec: dict[str, Any]) -> str:
    aid = rec["artifactId"]
    nid = f"doc:{aid}"
    prov = _prov(rec, "office", when_key="createdAt")
    g.add_node(Node(id=nid, type="Document", label=rec.get("title") or aid, provenance=prov))
    g.add_edge(Edge(src=g.self_id, dst=nid, rel="authored", provenance=prov))
    return nid


# ── batch ingest ──────────────────────────────────────────────────────────────
def ingest_workspace(
    g: PKG,
    contacts: list[dict] | None = None,
    events: list[dict] | None = None,
    messages: list[dict] | None = None,
    artifacts: list[dict] | None = None,
) -> PKG:
    """Ingest whole workspace exports in dependency order (people first so mail/
    calendar edges resolve to existing Person nodes)."""
    for rec in contacts or []:
        adapt_contact(g, rec)
    for rec in artifacts or []:
        adapt_artifact(g, rec)
    for rec in events or []:
        adapt_event(g, rec)
    for rec in messages or []:
        adapt_message(g, rec)
    return g
