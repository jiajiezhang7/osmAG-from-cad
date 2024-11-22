#ifndef TOPO_GRAPH_H
#define TOPO_GRAPH_H

#include "VoriGraph.h"

// #include <QPainter>

class TopoExit;

class TopoVertex;

class TopoHalfEdge;

class TopoGraph;

class VoriGraphHalfEdge;

extern VoriConfig *sConfig;


/**
 * Saves distance values: distance along the path and hops in the graph and hops only over major vertices
 * 记录path的长度(distance)和其上的hope(段数)
 */
struct DistanceCalcHelper {
    DistanceCalcHelper() : distance( -1. ), hops( 0 ), majorHops( 0 ) {}

    double distance;
    unsigned int hops;
    unsigned int majorHops; // only those that not only have feature edges

    void clear();
};


/**
 * A vertex in the topology graph
 * 
 */
class TopoVertex {
public:
    TopoVertex() : distanceOfJoinedVertices( 0. ), isFeatureVertex( false ) {}


    void calculateAngles();

    TopoExit *findDirectExitTo(TopoVertex *vertex);

    TopoExit *findExitTo(TopoVertex *vertex, bool *wasMajor = 0);

    std::list<VoriGraphVertex *> aVoriVertices;

    std::list<TopoExit *> aExits;
    double biggestExitAngleRad, smallestExitAngleRad;

    topo_geometry::point point;
    double distanceOfJoinedVertices;

    double averageDistanceToObstacles;

    DistanceCalcHelper distanceCalcHelper;
    // is true if there are exactly two non-feature adjacent vertices (== this vertex would vanish if the feature edges are removed)
    // the opposite is called major Vertex
    bool isFeatureVertex;

    // loops that this vertex is part of
    // the lower pointer exit has to be first
    // experimental for matching....
    std::map<std::pair<TopoExit *, TopoExit *>, DistanceCalcHelper> loops;

    // for the similairty matching...
    bool inconsistent;

    bool isIsomorph;

    unsigned int id;

    friend class TopoGraph;
};

/**
 * 
 * A Half edge in the TopoGraph
 * 
 * 
 */
class TopoHalfEdge {
public:
    TopoHalfEdge() : sourceExit( 0 ), targetExit( 0 ), sourceVertex( 0 ), targetVertex( 0 ), twin( 0 ),
                     edgeFlags( 0 ) {}

    enum EdgeFlags {
        UNKNOWN = 0,
        DEAD_END = 0x01,   // In this direction a dead end is reached (shorter distance than the rest of the graph)
        FEATURE_END = 0x02,   // this dead end is even so small that it is just a feature
        OUTSIDE = 0x04,   // In this direction a ray to the outside is reached
        DEAD_ENDISH = 0x08,   // There is at least one DEAD_END in this direction
        OUTSIDEISH = 0x10,   // There is at least one OUTSIDE end in this direction
        LOOP = 0x20,   // In this direction at least one loop is present
        LOOP_BACK = 0x40
    };  // Going this direction there is a way to come back to this source (not using this twin!)

    TopoExit *sourceExit;
    TopoExit *targetExit;

    TopoVertex *sourceVertex;
    TopoVertex *targetVertex;

    TopoHalfEdge *twin;

    // the flas show what to expect if you follow this edge
    // so a dead end will have the dead_end flag on the edge that leads to the end vertex
    unsigned int edgeFlags;

    bool isRay() { return !(sourceVertex && targetVertex); }

    bool getPointForDistance(double distance, topo_geometry::point &);

    VoriGraphHalfEdge *getFirst() { return *voriHalfEdges.begin(); }

    std::list<VoriGraphHalfEdge *> voriHalfEdges;
    double distance;

};

/**
 * Handles one edge connected to a (source) vertex (leading from this vertex)
 * 
 */
class TopoExit {
public:

    TopoHalfEdge *exitEdge; // the edge whose source is topoVertex
    TopoHalfEdge *twinEdge() { return exitEdge->twin; }

    TopoVertex *source() { return exitEdge->sourceVertex; }

    TopoVertex *target() { return exitEdge->targetVertex; }

    TopoExit *nextTopoExit;
    double angleToNextTopoExitRad; // between 0. and 2 M_PI

    double vertexEdgeDistance; // The distance between the (possibly joined) vertex and the beginning of the actual edge
    double totalDistance; // The edge distance plus both vertexEdgeDistances

    double distance() { return totalDistance; }

    // already includes both vertexEdgeDistance
    double distanceToNextMajorVertex;
    TopoVertex *nextMajorVertex;

    std::map<TopoVertex *, DistanceCalcHelper> distances;
};


class TopoGraph {
public:
    TopoGraph(VoriGraph &pVoriGraph);

//     void paintPaths(QImage &image);
//     void paintNumbers(QImage &image);
    void printInfo();

    void assignVertexIds();

// private:
    void createFromVoriGraph();
//     void paintVoriEdge(QPainter &painter, VoriGraphHalfEdge *edge, bool isFeature);

    void markGraph();

    void checkFirstVertexInList(std::map<TopoVertex *, bool> &workList);

    void removeDistanceMarks();

    void setInconsistencyMarks(bool set);

    void calcAllDistances();

    void calcDistancesFor(TopoExit *startExit);

    void addTargetToWorkList(TopoExit *currExit, std::set<TopoExit *> &workList, TopoVertex *startVertex);


    // lists of ALL exits, vertices and half edges in the topo graph...
    std::list<TopoExit> aExits;
    std::list<TopoVertex> aVertices;
    std::list<TopoHalfEdge> aHalfEdges;

    VoriGraph &aVoriGraph; // the graph all voriGraph pointers refer to
};


#endif
