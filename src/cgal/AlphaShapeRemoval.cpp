#include "cgal/AlphaShapeRemoval.h"

#include <iostream>
#include <QImage>
#include <QDebug>
#include <QPainter>
#include "cgal/AlphaShape.h"

using namespace std;

void performAlphaRemoval(QImage &pImg, double pAlphaShapeSquaredDist, double pMaxPolygonLength){
  AlphaShapePolygon alphaShapePolygon;

  vector<AlphaShapePolygon::K::Point_2> points;
  alphaShapePolygon.getPoints(pImg, points);

  list<AlphaShapePolygon::Polygon_2> polygons;
  alphaShapePolygon.generatePolygons(points, pAlphaShapeSquaredDist, polygons);

  QImage image = pImg.convertToFormat(QImage::Format_ARGB32);
  image.fill(qRgba(255, 255, 255, 0));
  QPainter painty(&image);
  painty.setPen(Qt::blue);
  for(list<AlphaShapePolygon::Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr){
    for(AlphaShapePolygon::Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr){
        AlphaShapePolygon::Segment s = *edgeItr;
        painty.drawLine(round(s.source().x()), round(s.source().y()), round( s.target().x()), round(s.target().y()));
    }
  }

  
  for(list<AlphaShapePolygon::Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end();){
    if(alphaShapePolygon.calculatePolygonLength(*itr) > pMaxPolygonLength){
      itr = polygons.erase(itr);
    }else{
      ++itr;
    }
  }

  painty.setPen(Qt::red);
  for(list<AlphaShapePolygon::Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr){
    for(AlphaShapePolygon::Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr){
        AlphaShapePolygon::Segment s = *edgeItr;
        painty.drawLine(round(s.source().x()), round(s.source().y()), round( s.target().x()), round(s.target().y()));
    }
  }
  painty.end();
//  image.save("detectAlphaRemoval.png");
  
  list<CGAL::Bbox_2> bboxes;
  alphaShapePolygon.generateBBoxesForPolygons(polygons, bboxes);

  cout<<"Removing the points for "<<polygons.size()<<" polygons..."<<endl;
  for(vector<AlphaShapePolygon::K::Point_2>::iterator itrPoints = points.begin(); itrPoints != points.end(); ++itrPoints){
    bool remove = false;
    list<CGAL::Bbox_2>::iterator itrBBoxes= bboxes.begin();
    for(list<AlphaShapePolygon::Polygon_2>::iterator itrPolygons = polygons.begin(); itrPolygons != polygons.end(); ++itrPolygons, ++itrBBoxes){
      if(AlphaShapePolygon::isOutside(*itrPoints, *itrPolygons, *itrBBoxes) ){
        remove = true;
        break;
      }
    }
    if(remove){
      pImg.setPixel(round(itrPoints->x()), round(itrPoints->y()), qRgba(255, 255, 255, 255) );
    }
  }
  
}



