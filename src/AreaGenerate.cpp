//
// Created by houjiawei on 18-1-24.
//

// #include <ros/ros.h>
#include "AreaGenerate.h"

#define occupied_thresh 0.75
#define neighbors 8
#define percentage 0

void generateAreas(const char *input_name, const char *output_name, VoriConfig *sConfig, VoriGraph &voriGraph) {

    int black_threshold;
    black_threshold = round(255 * occupied_thresh);
    bool de = DenoiseImg(input_name, "clean.png", black_threshold, neighbors, percentage);
    if (de)
        cout << "Denoise run successed!!" << endl;

    QImage test;
    test.load("clean.png");
    bool isTriple;
    analyseImage(test, isTriple);
    cout << " is triple?: " << isTriple << endl;


    std::vector<topo_geometry::point> sites;
    bool ret = getSites(test, sites);

    // create the voronoi graph and vori graph
    ret = createVoriGraph(sites, voriGraph, sConfig);
//    printGraphStatistics(voriGraph);

    QImage alpha = test;
    AlphaShapePolygon alphaSP;
    AlphaShapePolygon::Polygon_2 *poly = alphaSP.performAlpha(alpha, sConfig->alphaShapeRemovalSquaredSize(), false);

    cout << "size of Polygons: " << alphaSP.sizeOfPolygons() << endl;
    if (poly) {
        cout << "Removing vertices outside of polygon" << endl;
        removeOutsidePolygon(voriGraph, *poly);   //Remove vertices outside of polygon
//        paintVori(alpha, voriGraph);
    }
    voriGraph.joinHalfEdges_jiawei();
//    alpha.save("alpha.png");

    std::list<std::list<VoriGraphHalfEdge>::iterator> zeroHalfEdge;

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

    if (sConfig->firstDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->firstDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
//         printGraphStatistics(voriGraph, "First dead ends");
    }
//    QImage filter = test;
//    paintVori_Area(filter, voriGraph);
//    filter.save("filter.png");

    if (sConfig->secondDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->secondDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
//    QImage filter2 = test;
//    paintVori_Area(filter2, voriGraph);
//    filter.save("filter2.png");

    gernerateGroupId(voriGraph);
    keepBiggestGroup(voriGraph);

    removeRays(voriGraph);
    voriGraph.joinHalfEdges_jiawei();

    if (sConfig->thirdDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->thirdDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
    if (sConfig->fourthDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->fourthDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }

//    QImage lastVori = test;
//    paintVori_Area(lastVori, voriGraph);
//    lastVori.save("lastVori.png");


    RoomDect roomtest;
    roomtest.forRoomDect(alphaSP, voriGraph, poly);

//    QImage after = test;
//    paintVori_pathFace(after, voriGraph);
//    after.save("after.png");

    QImage dectRoom = test;
    paintVori_AreaRoom(dectRoom, voriGraph);
    dectRoom.save(output_name);

    std::cout << "end generateAreas..." << std::endl;
}


void generateRMG(RMG::AreaGraph &RMGraph) {
    std::cout << "enter generateRMG" << std::endl;

    RMGraph.mergeAreas();
    RMGraph.arrangeRoomId();
//    RMGraph.show();

    RMGraph.mergeRoomPolygons();
}

