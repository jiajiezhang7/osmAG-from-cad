/*roomGraph:
 *
 * Author:  Yijun Yuan
 * date:    Nov.2.2017
 *
 * The main task of this roomGraph is to build a line graph 
 * and then merge those edges with same roomId into one 
 * roomVertex
 */

#ifndef ROOMGRAPH_H__
#define ROOMGRAPH_H__


#include <vector>
#include <QPainter>
#include <QImage>
#include <QDebug>
#include <QPoint>
#include <QPolygon>

#include <iterator>

#include "VoriGraph.h"
#include "TopoGeometry.h"
#include "passageSearch.h"


#include "CGAL/Polygon_2.h"
#include "cgal/CgalVoronoi.h"


namespace RMG{
class roomVertex;
class passageEdge;

    class AreaGraph {
    public:
    //TODO: try to change originSet from vector to list, because we need to delete roomVertex in mergeRoomCell
        std::vector<roomVertex*> originSet;//here we use vector not set because it only insert while new a node.
//        std::vector<roomVertex*> graph;

        std::set<VoriGraphVertex*> passageV_set;
//        std::vector<passageEdge*> passageEList;       //mainly used in buildAreaGraph_bk()
        std::list<passageEdge*> passageEList;
    public:
//        roomGraph(VoriGraph &voriGraph);  //by Yijun
        void mergeRoomCell();
        void prunning();
        void arrangeRoomId();
        void show();
        void draw(QImage& image);
        void mergeRoomPolygons();
        
        // 优化房间多边形，使通道与房间边界重合
        // 可选参数：已计算好的通道端点信息，避免重复计算
        void optimizeRoomPolygonsForPassages(const std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, std::pair<roomVertex*, roomVertex*>>>* precomputedPassagePoints = nullptr);
        
        // 去除originSet中形状相同的多边形
        void removeDuplicatePolygons();
        size_t calculatePolygonHash(const std::list<topo_geometry::point>& polygon);
        bool arePolygonsEqual(const std::list<topo_geometry::point>& poly1, const std::list<topo_geometry::point>& poly2);
        void transferPassages(roomVertex* source, roomVertex* target);
        
        // 简化多边形，减少直线上的冗余点
        void simplifyPolygons(double epsilon = 0.05, const std::vector<topo_geometry::point>* preservePoints = nullptr);
        std::list<topo_geometry::point> simplifyPolygon(const std::list<topo_geometry::point>& polygon, double epsilon, const std::vector<topo_geometry::point>* preservePoints = nullptr);
        double pointToLineDistance(const topo_geometry::point& p, const topo_geometry::point& lineStart, const topo_geometry::point& lineEnd);
        
        // 移除多边形中的“毛刺”
        void removeSpikesFromPolygons(double angleThreshold = 30.0, double distanceThreshold = 0.05, 
                                    const std::vector<topo_geometry::point>* preservePoints = nullptr);
        std::list<topo_geometry::point> removeSpikesFromPolygon(const std::list<topo_geometry::point>& polygon, 
                                                            double angleThreshold, double distanceThreshold,
                                                            const std::vector<topo_geometry::point>* preservePoints = nullptr);
        
        // 合并小面积相邻房间
        void mergeSmallAdjacentRooms(double minArea = 4.0, double maxMergeDistance = 1.5);
        std::list<topo_geometry::point> mergePolygons(const std::list<topo_geometry::point>& poly1, 
                                                     const std::list<topo_geometry::point>& poly2);
        double calculateRoomArea(roomVertex* room);
        topo_geometry::point calculateRoomCenter(roomVertex* room);
        
        // 导出为osmAG.xml格式
        void exportToOsmAG(const std::string& filename,
                         bool simplify_enabled = true, double simplify_tolerance = 0.05,
                         bool spike_removal_enabled = true, double spike_angle_threshold = 60.0, 
                         double spike_distance_threshold = 0.30);

        //Jiawei: For using passages as edges
        AreaGraph(VoriGraph &voriGraph);
        void buildAreaGraph(VoriGraph &voriGraph);
        void mergeAreas();
    public:
        /*
         * created at 1/22/2018 for passage based search
         */
        //0. generate_areaInnerPPGraph for each roomVertex
//        void roomV_generate_areaInnerPPGraph(VoriGraph &voriGraph);

        //1. for a random point provide the path in its room

            //2. integrate the whole graph by collect all the PPEdges

        //3. visualize
        //4. visualize the high level graph
};

class roomVertex{
    public:
        // 房间ID
        int roomId;
        // 房间中心点
        topo_geometry::point center;

        topo_geometry::point st;//edge start (only used at roomGraph init, because at very beginning, each roomVertex is a half edge
        topo_geometry::point ed;//edge end (only used at roomGraph init

        // 房间包含的多边形
        std::vector<VoriGraphPolygon*> polygons;

        // 相邻房间
        std::set<roomVertex*> neighbours;

        roomVertex* parentV;//if not null, it is a sub-cell

        // 连接此房间的通道
        std::vector<passageEdge *> passages;
    public:
        roomVertex(int roomId, topo_geometry::point loc, topo_geometry::point st, topo_geometry::point ed);

        //merge polygon
        // 房间的边界多边形
        std::list<topo_geometry::point> polygon;
        void mergePolygons();


public:
        /*
         * created at 1/21/2018 for passage based search
         */
        //local passage stuff
        std::list<VoriGraphHalfEdge*> areaInnerPathes;//record the path ()
        std::list<PS::PPEdge*> areaInnerPPGraph;//the vertex to vertex graph in this room
        std::list<PS::PPEdge*> areaInnerP2PGraph;//the passage to passage graph
        std::set<VoriGraphVertex*> voriV_set;
        //transform from areaInnerPathes to areaInnerPPGraph
        void init_areaInnerPPGraph();
        //from areaInnerPPGraph to areaInnerP2PGraph(Passage to Passage graph)

};

class passageLine{
public:
    std::list<topo_geometry::point> cwline;     //line in clockwise
    std::list<topo_geometry::point> ccwline;    //line in counterclockwise
    double length;

public:
    double get_len(){
        std::list<topo_geometry::point>::iterator last_pit=cwline.begin();
        std::list<topo_geometry::point>::iterator pit=last_pit;
        double len=0;
        for(pit++;pit!=cwline.end();pit++){
            len+=boost::geometry::distance(*last_pit,*pit);
            last_pit=pit;
        }
        length=len;
        return len;
    }
};
class passageEdge{
public:
    // 通道位置 
    topo_geometry::point position;
    
    // 通道连接的房间
    std::vector<roomVertex*>  connectedAreas;

    // 表示通道是否为连接点
    bool junction;

    // 通道的线段表示
    passageLine line;

    passageEdge(topo_geometry::point p, bool j):position(p), junction(j){};
};


void connectRoomVertexes(std::vector<roomVertex*> &originSet);

}
#endif
