//
// Created by aass on 30/01/19.
//

// Last Modified by Jiajie on 24/7/02 

/*
Steps:
    1.Preprocess (noise, furniture removal)
    2.Voironoi generation
    3.Topology Graph generation
    4.Initial Area Graph generation
    5.Region 合并 -> final Area Graph

*/


#include <string>
#include <iostream>

#include <fstream>
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

#include <boost/filesystem.hpp>
#include <boost/iterator/filter_iterator.hpp>
#include <boost/filesystem/path.hpp>

#include <QApplication>

#include <QMessageBox>

#include "RoomDect.h"

#include "roomGraph.h"
#include "Denoise.h"
#include <sys/stat.h>
#include <sys/types.h>

#include "cgal/AlphaShapeRemoval.h"

using namespace std;

#include <sstream>

template<typename T>
std::string NumberToString(T Number) {
    std::ostringstream ss;
    ss << Number;
    return ss.str();
}

int nearint(double a) {
    return ceil( a ) - a < 0.5 ? ceil( a ) : floor( a );
}

VoriConfig *sConfig;

int main(int argc, char *argv[]) {
    // 参数解析和配置初始化
    if (argc < 2) {
        cout << "Usage " << argv[0]
             << " RGBimage.png <resolution door_wide corridor_wide noise_precentage(0-100) record_time(0 or 1)>"
             << endl;
        return 255;
    }
    double door_wide = 1.15, corridor_wide = 2, res = 0.05;
    double noise_percent = 1.5;
    bool record_time = false;
    if (argc > 2) {
        res = atof( argv[2] );
        if (argc > 4) {
            door_wide = atof( argv[3] ) == -1 ? 1.15 : atof( argv[3] );
            corridor_wide = atof( argv[4] ) == -1 ? 1.35 : atof( argv[4] );

            if (argc > 5) {
                noise_percent = atof( argv[5] );
                if (argc > 6)
                    record_time = true;
            }
        }
    }

    // 配置参数设定
    sConfig = new VoriConfig();
    // 增大alphaShapeRemovalSquaredSize的值（默认625）到900-1000，这样可以减少过度分割
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = 900;
    sConfig->doubleConfigVars["firstDeadEndRemovalDistance"] = 100000;
    sConfig->doubleConfigVars["secondDeadEndRemovalDistance"] = -100000;
    sConfig->doubleConfigVars["thirdDeadEndRemovalDistance"] = 0.25 / res;
    sConfig->doubleConfigVars["fourthDeadEndRemovalDistance"] = 8;
    sConfig->doubleConfigVars["topoGraphAngleCalcEndDistance"] = 10;
    sConfig->doubleConfigVars["topoGraphAngleCalcStartDistance"] = 3;
    sConfig->doubleConfigVars["topoGraphAngleCalcStepSize"] = 0.1;
    sConfig->doubleConfigVars["topoGraphDistanceToJoinVertices"] = 10;
    // 增大topoGraphMarkAsFeatureEdgeLength的值（当前为16）到20-24，这样可以减少特征边的生成
    sConfig->doubleConfigVars["topoGraphMarkAsFeatureEdgeLength"] = 20;
    sConfig->doubleConfigVars["voronoiMinimumDistanceToObstacle"] = 0.25 / res;
    sConfig->doubleConfigVars["topoGraphDistanceToJoinVertices"] = 4;

    // ----------------------------------------------------------------------------
    clock_t start;
    start = clock();

    // Preprocess: Denoise (注意,如果过度clean,将导致多边形黑色边线不完整,所以正如Readme所言,对于比较干净的图,可以将命令行的最后一个参数设置为0)
    int black_threshold = 210;
    bool de = DenoiseImg( argv[1], "clean.png", black_threshold, 18, noise_percent );
    if (de)
        cout << "Denoise run successed!!" << endl;

    clock_t afterDenoise = clock();
    // ----------------------------------------------------------------------------
    // Preprocess: Furniture removal using Alpha Shape

    // QImage类是一个基于像素的图像处理类，限定了输入图像为png格式
    QImage test;
    test.load( "clean.png" );

    bool isTriple;
    analyseImage( test, isTriple );

    double AlphaShapeSquaredDist =
            (sConfig->voronoiMinimumDistanceToObstacle()) * (sConfig->voronoiMinimumDistanceToObstacle());
    performAlphaRemoval( test, AlphaShapeSquaredDist, MAX_PLEN_REMOVAL );
    test.save( "afterAlphaRemoval.png" );

    clock_t afterAlphaRemoval = clock();
    std::vector<topo_geometry::point> sites;
    bool ret = getSites( test, sites );


    int remove_alpha_value = 3600;
    // strategy of alpha param.
    double a = door_wide < corridor_wide ? door_wide + 0.1 : corridor_wide - 0.1;
    int alpha_value = ceil( a * a * 0.25 / (res * res));
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = alpha_value;
    std::cout << "a = " << a << ", where alpha = " << alpha_value << std::endl;
    clock_t loop_start = clock();
    // create the voronoi graph and vori graph
    VoriGraph voriGraph;
    ret = createVoriGraph( sites, voriGraph, sConfig );
    printGraphStatistics( voriGraph );
    // -----------------------------------------------------------------------------
    clock_t generatedVG = clock();
    QImage alpha = test;
    AlphaShapePolygon alphaSP, tem_alphaSP;
    AlphaShapePolygon::Polygon_2 *poly = alphaSP.performAlpha_biggestArea( alpha, remove_alpha_value, true );
    if (poly) {
        cout << "Removing vertices outside of polygon" << endl;
        removeOutsidePolygon( voriGraph, *poly );
    }
    AlphaShapePolygon::Polygon_2 *tem_poly = tem_alphaSP.performAlpha_biggestArea( alpha,
                                                                                   sConfig->alphaShapeRemovalSquaredSize(),
                                                                                   false );
    voriGraph.joinHalfEdges_jiawei();
    cout << "size of Polygons: " << tem_alphaSP.sizeOfPolygons() << endl;
    // -----------------------------------------------------------------------------
    // Remove small edges
    clock_t rmOut = clock();
    std::list<std::list<VoriGraphHalfEdge>::iterator> zeroHalfEdge;
    for (std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = voriGraph.halfEdges.begin();
         pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
        if (pathEdgeItr->distance <= EPSINON) {
            zeroHalfEdge.push_back( pathEdgeItr );
        }
    }
    for (std::list<std::list<VoriGraphHalfEdge>::iterator>::iterator zeroHalfEdgeItr = zeroHalfEdge.begin();
         zeroHalfEdgeItr != zeroHalfEdge.end(); zeroHalfEdgeItr++) {
        voriGraph.removeHalfEdge_jiawei( *zeroHalfEdgeItr );
    }
    // -----------------------------------------------------------------------------
    // Remove dead ends
    clock_t zeroHf = clock();
    if (sConfig->firstDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon( voriGraph,
                                         sConfig->firstDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
    if (sConfig->secondDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon( voriGraph, sConfig->secondDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }

    gernerateGroupId( voriGraph );
    keepBiggestGroup( voriGraph );

    removeRays( voriGraph );
    voriGraph.joinHalfEdges_jiawei();

    if (sConfig->thirdDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon( voriGraph, sConfig->thirdDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
//         printGraphStatistics(voriGraph, "Third dead ends");
    }
    if (sConfig->fourthDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon( voriGraph, sConfig->fourthDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
//         printGraphStatistics(voriGraph, "Fourth dead ends");
    }
    // ----------------------------------------------------------------------------------------------
    clock_t DeadEndRemoval = clock();

    // Room Detection
    RoomDect roomtest;
    roomtest.forRoomDect( tem_alphaSP, voriGraph, tem_poly );

    clock_t roomDetect = clock();

    // 保存彩色区域图
    QImage dectRoom = test;
    paintVori_onlyArea(dectRoom, voriGraph);
    string tem_s = NumberToString(nearint(a * 100)) + ".png";
    dectRoom.save(tem_s.c_str());
    
    // 添加黑白轮廓输出
    QImage outlineRoom = test;
    paintVori_OnlyOutline(outlineRoom, voriGraph);
    string outline_name = NumberToString(nearint(a * 100)) + "_outline.png";
    if(!outlineRoom.save(outline_name.c_str())) {
        std::cout << "Failed to save outline image to: " << outline_name << std::endl;
    } else {
        std::cout << "Successfully saved outline image to: " << outline_name << std::endl;
    }

    //-----------------------------------------------------------------------------------------------
    // Region Merge
    clock_t beforeMerge = clock();

    RMG::AreaGraph RMGraph( voriGraph );
    RMGraph.mergeAreas();
    RMGraph.mergeRoomCell();
    RMGraph.prunning();
    RMGraph.arrangeRoomId();
    RMGraph.show();

    clock_t geneAG = clock();
    double t_wholeloop = geneAG - start;

    RMGraph.mergeRoomPolygons();
    std::cout << "Area Graph generation use time (including denoising pre-processiong): " << t_wholeloop / CLOCKS_PER_SEC << std::endl;
    std::cout << "Area Graph generation use time: " << (double)(geneAG-afterAlphaRemoval) / CLOCKS_PER_SEC << std::endl;

//    QImage RMGIm = test;
//    RMGraph.draw( RMGIm );
//    RMGIm.save( "roomGraph.png" );
    return 0;
}
