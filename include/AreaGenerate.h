//
// Created by houjiawei on 18-1-24.
//

#ifndef TOPO_GRAPH_2D_AREAGENERATE_H
#define TOPO_GRAPH_2D_AREAGENERATE_H

#include <string>
#include <iostream>
#include <cmath>
#include <cstdio>
#include <stdlib.h>
#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>

#include "VoriGraph.h"
#include "TopoGraph.h"
#include "cgal/CgalVoronoi.h"
#include "cgal/AlphaShape.h"
#include "qt/QImageVoronoi.h"


//#include "TopoPathMatcher.h"

#include <QApplication>

#include <fstream>

#include "RoomDect.h"

#include "roomGraph.h"
#include "Denoise.h"

void generateAreas(const char *input_name, const char *output_name, VoriConfig *sConfig, VoriGraph &voriGraph);


void generateRMG(RMG::AreaGraph &RMGraph);
//bool generateAreas(QImage input_name, QImage output_name){}
#endif //TOPO_GRAPH_2D_AREAGENERATE_H