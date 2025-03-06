## Indoor osmAG Map Standard
This is a draft by Jiajie Zhang. Some details still need to be discussed and approved by Prof. Schwertfeger.

This document outlines the specifications for the **osmAG (OpenStreetMap Area Graph)** map format, which is specifically designed for mobile robotics applications. The osmAG format is built upon and extends the **OpenStreetMap (OSM) XML** format to incorporate hierarchical structures, semantic information, and topometric data.

### **O. Key Advantages**

- **Full Compatibility:** Seamlessly compatible with the OSM standard, enabling the use of existing tools and libraries in the OSM ecosystem.
- **Memory Efficiency:** Achieves significantly reduced memory consumption compared to traditional 2D/3D grid maps by orders of magnitude.
- **Rich Hierarchical and Semantic Support:** Provides comprehensive support for multi-level maps and detailed semantic annotations.
- **Robotics-Centric Design:** Purposefully engineered to store and utilize robotic map information in a hierarchical manner optimized for robotics applications.

### **I. Core Concepts**

- **Area:** Represents a closed polygonal region, which can be a room or corridor in indoor environments, or larger spaces like buildings and campuses in outdoor settings. Areas are defined by an ordered sequence of nodes (implemented as a closed "way" element in OSM).
    - **Inner Area (room & corridor):** Represents an unobstructed space within boundaries, particularly useful for robot localization.
    - **Structure Area (sector & floor & building):** Encompasses a region with defined boundaries, typically representing the external perimeter of a building and serving as a container for sub-areas.
- **Passage:** Represents an edge within the Area Graph that establishes topological connections between two areas, implemented as a line segment formed by nodes shared between the connected areas.
- **Hierarchy:** Implements a hierarchical organization of areas, enabling both vertical grouping (e.g., multi-floor buildings) and horizontal grouping (e.g., combining adjacent areas).
- **Topometric Data:** Incorporates both metric information about spatial positions and topological relationships between areas and passages.
- **Semantic Information:** Encodes rich contextual data including room types, terrain characteristics, and accessibility features through OSM tags.

### **II. On-Disk Format (OSM XML)**

The osmAG format utilizes and extends the OSM XML format with specific enhancements.

- **XML Tag: `node`:** Defines a geographic point using latitude and longitude coordinates, each with a unique identifier.
    - A designated `root node` serves as the map's origin point, facilitating conversion between geodetic and Cartesian coordinate systems for indoor robot navigation. This node is marked with a special tag: `<tag k='name' v='root' />`
- **XML Tag: `way`:** Represents an ordered sequence of nodes, utilized in osmAG to define both areas and passages.
    - Area-specific Tags:
        - **`height`:** Defines the vertical dimension of different floors using the standard OSM height key.
        - `indoor`: Currently set uniformly to "room" (usage under review for necessity)
        - `level`: Indicates the floor number within the building hierarchy.
        - `name`: Specifies the area's identifier, typically derived from CAD documentation.
        - **`osmAG:type`:** Distinguishes between `area` and `passage` elements.
            - Possible values: area, passage
        - **`osmAG:areatype`:** Specifies the functional classification of an area as either an `inner` area or a `structure` area. Inner areas are further categorized by function: stairs, elevator, or room.
            - Possible values: room, stairs, elevator, structure
        - **`osmAG:parent`:** References the parent area's identifier, establishing the hierarchical structure. Child areas must be fully contained within their parent's boundaries.
    - Passage-specific Tags:
        - **`osmAG:from` and `osmAG:to`:** Define the connected areas' identifiers. The order is not significant as the Area Graph is undirected.
        - `level`: Indicates the floor level where the passage is located.
        - `name`: Currently implemented as a random numerical identifier (usage under review)
        - **`osmAG:type`:** Identifies the element as a passage.
            - Value: passage

### **III. Hierarchical Structure**

The hierarchical organization serves two primary functions:

- **Area Aggregation:** Enables the logical combination of adjacent areas to form larger unified spaces. This applies to both outdoor scenarios (e.g., combining parking lots with streets) and indoor environments (e.g., grouping rooms within a floor).
- **Multi-Level Organization:** Facilitates the representation of vertically stacked 2D areas to accurately model multi-story buildings.

### **IV. Rules for Elevators and Stairs**

- Elevators and stairs serve as special vertical connectors between floors. In osmAG, they are implemented as areas with distinctive semantic tags: **`osmAG:areatype` = elevator || stairs**
- Elevator Implementation:
    - Each floor contains an area representing the same elevator, with the floor area as its parent.
    - Elevator access points are represented by passages, defined using osmAG:from = elevator area, osmAG:to = connected floor area
    - (The current implementation follows standard area rules with minimal exceptions, adhering to the principle of maintaining consistent representation with minimal special cases)
- Stairwell Implementation:
    - Follows the same pattern as elevators, differentiated by the semantic tag: `osmAG:areaType`= stairs
- Escalator-style Staircases:
    - only one area representing the escalator-style staircase, parented to the higher floor.
    - Features two passages representing both ends:
        - First passage: osmAG:from = staircase area, osmAG:to = connected area on floor A
        - Second passage: osmAG:from = staircase area, osmAG:to = connected area on floor B

### **V. Utilities**

**Visualization and Editing Capabilities**

- osmAG data can be visualized and modified using standard OpenStreetMap-compatible software, particularly JOSM (Java OpenStreetMap Editor)
- Supports both 2D and 3D rendering, with semantic labels displayed using standard OSM iconography. OpenIndoor provides 3D visualization capabilities for osmAG maps.
- Custom ROS packages have been developed to parse and visualize osmAG in 3D through Rviz, leveraging the hierarchical design to enable selective focus on areas of interest.

**Format Conversion Tools**

For manual editing of osmAG.xml in JOSM, we provide conversion scripts to transform between fix_id and semantic versions.

**Automated Map Generation**

- Supports automated generation of osmAG maps from various source data including 2D grid maps, 3D point clouds, and CAD files.
- Implements sophisticated processes for segmentation, feature extraction, and area merging from existing map data.
- Includes specialized processing for CAD files with layer management and algorithmic parameters to optimize segmentation quality.

### **VII. Path Planning**

- The osmAG format is optimized for path planning applications, leveraging its hierarchical structure and semantic annotations.
- Incorporates robot capability considerations by assigning appropriate costs to passages and areas based on robot specifications and semantic context.
- Implements efficient path planning through passage graph generation for leaf areas, utilizing A* algorithms to compute accurate traversal costs.
- Employs hierarchical planning strategies to enhance pathfinding efficiency by utilizing pre-computed costs at higher hierarchical levels. (Currently under development by Yongqi)

### Notice

- The osmAG format currently exists in two variants: "fix_id" and "semantic" versions (distinct from Fujing's semantic definition)
    - Key Distinctions:
        - Fix_id version: Uses way IDs as values for tags "`osmAG:parent`", "`osmAG:from`", and "`osmAG:to`"
        - Semantic version: Uses the area's "`name`" tag value instead
    - Rationale for Dual Versions:
        - Legacy Support: Existing codebase by Delin & Chengqian for data parsing, global planning, and visualization requires the fix_id version
        - Editor Compatibility: JOSM editing necessitates the semantic version due to automatic ID reassignment during file saves, which would break references in the fix_id version
- To address this duality, we have developed comprehensive Python utilities for bidirectional conversion between these versions.
