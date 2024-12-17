#ifndef VORI_GRAPH_H
#define VORI_GRAPH_H

//#include "cgal/CgalVoronoi.h"
#include "VoriConfig.h"

#include "TopoGeometry.h"

#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <CGAL/Polygon_2.h>
#define thresholdForCut 0.001
#define EPSINON 0.00000001

class VoriGraphVertex;

class VoriGraphHalfEdge;



/**
 * A polygon (jointed faces) in the vori graph
 *
 */
struct VoriGraphPolygon {
    VoriGraphPolygon() : isRay( false ) {}

    bool operator==(const VoriGraphPolygon &other) {
        return this == &other;
    }

    bool isRay;
    std::list<VoriGraphHalfEdge *> belongpaths;
    // 各个face中的site => list of points (for the sites)
    std::list<topo_geometry::point> sites;
    VoriGraphPolygon *twin;
    std::list<topo_geometry::point> polygonpoints; //多边形端点

};

/**
 * A half edge in the vori graph
 * 
 */
struct VoriGraphHalfEdge {   //path
    VoriGraphHalfEdge() : source( 0 ), target( 0 ), twin( 0 ), distance( 0 ), deadEnd( false ), groupId( 0 ),
                          roomId( -1 ), obstacleAverage( 0. ), obstacleMinimum( 0. ), pathFace( NULL ),
                          roomPath( false ) {}

    bool operator==(const VoriGraphHalfEdge &other) {
        return this == &other;
    }

    /// the list of path edges - those are simple coordinates forming the path from the voronoi diagram
    std::list<topo_geometry::Halfedge> pathEdges;

    VoriGraphVertex *source;
    VoriGraphVertex *target;
    VoriGraphPolygon *pathFace;
    VoriGraphHalfEdge *twin;  // a pointer point to another VoriGraphHalfEdge

    std::list<topo_geometry::point> joinPolygon(VoriGraphHalfEdge *, VoriGraphHalfEdge *);

    /// The length along the path of this edge
    double distance;    //length of this path
    /// if this is a ray the ray coordinates are saved in here
    topo_geometry::Halfedge topo_ray;

    /// true if this is a dead end
    bool deadEnd;
    /// a group id assigned to this vertex - after keepBiggestGroup only one group should exist
    unsigned int groupId;

    /// average distance to the obstacles along the path
    double obstacleAverage;
    /// minimum distance to an obstacle along the path
    double obstacleMinimum;

    // added from yutianyan
    int roomId;    // a room id assigned to this halfedge : -1 means not in any room
    // set and get function of roomId
    void setRoomId(unsigned int i) { roomId = i; };
    int getRoomId() { return roomId; };
    bool roomPath;    // artificial path from room border to center
    bool markRoomPath() { 
        roomPath = true;
        return true; };
    bool isRoomPath() { return roomPath; };

    /// returns if this a ray or not.
    bool isRay() const { return (bool) (source) ^ (bool) (target); }

    /// samples one point along the path in a certain distance.
    bool getPointForDistance(double distance, topo_geometry::point &);    //获取路径上距离始节点特定距离的某个点的坐标（该点可能在某个Halfedge上）

    // added from yutianyan
    std::list<VoriGraphHalfEdge> cutVoriGraphHalfEdge_Polygon(double cutlength, VoriGraphVertex &,
                                                              std::list<VoriGraphPolygon> &);
    std::list<VoriGraphHalfEdge> cutVoriGraphHalfEdge_Polygon_accruay(double cutlength, VoriGraphVertex &,
                                                              std::list<VoriGraphPolygon> &);
    std::list<VoriGraphHalfEdge> cutVoriGraphHalfEdge(double cutlength, VoriGraphVertex &);
    //if size is 0, fail to cut.
};


/**
 * A vertex in the voronoi graph
 * 
 */
struct VoriGraphVertex {
    VoriGraphVertex() : groupId( 0 ), roomId( -1 ), obstacleDist( 0. ), roomVertex( false ), borderVertex( false ),
                        roomCenter( false ),passageVertex(false) {}

    bool operator==(const VoriGraphVertex &other) {
        return this == &other;
    }

    /// the coordinate of this vertex
    topo_geometry::point point;   //the position of this vertex

    std::list<VoriGraphHalfEdge *> edgesConnected;  // the VoriGraphHalfEdge list connected to this vertex
    unsigned int groupId;

    double obstacleDist;  // distance to the closes obstacle
    // added from yutianyan
    //bool for room vertex(at the cut)
    bool roomVertex;
    // added from yutianyan
    //bool for border (deadend and the cut)
    bool borderVertex;
    // added from yutianyan
    //bool for room center
    bool roomCenter;
    // added from yutianyan
    // a room id assigned to this vertex - -1 means not in any polygons
    int roomId;
    //added by jiawei: label the passage vertex
    bool passageVertex;
    
    // added from yutianyan
    //set and get function of roomId
    void setRoomId(unsigned int i) { roomId = i; };
    // added from yutianyan
    int getRoomId() { return roomId; };

    bool removeHalfEdge(VoriGraphHalfEdge *edge);   //remove a VoriGraphHalfEdge from the list edgesConnected
    void markTwins();   //find the twin for each VoriGraphHalfEdge
    // added from yutianyan
    //mark room vertex (at the cut)
    void markRoomVertex() {
        roomVertex = true;
        borderVertex = true;
    };
    // added from yutianyan
    //mark border vertex (at the cut and dead end within a room)
    void markBorderVertex() { borderVertex = true; };
    // added from yutianyan
    //mark room center
    void markRoomCenter() { roomCenter = true; };
    // added from yutianyan
    bool isRoomVertex() { return roomVertex; };
    // added from yutianyan
    bool isBorderVertex() { return borderVertex; };
    // added from yutianyan
    bool isRoomCenter() { return roomCenter; };
    // added from yutianyan
    bool isPassageVertex() { return passageVertex; };
};

/**
 * A group of connected elements (vertices and edges) in the graph
 */



struct VoriGroup {
    /// pointer to some edge in the group
    VoriGraphHalfEdge *edge;
    /// the id of this group
    unsigned int groupId;
    /// the total sum of distances (length) of the paths of the edges in this group
    double distance;
};
//add by jiawei 2017.10.31
struct VoriGraphArea {
    VoriGraphArea() : roomId( -1 ){}
    bool operator==(const VoriGraphArea &other) {
        return this == &other;
    }

    int roomId;
    std::map<topo_geometry::point, VoriGraphArea*> connecttedAreas;
    std::map<VoriGraphHalfEdge*, VoriGraphPolygon*> includedPolygons;
    std::list<topo_geometry::point> polygonPoints;
};

/**
 * A vori graph is the first, basic, topological structure (generated from a voronoi diagram)
 * 
 */
struct VoriGraph {

    typedef CGAL::Exact_predicates_inexact_constructions_kernel K;
    typedef CGAL::Point_2<K> Point;
    typedef CGAL::Polygon_2<K> Polygon_2;
    VoriGraph() {};

    typedef std::map<topo_geometry::point, VoriGraphVertex, topo_geometry::Smaller> VertexMap;  //按照节点位置排序（x小在前，y小在前），由节点坐标索引VoriGraphVertex
    VertexMap vertices;   //包含所有节点的哈希表
    std::list<VoriGraphHalfEdge> halfEdges;
    std::list<VoriGraphPolygon> pathFaces;
    std::list<VoriGroup> groups;
    std::list<VoriGraphArea*> areas;


    std::list<VoriGraphHalfEdge>::iterator removeHalfEdge(std::list<VoriGraphHalfEdge>::iterator &remove);

    // added from yutianyan
    std::list<VoriGraphHalfEdge>::iterator removeHalfEdge_tianyan(std::list<VoriGraphHalfEdge>::iterator &remove,
                                                          bool deleteEmpty = true, bool deleteRoomBorder = true);
    //从VoriGraphHalfEdge列表里删掉 remove这条 VoriGraphHalfEdge
    std::list<VoriGraphHalfEdge>::iterator removeHalfEdge_jiawei(std::list<VoriGraphHalfEdge>::iterator &remove);

    std::list<VoriGraphHalfEdge>::iterator removeHalfEdge_roomPolygon(std::list<VoriGraphHalfEdge>::iterator &remove,
                                                                  bool deleteEmpty = true, bool deleteRoomBorder = true);
    void removeHalfEdge_roomPolygon(VoriGraphHalfEdge *remove, bool deleteEmpty = true, bool deleteRoomBorder = true);
    void joinHalfEdges();
    void joinHalfEdges_jiawei();
    void joinHalfEdges_tianyan();

    void joinHalfEdges(VoriGraphHalfEdge *, VoriGraphHalfEdge *);
    void joinHalfEdges_jiawei(VoriGraphHalfEdge *, VoriGraphHalfEdge *, bool = false); //把pFirst和pSecond两条路径连接起来
    //add from yutianyan
    void joinHalfEdges_tianyan(VoriGraphHalfEdge *, VoriGraphHalfEdge *, bool = false);// added from yutianyan

    void markDeadEnds_isRoomVertex();
    void markDeadEnds();

    // added from yutianyan
    bool cutHalfEdgeAtDistance_Polygon(double cutlength, VoriGraphHalfEdge *pHalfEdge, VoriGraphVertex &pPoint, unsigned int = 0);
    bool cutHalfEdgeAtDistance_Polygonbk(double cutlength, VoriGraphHalfEdge *pHalfEdge, VoriGraphVertex &pPoint, unsigned int = 0);
    bool cutHalfEdgeAtDistance(double cutlength, VoriGraphHalfEdge *pHalfEdge, VoriGraphVertex &pPoint, unsigned int = 0);
};


void coutpoint(topo_geometry::point p);

void printGraphStatistics(VoriGraph &voriGraph, std::string= "");


void gernerateGroupId(VoriGraph &voriGraph);

void removeGroupId(VoriGraph &voriGraph);

void keepBiggestGroup(VoriGraph &voriGraph);


void removeRays(VoriGraph &voriGraph);


void removeDeadEnds_addFacetoPolygon(VoriGraph &voriGraph, double maxDist);

void removeDeadEnds(VoriGraph &voriGraph, double maxDist);

/// for debugging...
void checkConnectedEdgesForError(VoriGraph &voriGraph);

VoriGraphHalfEdge *
pathToEdge(VoriGraph &voriGraph, double x, double y, double &Pmindist, topo_geometry::point &closestP);

#endif
