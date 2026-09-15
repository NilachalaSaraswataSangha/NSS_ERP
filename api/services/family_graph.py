"""
Family Graph — dynamic relationship computation.

Builds an in-memory graph from ``nss.family_link`` rows and computes
relationship labels relative to any viewer via BFS traversal.

Edge types stored in the DB:
    PARENT_OF  — person_a is parent of person_b (directed)
    SPOUSE_OF  — person_a and person_b are spouses (bidirectional)

Traversal step types (internal):
    UP      — move to a parent   (reverse of PARENT_OF)
    DOWN    — move to a child    (forward  PARENT_OF)
    SPOUSE  — move to a spouse   (either direction of SPOUSE_OF)

The path from viewer → target is a tuple of step types.  A lookup table
maps each path pattern to a gendered relationship label pair
(male_label, female_label).  The target person's gender_code selects
which label to use.

Design decision:  Only direct edges are stored.  Every other kinship
term is derived.  When the Family Head changes, zero data re-entry
is required — the graph is the same, only the viewer changes.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import UUID


# ── Step types ───────────────────────────────────────────────────────────

class Step(Enum):
    UP = "UP"          # to parent
    DOWN = "DOWN"      # to child
    SPOUSE = "SPOUSE"  # to spouse


# ── Path → label mapping ────────────────────────────────────────────────
# Each key is a tuple of Step values representing the shortest path
# from viewer to target.  Value is (male_label, female_label).

PATH_LABELS: dict[tuple[Step, ...], tuple[str, str]] = {
    # ── Generation 0 ──
    (Step.SPOUSE,):
        ("Husband", "Wife"),

    # Sibling: up to shared parent, down to target
    (Step.UP, Step.DOWN):
        ("Brother", "Sister"),

    # Sibling's spouse
    (Step.UP, Step.DOWN, Step.SPOUSE):
        ("Brother-in-Law", "Sister-in-Law"),

    # Spouse's sibling
    (Step.SPOUSE, Step.UP, Step.DOWN):
        ("Brother-in-Law", "Sister-in-Law"),

    # Spouse's sibling's spouse (co-in-law / co-sister-in-law)
    (Step.SPOUSE, Step.UP, Step.DOWN, Step.SPOUSE):
        ("Brother-in-Law", "Sister-in-Law"),

    # ── Generation -1 (parents) ──
    (Step.UP,):
        ("Father", "Mother"),

    # Spouse's parent = parent-in-law
    (Step.SPOUSE, Step.UP):
        ("Father-in-Law", "Mother-in-Law"),

    # Step-parent: parent's spouse (who is not the viewer's other parent)
    (Step.UP, Step.SPOUSE):
        ("Step-Father", "Step-Mother"),

    # Spouse's parent's spouse (parent-in-law via spouse path)
    (Step.SPOUSE, Step.UP, Step.SPOUSE):
        ("Father-in-Law", "Mother-in-Law"),

    # ── Generation -2 (grandparents) ──
    (Step.UP, Step.UP):
        ("Grandfather", "Grandmother"),

    # Spouse's grandparent
    (Step.SPOUSE, Step.UP, Step.UP):
        ("Grandfather-in-Law", "Grandmother-in-Law"),

    # ── Generation +1 (children) ──
    (Step.DOWN,):
        ("Son", "Daughter"),

    # Spouse's child (step-child)
    (Step.SPOUSE, Step.DOWN):
        ("Step-Son", "Step-Daughter"),

    # Child's spouse
    (Step.DOWN, Step.SPOUSE):
        ("Son-in-Law", "Daughter-in-Law"),

    # ── Generation +2 (grandchildren) ──
    (Step.DOWN, Step.DOWN):
        ("Grandson", "Granddaughter"),

    # ── Extended family ──

    # Uncle / Aunt: parent's sibling
    (Step.UP, Step.UP, Step.DOWN):
        ("Uncle", "Aunt"),

    # Uncle/Aunt's spouse
    (Step.UP, Step.UP, Step.DOWN, Step.SPOUSE):
        ("Uncle", "Aunt"),

    # Spouse's uncle/aunt
    (Step.SPOUSE, Step.UP, Step.UP, Step.DOWN):
        ("Uncle-in-Law", "Aunt-in-Law"),

    # Nephew / Niece: sibling's child
    (Step.UP, Step.DOWN, Step.DOWN):
        ("Nephew", "Niece"),

    # Spouse's sibling's child
    (Step.SPOUSE, Step.UP, Step.DOWN, Step.DOWN):
        ("Nephew", "Niece"),

    # Cousin: parent's sibling's child
    (Step.UP, Step.UP, Step.DOWN, Step.DOWN):
        ("Cousin", "Cousin"),

    # Great-grandparent
    (Step.UP, Step.UP, Step.UP):
        ("Great-Grandfather", "Great-Grandmother"),

    # Great-grandchild
    (Step.DOWN, Step.DOWN, Step.DOWN):
        ("Great-Grandson", "Great-Granddaughter"),

    # Grandchild's spouse
    (Step.DOWN, Step.DOWN, Step.SPOUSE):
        ("Grandson-in-Law", "Granddaughter-in-Law"),

    # Sibling's grandchild
    (Step.UP, Step.DOWN, Step.DOWN, Step.DOWN):
        ("Grand-Nephew", "Grand-Niece"),
}


# ── Data structures ──────────────────────────────────────────────────────

@dataclass
class PersonNode:
    """Minimal person info needed for graph traversal."""
    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: Optional[str]
    last_name: Optional[str]
    gender_code: Optional[str]  # MALE / FEMALE


@dataclass
class FamilyGraph:
    """
    Adjacency-list graph of a single family group.

    Edges are stored as (neighbor_pk, step_type) per node.
    """
    persons: dict[UUID, PersonNode] = field(default_factory=dict)
    adjacency: dict[UUID, list[tuple[UUID, Step]]] = field(default_factory=dict)

    def add_person(self, node: PersonNode) -> None:
        self.persons[node.person_pk] = node
        if node.person_pk not in self.adjacency:
            self.adjacency[node.person_pk] = []

    def add_link(self, person_a_pk: UUID, person_b_pk: UUID, link_type: str) -> None:
        """Add a directed link and its reverse."""
        if person_a_pk not in self.adjacency:
            self.adjacency[person_a_pk] = []
        if person_b_pk not in self.adjacency:
            self.adjacency[person_b_pk] = []

        if link_type == "PARENT_OF":
            # A is parent of B → from A's view: DOWN to B; from B's view: UP to A
            self.adjacency[person_a_pk].append((person_b_pk, Step.DOWN))
            self.adjacency[person_b_pk].append((person_a_pk, Step.UP))
        elif link_type == "SPOUSE_OF":
            # Bidirectional
            self.adjacency[person_a_pk].append((person_b_pk, Step.SPOUSE))
            self.adjacency[person_b_pk].append((person_a_pk, Step.SPOUSE))

    def compute_relationships(
        self,
        viewer_pk: UUID,
        max_depth: int = 6,
    ) -> list[dict]:
        """
        BFS from viewer to all reachable persons.

        Returns a list of dicts, one per family member (excluding the
        viewer), each containing person info + computed relationship
        label + generation offset.

        ``max_depth`` caps traversal to avoid runaway in unusual graphs.
        """
        if viewer_pk not in self.adjacency:
            return []

        # BFS: track shortest path (as tuple of Steps) to each node
        visited: dict[UUID, tuple[Step, ...]] = {viewer_pk: ()}
        queue: deque[UUID] = deque([viewer_pk])

        while queue:
            current = queue.popleft()
            current_path = visited[current]

            if len(current_path) >= max_depth:
                continue

            for neighbor_pk, step in self.adjacency[current]:
                if neighbor_pk in visited:
                    continue
                new_path = current_path + (step,)
                visited[neighbor_pk] = new_path
                queue.append(neighbor_pk)

        # Build results
        results: list[dict] = []
        for person_pk, path in visited.items():
            if person_pk == viewer_pk:
                continue  # skip self

            person = self.persons.get(person_pk)
            if person is None:
                continue

            label = self._path_to_label(path, person.gender_code)
            generation = self._path_to_generation(path)

            results.append({
                "person_pk": str(person.person_pk),
                "person_id": person.person_id,
                "first_name": person.first_name,
                "middle_name": person.middle_name,
                "last_name": person.last_name,
                "gender_code": person.gender_code,
                "relationship_label": label,
                "generation": generation,
                "path": [s.value for s in path],
            })

        # Sort by generation, then name
        results.sort(key=lambda r: (r["generation"], r["first_name"] or ""))
        return results

    @staticmethod
    def _path_to_label(path: tuple[Step, ...], gender_code: Optional[str]) -> str:
        """Map a BFS path to a human-readable relationship label."""
        labels = PATH_LABELS.get(path)
        if labels is None:
            return "Relative"

        male_label, female_label = labels
        if gender_code == "MALE":
            return male_label
        elif gender_code == "FEMALE":
            return female_label
        else:
            # Unknown gender — return male form (conventional default)
            return male_label

    @staticmethod
    def _path_to_generation(path: tuple[Step, ...]) -> int:
        """
        Compute generation offset from a path.

        UP = -1, DOWN = +1, SPOUSE = 0.
        """
        gen = 0
        for step in path:
            if step == Step.UP:
                gen -= 1
            elif step == Step.DOWN:
                gen += 1
            # SPOUSE: no generation change
        return gen


# ── Graph builder (from DB rows) ─────────────────────────────────────────

def build_family_graph(
    person_rows: list[dict],
    link_rows: list[dict],
) -> FamilyGraph:
    """
    Build a FamilyGraph from raw DB query results.

    ``person_rows``: each dict has person_pk, person_id, first_name,
                     middle_name, last_name, gender_code
    ``link_rows``:   each dict has person_a_pk, person_b_pk, link_type
    """
    graph = FamilyGraph()

    for row in person_rows:
        node = PersonNode(
            person_pk=UUID(str(row["person_pk"])),
            person_id=row["person_id"],
            first_name=row["first_name"],
            middle_name=row.get("middle_name"),
            last_name=row.get("last_name"),
            gender_code=row.get("gender_code"),
        )
        graph.add_person(node)

    for row in link_rows:
        graph.add_link(
            person_a_pk=UUID(str(row["person_a_pk"])),
            person_b_pk=UUID(str(row["person_b_pk"])),
            link_type=row["link_type"],
        )

    return graph
