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
#include <sstream>
#include <sys/stat.h>
#include <sys/types.h>

#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>
#include <boost/filesystem.hpp>
#include <boost/iterator/filter_iterator.hpp>
#include <boost/filesystem/path.hpp>

#include <QApplication>
#include <QMessageBox>
#include <QImage>

#include "VoriGraph.h"
#include "TopoGraph.h"
#include "cgal/CgalVoronoi.h"
#include "cgal/AlphaShape.h"
#include "cgal/AlphaShapeRemoval.h"
#include "qt/QImageVoronoi.h"
#include "RoomDect.h"
#include "roomGraph.h"
#include "Denoise.h"


using namespace std;

template<typename T>
std::string NumberToString(T Number) {
    std::ostringstream ss;
    ss << Number;
    return ss.str();
}

int nearint(double a) {
    return ceil(a) - a < 0.5 ? ceil(a) : floor(a);
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
    
    // 默认参数设置
    double door_wide = 1.15;
    double corridor_wide = 2;
    double res = 0.05;
    double noise_percent = 1.5;
    bool record_time = false;
    
    // 从命令行读取参数
    if (argc > 2) {
        res = atof(argv[2]);
        if (argc > 4) {
            door_wide = atof(argv[3]) == -1 ? 1.15 : atof(argv[3]);
            corridor_wide = atof(argv[4]) == -1 ? 1.35 : atof(argv[4]);

            if (argc > 5) {
                noise_percent = atof(argv[5]);
                if (argc > 6)
                    record_time = true;
            }
        }
    }

    // 第0步：配置参数设定
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
    // 第1步: 预处理输入图像 
        // 输入 - grid_map.png -> argv[1]
        // 输出 - clean.png

    int black_threshold = 210;
    // 注意: 如果过度clean,将导致多边形黑色边线不完整, 对于比较干净的图,可以将命令行的最后一个参数设置为0
    bool is_denoise = DenoiseImg(argv[1], "clean.png", black_threshold, 18, noise_percent);
    if (is_denoise)
        cout << "Denoise run successed!!" << endl;
    
    // ----------------------------------------------------------------------------
    // 第2步: 移除家具 - 使用Alpha Shape算法
        // 输入 - clean.png -> test (QImage对象)
        // 输出 - afterAlphaRemoval.png

    QImage test;
    test.load("clean.png");

    bool isTriple;
    analyseImage(test, isTriple);

    double AlphaShapeSquaredDist = 
            (sConfig->voronoiMinimumDistanceToObstacle()) * (sConfig->voronoiMinimumDistanceToObstacle());
    // 关键函数，执行家具移除
    performAlphaRemoval(test, AlphaShapeSquaredDist, MAX_PLEN_REMOVAL);
    test.save("afterAlphaRemoval.png");

    // ----------------------------------------------------------------------------
    // 第3步： 提取障碍物点
        // 输入 - test  （处理后的图像）
        // 输出 - sites （障碍物点集合）

    std::vector<topo_geometry::point> sites;
    bool ret = getSites(test, sites);

    // ----------------------------------------------------------------------------
    // 第4步: Voronoi图生成
        // 输入 - sites - 障碍物点集
        // 输出 - voriGraph - Voronoi图结构 
    int remove_alpha_value = 3600;

    // alpha参数策略
    double a;
    if (door_wide < corridor_wide) {
        a = door_wide + 0.1;
    } else {
        a = corridor_wide - 0.1;
    }

    int alpha_value = ceil(a * a * 0.25 / (res * res));
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = alpha_value;
    std::cout << "a = " << a << ", where alpha = " << alpha_value << std::endl;
    
    VoriGraph voriGraph;
    // 关键函数 -- 创建 VoriGraph
    ret = createVoriGraph(sites, voriGraph, sConfig);

    // 统计一些参数作为调试输出
    printGraphStatistics(voriGraph);
    
    // -----------------------------------------------------------------------------
    // 第5步： Alpha Shape处理
        // 输入 - voriGraph 和 test图像
        // 输出 - 修改后的 voriGraph
    
    QImage alpha = test;
    AlphaShapePolygon alphaSP, tem_alphaSP;
    AlphaShapePolygon::Polygon_2 *poly = alphaSP.performAlpha_biggestArea(alpha, remove_alpha_value, true);
    if (poly) {
        cout << "Removing vertices outside of polygon" << endl;
        removeOutsidePolygon(voriGraph, *poly);
    }
    
    AlphaShapePolygon::Polygon_2 *tem_poly = tem_alphaSP.performAlpha_biggestArea(alpha, sConfig->alphaShapeRemovalSquaredSize(), false);

    // 修剪voriGraph
    voriGraph.joinHalfEdges_jiawei();
    cout << "size of Polygons: " << tem_alphaSP.sizeOfPolygons() << endl;
    

    // -----------------------------------------------------------------------------
    // 第6步: 拓扑图生成 voriGraph -> TopoGraph
        // 输入 - voriGraph
        // 输出 - 优化后的voriGraph
    std::list<std::list<VoriGraphHalfEdge>::iterator> zeroHalfEdge;

        // 移除零长度的边
    for (std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = voriGraph.halfEdges.begin();
         pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
        if (pathEdgeItr->distance <= EPSINON) {
            zeroHalfEdge.push_back(pathEdgeItr);
        }
    }
    
    for (std::list<std::list<VoriGraphHalfEdge>::iterator>::iterator zeroHalfEdgeItr = zeroHalfEdge.begin();
         zeroHalfEdgeItr != zeroHalfEdge.end(); zeroHalfEdgeItr++) {
        voriGraph.removeHalfEdge_jiawei(*zeroHalfEdgeItr);
    }
    
        // 移除死端
    if (sConfig->firstDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->firstDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
    
    if (sConfig->secondDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->secondDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
        // 保留最大连通分量
    gernerateGroupId(voriGraph);
    keepBiggestGroup(voriGraph);

    removeRays(voriGraph);
    voriGraph.joinHalfEdges_jiawei();

    if (sConfig->thirdDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->thirdDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
        // printGraphStatistics(voriGraph, "Third dead ends");
    }
    
    if (sConfig->fourthDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->fourthDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
        // printGraphStatistics(voriGraph, "Fourth dead ends");
    }
    
    // ----------------------------------------------------------------------------------------------
    // 第7步: 初始区域图生成 - 房间检测
        // 输入 - voriGraph 和 tem_alphaSP
        // 输出 - 带有房间信息的 voriGraph

    RoomDect roomtest;
    roomtest.forRoomDect(tem_alphaSP, voriGraph, tem_poly);


    // ----------------------------------------------------------------------------------------------

    // 保存彩色区域图
    QImage dectRoom = test;
    paintVori_onlyArea(dectRoom, voriGraph);
    string tem_s = NumberToString(nearint(a * 100)) + ".png";
    dectRoom.save(tem_s.c_str());
    

    // 保存黑白轮廓图
    QImage outlineRoom = test;
    paintVori_OnlyOutline(outlineRoom, voriGraph);
    string outline_name = NumberToString(nearint(a * 100)) + "_outline.png";
    if (!outlineRoom.save(outline_name.c_str())) {
        std::cout << "Failed to save outline image to: " << outline_name << std::endl;
    } else {
        std::cout << "Successfully saved outline image to: " << outline_name << std::endl;
    }

    //-----------------------------------------------------------------------------------------------
    // TODO: 第8步: 区域合并 - 生成最终区域图 (也即经过优化后彩色区域图)

    RMG::AreaGraph RMGraph(voriGraph);
    RMGraph.mergeAreas();
    RMGraph.mergeRoomCell();
    RMGraph.prunning();
    RMGraph.arrangeRoomId();
    RMGraph.show();

    RMGraph.mergeRoomPolygons();

    QImage RMGIm = test;
    RMGraph.draw(RMGIm);
    RMGIm.save("roomGraph.png");
    
    // 导出为osmAG.xml格式
    std::cout << "正在导出为osmAG.xml格式..." << std::endl;
    RMGraph.exportToOsmAG("osmAG_optimized.osm");
    
    return 0;
}
