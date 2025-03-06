#ifndef QIMAGE_VORONOI_H
#define QIMAGE_VORONOI_H


#include <vector>

#include <QPainter>
#include <QImage>
#include <QPainterPath>
#include <QDebug>

//#include "TopoGeometry.h"
#include "TopoGraph.h"



enum TripleValue{OCCUPIED=0, UNKNOWN=127, FREE=255};

void analyseImage(QImage &pImg, bool &pIsTriple);

bool getSites(QImage &pImg, std::vector<topo_geometry::point> &sites);

void paintVori(QImage &image, VoriGraph &voriGraph);

void paintVori_Area(QImage &image, VoriGraph &voriGraph);

void paintVori_vertex(QImage &image, VoriGraph &voriGraph);

void paintVori_AreaRoom(QImage &image, VoriGraph &voriGraph);

void qRGB2Gray(QImage &image);

void paintVori_onlyArea(QImage &image, VoriGraph &voriGraph);

void paintVori_randomcolor(QImage &image, VoriGraph &voriGraph);

void paintVori_pathFace(QImage &image, VoriGraph &voriGraph);

  
void paintTopoPaths(TopoGraph &graph, QImage &image);
  
  
void paintVori_OnlyOutline(QImage &image, VoriGraph &voriGraph);

#endif
