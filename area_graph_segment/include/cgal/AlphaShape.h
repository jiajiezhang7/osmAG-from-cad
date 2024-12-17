#ifndef ALPHA_SHAPE_MAPTOOL_H
#define ALPHA_SHAPE_MAPTOOL_H

#include <CGAL/Triangulation_face_base_2.h>


#include <CGAL/spatial_sort.h>


#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>

#include <CGAL/Alpha_shape_2.h>

#include <CGAL/Alpha_shape_face_base_2.h>


#include <CGAL/Delaunay_triangulation_2.h>
#include <CGAL/Triangulation_hierarchy_2.h>

#include <CGAL/Triangulation_vertex_base_2.h>

#include <CGAL/Polygon_2.h>


class QImage;


class AlphaShapePolygon{
  public:

  typedef CGAL::Exact_predicates_inexact_constructions_kernel K;

  typedef CGAL::Alpha_shape_vertex_base_2<K> Avb;
  typedef CGAL::Triangulation_hierarchy_vertex_base_2<Avb> Av;

  typedef CGAL::Triangulation_face_base_2<K> Tf;
  typedef CGAL::Alpha_shape_face_base_2<K,Tf> Af;

  typedef CGAL::Triangulation_default_data_structure_2<K,Av,Af> Tds;
  typedef CGAL::Delaunay_triangulation_2<K,Tds> Dt;
  typedef CGAL::Triangulation_hierarchy_2<Dt> Ht;
  typedef CGAL::Alpha_shape_2<Ht> Alpha_shape_2;

  typedef Alpha_shape_2::Alpha_shape_edges_iterator  Edge_iterator;

  typedef CGAL::Polygon_2<K> Polygon_2;
    typedef CGAL::Point_2<K> Point;
    typedef Polygon_2::Vertex_iterator VertexIterator;
    typedef Polygon_2::Edge_const_iterator EdgeIterator;
  typedef K::Segment_2  Segment;

  
  class SegmentSearchy{
    public:
      SegmentSearchy(std::list<std::pair<AlphaShapePolygon::Segment, bool> > &pSegments);

      typedef std::list<std::pair<AlphaShapePolygon::Segment, bool> >::iterator CellEntry;
      typedef std::list<CellEntry > CellEntries;
      CellEntries findSegments(AlphaShapePolygon::K::Point_2 &p);
    protected:
      void fill();

      std::list<std::pair<AlphaShapePolygon::Segment, bool> > & aSegments;
      std::map<int, std::map<int, SegmentSearchy::CellEntries> > segmentSourceMap;
  };

  Polygon_2 *performAlpha(QImage &pImg, double squared_size_is_alpha, bool deleteSmallPolygon = true);
  Polygon_2 *performAlpha_biggestArea(QImage &pImg, double squared_size_is_alpha, bool deleteSmallPolygon = true);

  void getPoints(QImage &pImg, std::vector<K::Point_2> &points);

  void generatePolygons(std::vector<K::Point_2> &points, double squared_size_is_alpha, std::list<Polygon_2> &polygons);
  void generateBBoxesForPolygons(std::list<Polygon_2> &polygons, std::list<CGAL::Bbox_2> &bboxes);

  static bool isOutside(const K::Point_2 &p, Polygon_2 &poly, CGAL::Bbox_2 &box);
  
  static double calculatePolygonLength(Polygon_2 &polygon);
  
  //add  
  Polygon_2 & getPolygon(unsigned int i);
  
  unsigned int sizeOfPolygons();
  
  void drawPolygonByIndex(QImage &pImg, unsigned int index);
  
  void drawPolygon(QImage &pImg, Polygon_2 * poly);

  protected:
    std::list<Polygon_2> polygons;

//     void growPolygon(std::list<Segment> &segments, Polygon_2 &polygon, K::Point_2 front, K::Point_2 back);
    void growPolygon(SegmentSearchy &searchy, Polygon_2 &polygon, K::Point_2 front, K::Point_2 back);
};

#endif

