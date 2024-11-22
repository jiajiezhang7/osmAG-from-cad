#ifndef ROOM_DECT_H
#define ROOM_DECT_H

#include <QImage>
#include <CGAL/Polygon_2.h>
#include <string>

// includes for defining the Voronoi diagram adaptor
//#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
//#include <CGAL/Delaunay_triangulation_2.h>
//#include <CGAL/Voronoi_diagram_2.h>
//#include <CGAL/Delaunay_triangulation_adaptation_traits_2.h>
//#include <CGAL/Delaunay_triangulation_adaptation_policies_2.h>

#include <CGAL/Alpha_shape_2.h>
#include <CGAL/Alpha_shape_face_base_2.h>
#include <CGAL/Delaunay_triangulation_2.h>
#include <CGAL/Triangulation_hierarchy_2.h>

#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>

#include <boost/geometry/geometries/adapted/boost_tuple.hpp>

#include "cgal/AlphaShape.h"

typedef CGAL::Exact_predicates_inexact_constructions_kernel K;

typedef CGAL::Alpha_shape_vertex_base_2<K> Avb;
typedef CGAL::Triangulation_hierarchy_vertex_base_2<Avb> Av;
typedef CGAL::Triangulation_face_base_2<K> Tf;
typedef CGAL::Alpha_shape_face_base_2<K, Tf> Af;

typedef CGAL::Triangulation_default_data_structure_2<K, Av, Af> Tds;
typedef CGAL::Delaunay_triangulation_2<K, Tds> Dt;
typedef CGAL::Triangulation_hierarchy_2<Dt> Ht;
typedef CGAL::Alpha_shape_2<Ht> Alpha_shape_2;

typedef Alpha_shape_2::Alpha_shape_edges_iterator Edge_iterator;

typedef CGAL::Polygon_2<K> Polygon_2;
typedef K::Segment_2 Segment;

//add
typedef Polygon_2::Vertex_iterator Vertex_iterator;

#include "VoriGraph.h"

class RoomDect {
public:
    // containing roomid of all polygons (except the biggest one)
    std::list<unsigned int> roomidList;

    //record map room's id to room's vorigraph
    std::map<unsigned int, VoriGraph> voriRooms;

    //map of border vertices in voriroom to the ones in vorigraph
    std::map<unsigned int, std::map<VoriGraphVertex *, VoriGraphVertex *> > roomMap;

    //void drawRoom(std::string prefix);
    //cut at intersections
    void cutEdgeCrossingPolygons(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph, Polygon_2 *poly);
    void forRoomDect(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph, AlphaShapePolygon::Polygon_2 *poly);

    void drawPolygon(AlphaShapePolygon &alphaSP, QImage &pImg);

private:
//return true if edge intersects with polygon and put the cut distances from source to the vector
    bool cutDist(VoriGraphHalfEdge *edge, Polygon_2 *polygon, std::vector<double> &distance);

//used during cutEdgeCrossingPolygons
    void setRoomIDForNonRoomVertex(VoriGraphHalfEdge *edge, Polygon_2 *polygon, int index = -1);

    void setRoomIDForPath(VoriGraph &voriGraph, AlphaShapePolygon &alphaSP);

    void mergeDeadEndInRoom_polygon(VoriGraph &voriGraph);
    void mergeDeadEndInRoom(VoriGraph &voriGraph);
    
    void labelpassages(VoriGraph &voriGraph);

    void saveRooms(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph, Polygon_2 *poly);

    void roomCenterCalc(AlphaShapePolygon &alphaSP, int roomIndex, double &centerX, double &centerY);

    void generateNewRoom(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph);

    void removeDeadEndRoomVertex(VoriGraph &voriGraph);

};

#endif