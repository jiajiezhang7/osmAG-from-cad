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
        int roomId;
        topo_geometry::point center;
        topo_geometry::point st;//edge start (only used at roomGraph init, because at very beginning, each roomVertex is a half edge
        topo_geometry::point ed;//edge end (only used at roomGraph init
        std::vector<VoriGraphPolygon*> polygons;
        std::set<roomVertex*> neighbours;

        roomVertex* parentV;//if not null, it is a sub-cell

        std::vector<passageEdge *> passages;
    public:
        roomVertex(int roomId, topo_geometry::point loc, topo_geometry::point st, topo_geometry::point ed);

        //merge polygon
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
    topo_geometry::point position;
    std::vector<roomVertex*>  connectedAreas;
    bool junction;
    passageLine line;

    passageEdge(topo_geometry::point p, bool j):position(p), junction(j){};
};


void connectRoomVertexes(std::vector<roomVertex*> &originSet);

}
#endif
