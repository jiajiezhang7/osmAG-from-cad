# osmAG Standards Document Updates (2025-06-03)

This document logs the recent additions to the `osmAG_standards_24.12.md` file.

## Section III: Hierarchical Structure

The following rules were added to this section:

1.  **Containment Principle:** For a parent area representing a hierarchy, all its child areas must be strictly within the parent area.
    *   *Details:* This rule ensures that parent areas fully encompass their child areas, maintaining a clear spatial hierarchy.

2.  **Non-Overlapping Principle (Same Hierarchy):** Any two areas under the same immediate parent (i.e., at the same hierarchy level within that parent) must not overlap. Areas can overlap if they are at different hierarchy levels or belong to different parent areas after aggregation.
    *   *Details:* This rule prevents spatial ambiguity for areas that are siblings within the same hierarchical level. Overlap is permitted for areas at different levels or under different parent structures resulting from aggregation.

## Section IV: Rules for Elevators and Stairs

The following rule was added to this section:

1.  **Inter-Floor Passages:** For elevators and stairwells, passages are explicitly defined to connect their corresponding areas of the same name across different (typically adjacent) floors. These passages function as the edges representing vertical movement between these areas, e.g., `osmAG:from` = `elevatorA_floor1_area`, `osmAG:to` = `elevatorA_floor2_area`.
    *   *Details:* This rule clarifies how vertical connections between floors are represented for elevators and stairwells, using passages to link same-named areas on different levels.
