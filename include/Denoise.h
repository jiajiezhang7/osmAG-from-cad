//
// Created by houjiawei on 18-1-23.
//

#ifndef TOPO_GRAPH_2D_DENOISE_H
#define TOPO_GRAPH_2D_DENOISE_H

#endif //TOPO_GRAPH_2D_DENOISE_H
#include <iostream>
#include <string>
#include <CGAL/remove_outliers.h>
#include <CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include <QImage>
#include <QColor>


typedef CGAL::Exact_predicates_inexact_constructions_kernel Kernel;
typedef Kernel::Point_3 Point;


using namespace std;

QImage paintPoints(const char*  file_name, const vector<Point> &points, int width, int height);
bool isBlack(uchar* pixel, int black_threshold);
void getPoints(QImage &img, int &black_threshold, vector<Point> &points);
void usage();
bool DenoiseImg(const char* input_name, const char* output_name, int &black_threshold, int neighbors, double percentage);