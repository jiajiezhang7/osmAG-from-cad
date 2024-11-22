#include "RoomDect.h"

#include "cgal/CgalVoronoi.h"

#include "TopoGraph.h"

#define thresholdForCross 0.0001

#define thresholdForCutLength 0.001

#define divide 10

#define mergeLenThreshold 48 //20

using namespace std;

//extern VoriConfig *sConfig;


//void coutpoint_RD(topo_geometry::point p) {
//    double x, y;
//    x = topo_geometry::getX(p);
//    y = topo_geometry::getY(p);
//    std::cout << "(" << x << ", " << y << ") ";
//}
bool RoomDect::cutDist(VoriGraphHalfEdge *edge, Polygon_2 *polygon, std::vector<double> &distance) {
    distance.clear();
    if (edge->source && edge->target && !(edge->isRay())) {
        topo_geometry::point subSource;
        topo_geometry::point subTarget;
        for (int i = 0; i < divide; i++) {
            // divide the edge(VoriGraphHalfEdge) into 10 part
            edge->getPointForDistance((edge->distance) * i / divide, subSource);
            edge->getPointForDistance((edge->distance) * (i + 1) / divide, subTarget);

            CgalVoronoi::Point_2 pSource(topo_geometry::getX(subSource), topo_geometry::getY(subSource));
            CgalVoronoi::Point_2 pTarget(topo_geometry::getX(subTarget), topo_geometry::getY(subTarget));

            if ((polygon->bounded_side(pSource) == CGAL::ON_UNBOUNDED_SIDE) !=
                (polygon->bounded_side(pTarget) ==
                 CGAL::ON_UNBOUNDED_SIDE)) {    //one of this two point is out of the polygon
                //fordebug++;

                int div = 2;
                double subCut = (edge->distance) / (divide * div);
                double cutLength = (edge->distance) * i / divide + subCut;
                topo_geometry::point subMiddle;

                while (true) {//用二分法找到该路径处于房间边界上的点，cutLength：该点距离source的距离
                    if (subCut < thresholdForCross)break;
                    edge->getPointForDistance(cutLength, subMiddle);
                    CgalVoronoi::Point_2 pMiddle(topo_geometry::getX(subMiddle), topo_geometry::getY(subMiddle));
                    if ((polygon->bounded_side(pMiddle) == CGAL::ON_UNBOUNDED_SIDE) ==
                        (polygon->bounded_side(pTarget) == CGAL::ON_UNBOUNDED_SIDE)) {

                        pTarget = pMiddle;
                        subCut /= div;
                        cutLength -= subCut;
                    } else {

                        pSource = pMiddle;
                        subCut /= div;
                        cutLength += subCut;
                    }
                }


                if (cutLength >= thresholdForCutLength && edge->distance - cutLength >= thresholdForCutLength) {
                    distance.push_back(cutLength);
                }
            }
        }
        //cout<<"-------------------------------------------------------"<<endl;
        if (distance.size() == 0) {
            return false;
        } else {
            return true;
        }

    } else {
        return false;
    }
}

//used during cutEdgeCrossingPolygons
void RoomDect::setRoomIDForNonRoomVertex(VoriGraphHalfEdge *edge, Polygon_2 *polygon,
                                         int index) {
    CgalVoronoi::Point_2 source(topo_geometry::getX(edge->source->point),
                                topo_geometry::getY(edge->source->point));
    CgalVoronoi::Point_2 target(topo_geometry::getX(edge->target->point),
                                topo_geometry::getY(edge->target->point));
    // source in polygon i not roomVertex
    if (polygon->bounded_side(source) == CGAL::ON_BOUNDED_SIDE
        && !(edge->source->isRoomVertex())) {
        edge->source->setRoomId(index);
    }
    //target in polygon i not roomVertex
    if (polygon->bounded_side(target) == CGAL::ON_BOUNDED_SIDE && !(edge->target->isRoomVertex())) {
        edge->target->setRoomId(index);
    }
//    std::cout<<"room id of "<<edge->source->point.x()<<", "<<edge->source->point.y()<<" is "<<edge->source->roomId<<std::endl;
}


void RoomDect::setRoomIDForPath(VoriGraph &voriGraph, AlphaShapePolygon &alphaSP) {
    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr;
    for (pathEdgeItr = voriGraph.halfEdges.begin(); pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
        unsigned int sourceId = pathEdgeItr->source->getRoomId();
        unsigned int targetId = pathEdgeItr->target->getRoomId();
        //situations:
        if (sourceId == targetId) {
            //1. source and target all in the same polygon (or at it's border) ---> set path's roomid = source/target's roomid
            if (sourceId != -1) {
                pathEdgeItr->setRoomId(sourceId);
                if (pathEdgeItr->twin) {
                    pathEdgeItr->twin->setRoomId(sourceId);
                } else {
                }
            }
            //2. source and target all out of any polygon ---> ignore
        } else {
            //3. if deadend and not long, put it in the room
            if (pathEdgeItr->deadEnd &&
                (pathEdgeItr->target->edgesConnected.size() == 2 || pathEdgeItr->source->edgesConnected.size() == 2)) {
                //for merge later
                //double rate = boost::geometry::distance(pathEdgeItr->source->point,pathEdgeItr->target->point)/(pathEdgeItr->distance);
                double len = pathEdgeItr->distance;
//                if (len < mergeLenThreshold) {
                if (1) {
                    pathEdgeItr->setRoomId((sourceId == -1) ? targetId : sourceId);
//                    std::cout<<"roomid of path ("<<pathEdgeItr->source->point.x()<<","<<pathEdgeItr->source->point.y()<<") - ("
//                             <<pathEdgeItr->target->point.x()<<","<<pathEdgeItr->target->point.y()
//                             <<") is "<<pathEdgeItr->roomId<<std::endl;
                    if (pathEdgeItr->twin) {
                        pathEdgeItr->twin->setRoomId((sourceId == -1) ? targetId : sourceId);
                    } else {
                    }
                }
                else{ //added by jiawei
                    std::cout<<"path ("<<pathEdgeItr->source->point.x()<<","<<pathEdgeItr->source->point.y()<<") - ("
                             <<pathEdgeItr->target->point.x()<<","<<pathEdgeItr->target->point.y()
                             <<") is a deadend but longer than mergeLenThreshold, so no roomID..."<<std::endl;
//                    if((sourceId == -1)||(targetId == -1)){
//                        pathEdgeItr->setRoomId((sourceId == -1) ? targetId : sourceId );
//                        if (pathEdgeItr->twin) {
//                            pathEdgeItr->twin->setRoomId((sourceId == -1) ? targetId : sourceId );
//                        }
//                    }
                }
            }
            else{//added by jiawei
//                std::cout<<"roomid of path ("<<pathEdgeItr->source->point.x()<<","<<pathEdgeItr->source->point.y()<<") - ("
//                         <<pathEdgeItr->target->point.x()<<","<<pathEdgeItr->target->point.y()<<")'s sourceID = "<<pathEdgeItr->source->roomId
//                         <<", targetID = "<<pathEdgeItr->target->roomId<<std::endl;

                if(sourceId==-1||targetId==-1){
                    pathEdgeItr->setRoomId((sourceId == -1) ? targetId : sourceId);
                    if (pathEdgeItr->twin) {
                        pathEdgeItr->twin->setRoomId((sourceId == -1) ? targetId : sourceId);
                    }

                }else {
                    AlphaShapePolygon::Polygon_2 tempAS_source = alphaSP.getPolygon( pathEdgeItr->source->roomId );
                    AlphaShapePolygon::Polygon_2 tempAS_target = alphaSP.getPolygon( pathEdgeItr->target->roomId );
                    double source_area = fabs( tempAS_source.area());
                    double target_area = fabs( tempAS_target.area());
                    pathEdgeItr->setRoomId((source_area < target_area) ? targetId : sourceId );
                    if (pathEdgeItr->twin) {
                        pathEdgeItr->twin->setRoomId((source_area < target_area) ? targetId : sourceId );
                    }
//                    std::cout<<"area are "<<tempAS_source.area()<<" and "<<tempAS_target.area()<<std::endl;

                }
//                std::cout<<"room id is "<<pathEdgeItr->roomId<<std::endl;
            }
            //3. this only happens when source and target are on different polygons' border ---> ignore
        }
    }
}

void RoomDect::mergeDeadEndInRoom_polygon(VoriGraph &voriGraph) {
    std::map<topo_geometry::point, VoriGraphVertex>::iterator itr = voriGraph.vertices.begin();
    while (true) {
        // check that there are only 4 halfEdges and it's a room vertex
        VoriGraphHalfEdge *deadEndPath = 0;
        VoriGraphHalfEdge *nonDeadEndPath = 0;

        VoriGraphHalfEdge *deadEndPathTwin = 0;
        VoriGraphHalfEdge *nonDeadEndPathTwin = 0;

        int deadEndCounter = 0;
        int nonDeadEndCounter = 0;
        int mergeCounter = 0;
        if (itr->second.edgesConnected.size() == 4 && itr->second.isRoomVertex()) {
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if((*itr2)->isRay())continue;
                if ((*itr2)->deadEnd) {
                    if (deadEndCounter == 0) {
                        deadEndPath = *itr2;
                    }
                    deadEndCounter++;
                } else {
                    if (nonDeadEndCounter == 0) {
                        nonDeadEndPath = *itr2;
                    }
                    nonDeadEndCounter++;
                }
            }

            if (deadEndCounter == 2 && nonDeadEndCounter == 2) {
                //curvy
                if (deadEndPath->getRoomId() == nonDeadEndPath->getRoomId()) {
                    if(deadEndPath->twin)
                    deadEndPathTwin = deadEndPath->twin;
                    else {itr++;continue;}
                    if(nonDeadEndPath->twin)
                    nonDeadEndPathTwin = nonDeadEndPath->twin;
                    else {itr++;continue;}
                    if (deadEndPath->source == nonDeadEndPath->source) {
                        voriGraph.joinHalfEdges_jiawei(nonDeadEndPathTwin, deadEndPath, true);
                        voriGraph.joinHalfEdges_jiawei(deadEndPathTwin, nonDeadEndPath, true);
                        itr = voriGraph.vertices.begin();
                    } else {
                        if (deadEndPath->source == nonDeadEndPath->target) {
                            voriGraph.joinHalfEdges_jiawei(nonDeadEndPath, deadEndPath, true);
                            voriGraph.joinHalfEdges_jiawei(deadEndPathTwin, nonDeadEndPathTwin, true);
                            itr = voriGraph.vertices.begin();
                        } else {
                            if (deadEndPath->target == nonDeadEndPath->source) {
                                voriGraph.joinHalfEdges_jiawei(deadEndPath, nonDeadEndPath, true);
                                voriGraph.joinHalfEdges_jiawei(nonDeadEndPathTwin, deadEndPathTwin, true);
                                itr = voriGraph.vertices.begin();
                            } else {
                                if (deadEndPath->target == nonDeadEndPath->target) {
                                    voriGraph.joinHalfEdges_jiawei(deadEndPath, nonDeadEndPathTwin, true);
                                    voriGraph.joinHalfEdges_jiawei(nonDeadEndPath, deadEndPathTwin, true);
                                    itr = voriGraph.vertices.begin();
                                }
                            }
                        }
                    }
                }
            }
        }
        itr++;
        if (itr == voriGraph.vertices.end())break;
    }
    voriGraph.markDeadEnds();
//     voriGraph.markDeadEnds_isRoomVertex();
}

void RoomDect::mergeDeadEndInRoom(VoriGraph &voriGraph) {
    std::map<topo_geometry::point, VoriGraphVertex>::iterator itr = voriGraph.vertices.begin();
    while (true) {
        // check that there are only 4 halfEdges and it's a room vertex
        VoriGraphHalfEdge *deadEndPath = 0;
        VoriGraphHalfEdge *nonDeadEndPath = 0;

        VoriGraphHalfEdge *deadEndPathTwin = 0;
        VoriGraphHalfEdge *nonDeadEndPathTwin = 0;

        int deadEndCounter = 0;
        int nonDeadEndCounter = 0;
        int mergeCounter = 0;
        if (itr->second.edgesConnected.size() == 4 && itr->second.isRoomVertex()) {
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->deadEnd) {
                    if (deadEndCounter == 0) {
                        deadEndPath = *itr2;
                    }
                    deadEndCounter++;
                } else {
                    if (nonDeadEndCounter == 0) {
                        nonDeadEndPath = *itr2;
                    }
                    nonDeadEndCounter++;
                }
            }

            if (deadEndCounter == 2 && nonDeadEndCounter == 2) {
                //curvy
                if (deadEndPath->getRoomId() == nonDeadEndPath->getRoomId()) {
                    deadEndPathTwin = deadEndPath->twin;
                    nonDeadEndPathTwin = nonDeadEndPath->twin;
                    if (deadEndPath->source == nonDeadEndPath->source) {
                        voriGraph.joinHalfEdges_tianyan(nonDeadEndPathTwin, deadEndPath, true);
                        voriGraph.joinHalfEdges_tianyan(deadEndPathTwin, nonDeadEndPath, true);
                        itr = voriGraph.vertices.begin();
                    } else {
                        if (deadEndPath->source == nonDeadEndPath->target) {
                            voriGraph.joinHalfEdges_tianyan(nonDeadEndPath, deadEndPath, true);
                            voriGraph.joinHalfEdges_tianyan(deadEndPathTwin, nonDeadEndPathTwin, true);
                            itr = voriGraph.vertices.begin();
                        } else {
                            if (deadEndPath->target == nonDeadEndPath->source) {
                                voriGraph.joinHalfEdges_tianyan(deadEndPath, nonDeadEndPath, true);
                                voriGraph.joinHalfEdges_tianyan(nonDeadEndPathTwin, deadEndPathTwin, true);
                                itr = voriGraph.vertices.begin();
                            } else {
                                if (deadEndPath->target == nonDeadEndPath->target) {
                                    voriGraph.joinHalfEdges_tianyan(deadEndPath, nonDeadEndPathTwin, true);
                                    voriGraph.joinHalfEdges_tianyan(nonDeadEndPath, deadEndPathTwin, true);
                                    itr = voriGraph.vertices.begin();
                                }
                            }
                        }
                    }
                }
            }
        }
        itr++;
        if (itr == voriGraph.vertices.end())break;
    }
    voriGraph.markDeadEnds();
}


void RoomDect::saveRooms(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph, Polygon_2 *poly) {
    //record the roomids
    roomidList.clear();
    for (unsigned int i = 0; i < alphaSP.sizeOfPolygons(); i++) {
        AlphaShapePolygon::Polygon_2 temp = alphaSP.getPolygon(i);
        //if a polygon has no vertices in it, do not push it into list

        if (temp != *poly) {
            VoriGraph::VertexMap::iterator vertItr = voriGraph.vertices.begin();
            while (vertItr != voriGraph.vertices.end()) {
                CgalVoronoi::Point_2 p(topo_geometry::getX(vertItr->first), topo_geometry::getY(vertItr->first));
                if (temp.bounded_side(p) == CGAL::ON_BOUNDED_SIDE)break;
                vertItr++;
            }
            if (vertItr != voriGraph.vertices.end()) {
                //cout<<vertCounter<<endl;
                roomidList.push_back(i);
            }
        }
    }

    //room exist
//    cout<<"roomidList.size()="<<roomidList.size()<<endl;
    if (roomidList.size() > 0) {
        for (std::list<unsigned int>::iterator roomidItr = roomidList.begin();
             roomidItr != roomidList.end(); roomidItr++) {
            unsigned int index = *roomidItr;
            voriRooms[index] = VoriGraph();
            //voriRooms.resize(voriRooms.size()+1);

            //make references
            VoriGraph &tempVoriRoom = voriRooms[index];
            std::map<VoriGraphVertex *, VoriGraphVertex *> &tempBroderVertexMap = roomMap[index];

            //把所有属于该room的voriGraph.halfEdges存到该room的VoriGraph中
            for (std::list<VoriGraphHalfEdge>::iterator halfEdgeItr = voriGraph.halfEdges.begin();
                 halfEdgeItr != voriGraph.halfEdges.end(); halfEdgeItr++) {
                //with certain roomid , not ray
                if (halfEdgeItr->getRoomId() == index && !(halfEdgeItr->isRay()) && halfEdgeItr->source &&
                    halfEdgeItr->target) {
                    topo_geometry::point source = halfEdgeItr->source->point;
                    topo_geometry::point target = halfEdgeItr->target->point;

                    //halfedge initialization
                    VoriGraphHalfEdge tempVoriHalfEdge;
                    VoriGraphVertex tempSource;
                    VoriGraphVertex tempTarget;

                    tempVoriHalfEdge.distance = halfEdgeItr->distance;
                    tempVoriHalfEdge.deadEnd = halfEdgeItr->deadEnd;
                    tempVoriHalfEdge.groupId = halfEdgeItr->groupId;
                    tempVoriHalfEdge.obstacleAverage = halfEdgeItr->obstacleAverage;
                    tempVoriHalfEdge.obstacleMinimum = halfEdgeItr->obstacleMinimum;
                    tempVoriHalfEdge.setRoomId(halfEdgeItr->getRoomId());
                    tempVoriHalfEdge.twin = 0;


                    //halfedge push
                    for (std::list<topo_geometry::Halfedge>::iterator halfItr = halfEdgeItr->pathEdges.begin();
                         halfItr != halfEdgeItr->pathEdges.end(); halfItr++) {
                        tempVoriHalfEdge.pathEdges.push_back(*halfItr);
                    }
                    tempVoriRoom.halfEdges.push_back(tempVoriHalfEdge);

                    std::list<VoriGraphHalfEdge>::iterator edgeItr = --tempVoriRoom.halfEdges.end();

                    VoriGraphHalfEdge *tempEdgeConnected = &*edgeItr;

                    VoriGraph::VertexMap::iterator sourcePos = tempVoriRoom.vertices.find(source);
                    VoriGraph::VertexMap::iterator targetPos = tempVoriRoom.vertices.find(target);

                    //not found in the map? put vertices with no edges to map
                    if (sourcePos == tempVoriRoom.vertices.end()) {
                        tempSource.point = halfEdgeItr->source->point;
                        tempSource.groupId = halfEdgeItr->source->groupId;
                        tempSource.obstacleDist = halfEdgeItr->source->obstacleDist;
                        tempSource.roomVertex = halfEdgeItr->source->roomVertex;
                        tempSource.setRoomId(halfEdgeItr->source->getRoomId());
                        tempSource.borderVertex = halfEdgeItr->source->borderVertex;
                        tempVoriRoom.vertices[source] = tempSource;
                    }

                    if (targetPos == tempVoriRoom.vertices.end()) {
                        tempTarget.point = halfEdgeItr->target->point;
                        tempTarget.groupId = halfEdgeItr->target->groupId;
                        tempTarget.obstacleDist = halfEdgeItr->target->obstacleDist;
                        tempTarget.roomVertex = halfEdgeItr->target->roomVertex;
                        tempTarget.setRoomId(halfEdgeItr->target->getRoomId());
                        tempTarget.borderVertex = halfEdgeItr->target->borderVertex;
                        tempVoriRoom.vertices[target] = tempTarget;
                    }

                    sourcePos = tempVoriRoom.vertices.find(source);
                    targetPos = tempVoriRoom.vertices.find(target);
                    //update new source and target
                    tempEdgeConnected->source = &(sourcePos->second);
                    tempEdgeConnected->target = &(targetPos->second);

                    sourcePos->second.edgesConnected.push_back(tempEdgeConnected);
                    targetPos->second.edgesConnected.push_back(tempEdgeConnected);


                    //for map
                    if (tempEdgeConnected->source->isBorderVertex()) {
                        tempBroderVertexMap[tempEdgeConnected->source] = halfEdgeItr->source;
                    }

                    if (tempEdgeConnected->target->isBorderVertex()) {
                        tempBroderVertexMap[tempEdgeConnected->target] = halfEdgeItr->target;
                    }
                }
            }

            for (VoriGraph::VertexMap::iterator vtxitr = tempVoriRoom.vertices.begin();
                 vtxitr != tempVoriRoom.vertices.end(); vtxitr++) {
                vtxitr->second.markTwins();
            }
            gernerateGroupId(tempVoriRoom);
            tempVoriRoom.markDeadEnds();

        }
    }
}

void RoomDect::roomCenterCalc(AlphaShapePolygon &alphaSP, int roomIndex, double &centerX, double &centerY) {
    //TODO:calculate the center of room, go through the vertices in the room saved	
    //Method: from https://en.wikipedia.org/wiki/Centroid#Centroid_of_polygon

    double divider = 0;

    Vertex_iterator vItr = alphaSP.getPolygon(roomIndex).vertices_begin();

    while (true) {
        Vertex_iterator first = vItr;
        Vertex_iterator next = ++vItr;
        if (next == alphaSP.getPolygon(roomIndex).vertices_end()) {
            next = alphaSP.getPolygon(roomIndex).vertices_begin();
            centerX += ((first->x()) + (next->x())) * ((first->x()) * (next->y()) - (next->x()) * (first->y()));
            centerY += ((first->y()) + (next->y())) * ((first->x()) * (next->y()) - (next->x()) * (first->y()));
            divider += ((first->x()) * (next->y()) - (next->x()) * (first->y())) * 3;
            break;
        } else {
            centerX += ((first->x()) + (next->x())) * ((first->x()) * (next->y()) - (next->x()) * (first->y()));
            centerY += ((first->y()) + (next->y())) * ((first->x()) * (next->y()) - (next->x()) * (first->y()));
            divider += ((first->x()) * (next->y()) - (next->x()) * (first->y())) * 3;
        }
    }
    centerX /= divider;
    centerY /= divider;
}

void RoomDect::generateNewRoom(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph) {
    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr;
    VoriGraph::VertexMap::iterator vertexItr;
    for (std::map<unsigned int, VoriGraph>::iterator roomItr = voriRooms.begin();
         roomItr != voriRooms.end(); roomItr++) {
        pathEdgeItr = voriGraph.halfEdges.begin();

        //delete all paths belongs to a certain room
        while (true) {
            if (pathEdgeItr->getRoomId() == roomItr->first) {
                //remove halfedge
                voriGraph.removeHalfEdge_tianyan(pathEdgeItr, true, false);
            } else {
                pathEdgeItr++;
            }
            if (pathEdgeItr == voriGraph.halfEdges.end())break;
        }

        //center vertex
        VoriGraphVertex roomCenter;
        //mark as center
        roomCenter.markRoomCenter();
        //set room id
        roomCenter.setRoomId(roomItr->first);

        //center of room
        double roomCenterX = 0.;
        double roomCenterY = 0.;

        //calculate center
        roomCenterCalc(alphaSP, roomItr->first, roomCenterX, roomCenterY);

        //set center
        topo_geometry::point center(roomCenterX, roomCenterY);

        roomCenter.point = center;
        //push into vertices map
        voriGraph.vertices[center] = roomCenter;

        //go through the vorigraph to find the border
        for (vertexItr = voriGraph.vertices.begin(); vertexItr != voriGraph.vertices.end(); vertexItr++) {
            //border vertex with a certain room id
            double distanceCenter = boost::geometry::distance(center, vertexItr->first);
            if (vertexItr->second.getRoomId() == roomItr->first && vertexItr->second.isBorderVertex()) {

                //obstacles need to be set later!!!
                //topo half edge from border to center
                //what does 1 mean?
                topo_geometry::Halfedge topo_pathToCenter(vertexItr->first, center, center, 1);
                //topo half edge from center to border
                topo_geometry::Halfedge topo_pathToCenterTwin(center, vertexItr->first, center, 1);

                //push back a new vorihalfedge
                voriGraph.halfEdges.push_back(VoriGraphHalfEdge());
                //point to the new edge
                std::list<VoriGraphHalfEdge>::reverse_iterator pushedPathItr = voriGraph.halfEdges.rbegin();
                //push back pathEdge
                pushedPathItr->pathEdges.push_back(topo_pathToCenter);
                //set target
                pushedPathItr->target = &(voriGraph.vertices[center]);
                //set source
                pushedPathItr->source = &(vertexItr->second);
                //set distance
                pushedPathItr->distance = topo_pathToCenter.dist();

                //set roomid
                pushedPathItr->setRoomId(roomItr->first);
                //marked as room path
                pushedPathItr->markRoomPath();

                //push back a new vorihalfedge(twin)
                voriGraph.halfEdges.push_back(VoriGraphHalfEdge());
                //point to the new edge
                std::list<VoriGraphHalfEdge>::reverse_iterator pushedPathItrTwin = voriGraph.halfEdges.rbegin();
                //push back pathEdge
                pushedPathItrTwin->pathEdges.push_back(topo_pathToCenterTwin);
                //set target
                pushedPathItrTwin->target = &(vertexItr->second);
                //set source
                pushedPathItrTwin->source = &(voriGraph.vertices[center]);
                //set distance
                pushedPathItrTwin->distance = topo_pathToCenterTwin.dist();

                //set roomid
                pushedPathItrTwin->setRoomId(roomItr->first);
                //marked as room path
                pushedPathItrTwin->markRoomPath();

                //markTwin
                pushedPathItr->twin = &*pushedPathItrTwin;
                pushedPathItrTwin->twin = &*pushedPathItr;

                //push to the center vertex connected list
                voriGraph.vertices[center].edgesConnected.push_back(&*pushedPathItr);
                voriGraph.vertices[center].edgesConnected.push_back(&*pushedPathItrTwin);
                vertexItr->second.edgesConnected.push_back(&*pushedPathItr);
                vertexItr->second.edgesConnected.push_back(&*pushedPathItrTwin);
                //voriGraph.vertices[center].markTwins();
            }
        }
    }
}

void removeBorderNonRoomVertex(VoriGraph &voriGraph) {
    for (std::list<VoriGraphHalfEdge>::iterator halfEdgeItr = voriGraph.halfEdges.begin();
         halfEdgeItr != voriGraph.halfEdges.end();) {
        VoriGraphVertex *source = halfEdgeItr->source;
        VoriGraphVertex *target = halfEdgeItr->target;
        if ((source->isBorderVertex() && !(source->isRoomVertex()) && target->isRoomCenter()) ||
            (target->isBorderVertex() && !(target->isRoomVertex()) && source->isRoomCenter())) {
            voriGraph.removeHalfEdge_tianyan(halfEdgeItr, false, true);
        } else {
            halfEdgeItr++;
        }
    }
}

void RoomDect::labelpassages(VoriGraph &voriGraph) {
    VoriGraph::VertexMap::iterator voriHalfVertexItr;
    for (voriHalfVertexItr = voriGraph.vertices.begin();
         voriHalfVertexItr != voriGraph.vertices.end(); ++voriHalfVertexItr) {

        if (voriHalfVertexItr->second.isRoomVertex()) {
            if (voriHalfVertexItr->second.edgesConnected.size() == 4) {
                std::list<VoriGraphHalfEdge *>::iterator halfEdgeItr = voriHalfVertexItr->second.edgesConnected.begin();
                int tem_roomid = (*halfEdgeItr)->getRoomId();
                for (; halfEdgeItr != voriHalfVertexItr->second.edgesConnected.end(); halfEdgeItr++) {
                    if ((*halfEdgeItr)->getRoomId() != tem_roomid) {
                        voriHalfVertexItr->second.passageVertex = true;
                        break;
                    }
                }
            }
        }
        if ((voriHalfVertexItr->second.edgesConnected.size() > 4
             && voriHalfVertexItr->second.getRoomId() == -1)) {
            voriHalfVertexItr->second.passageVertex = true;

        }
    }

}

void RoomDect::forRoomDect(AlphaShapePolygon &alphaSP,
                           VoriGraph &voriGraph,
                           AlphaShapePolygon::Polygon_2 *poly) {
    // input:
    // allphaSP.polygons: all alpha shapes
    std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > > edge_dist_map;
    int last_edm_size=0;
    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr;
    std::vector<double> dist;

    unsigned int sizeOfVectorBefore = voriGraph.vertices.size();
    int ff = 0;
    while (true) {
        for (unsigned int i = 0; i < alphaSP.sizeOfPolygons(); i++) {//遍历寻找要切割的点
            //is 0 always the biggest polygon?
            AlphaShapePolygon::Polygon_2 temp = alphaSP.getPolygon(i);
            if (temp != *poly) {
                for (pathEdgeItr = voriGraph.halfEdges.begin();
                     pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
                    if((pathEdgeItr->deadEnd&&pathEdgeItr->distance<20) || pathEdgeItr->isRay())continue;
                    VoriGraphHalfEdge *edgeElected = &*pathEdgeItr;
                    //not the biggest polygon
//                    cout<<"enter if (temp != *poly) ....."<<endl;
                    //check if the edgeElected intersects with the polygon i.
                    if (cutDist(edgeElected, &temp, dist))
                        //cutDist_Polygon： 需要切割返回true不需要切割返回false，dist为切割点与source的距离
                    {
                        for (std::vector<double>::iterator lengthItr = dist.begin();
                             lengthItr != dist.end(); lengthItr++) {
                            //push AlphaSP No. and the cutlength from source into the map
                            edge_dist_map[edgeElected].push_back(
                                    std::pair<unsigned int, double>(i, *lengthItr));//若某条边的list.size>1则被切了多次
//                            cout << "edge_dist_map["<<edgeElected->source->point.x()<<","<<edgeElected->source->point.y()
//                                 <<"-"<<edgeElected->target->point.x()<<","<<edgeElected->target->point.y()<<"].size() = "
//                                 << edge_dist_map[edgeElected].size() <<": "<< *dist.rbegin()<< endl;
                        }
                    }
                }
            }
        }
//        cout << "edge_dist_map.size() = " << edge_dist_map.size() << endl;
        if (edge_dist_map.size() == 0)break;
            // next 6 lines: jiawei
        else {
            if (edge_dist_map.size()==last_edm_size){ //< 3) {

                if (ff > 10) { break; }
                else { ff += 1; }
            }
        }
        last_edm_size=edge_dist_map.size();
        std::cout << "edge_dist_map.size() == " << edge_dist_map.size() << std::endl;


        //travse edge_dist_map, remove twin edges in the list
        for (std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator mapItr = edge_dist_map.begin();
             mapItr != edge_dist_map.end(); mapItr++) {
            std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator mapItr2 = edge_dist_map.begin();
            while (true) {
                mapItr2++;
                if ((mapItr2 == edge_dist_map.end()) || mapItr2->first == mapItr->first->twin)break;
            }

            if (mapItr2->first == mapItr->first->twin) {//mapItr2 != edge_dist_map.end()    //827modified
                edge_dist_map.erase(mapItr2);
            }
        }
//        std::cout<<"\n to cut edges in the list: \n";
//        for (std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator mapItr = edge_dist_map.begin();
//             mapItr != edge_dist_map.end(); mapItr++) {
//            coutpoint_RD(mapItr->first->source->point);std::cout<<" - ";coutpoint_RD(mapItr->first->target->point);
//        }std::cout<<std::endl;

        for (std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator it2 = edge_dist_map.begin();
             it2 != edge_dist_map.end(); ++it2) {
//            cout << "edge["<<it2->first->source->point.x()<<","<<it2->first->source->point.y()
//                 <<"->"<<it2->first->target->point.x()<<","<<it2->first->target->point.y()<<"] cut at "
//                 << it2->second.front().second<< endl;

            voriGraph.cutHalfEdgeAtDistance_Polygon( //只取it2->second.front()即只切一次
                    it2->second.front().second, it2->first, *(it2->first->source), it2->second.front().first);
            //参数列表：要切割的长度（与source距离），要切割的边，要切割的边的source，roomid

        }
//        break;
        //clear all for next loop
        dist.clear();
        edge_dist_map.clear();
    }//while(true)
    unsigned int sizeOfVectorAfter = voriGraph.vertices.size();

//    if (sizeOfVectorAfter > sizeOfVectorBefore) {
        for (int i = 0; i < alphaSP.sizeOfPolygons(); i++) {
            AlphaShapePolygon::Polygon_2 temp = alphaSP.getPolygon(i);
            for (pathEdgeItr = voriGraph.halfEdges.begin(); pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
                VoriGraphHalfEdge *edgeElected = &*pathEdgeItr;
                //not the biggest polygon
                if (temp != *poly) {//为edgeElected两个端点设置RoomId
                    setRoomIDForNonRoomVertex(edgeElected, &temp, i);
                }
            }
        }
        setRoomIDForPath(voriGraph, alphaSP);//set RoomID For Path whose sourceId==targetId 或 is deadend
        mergeDeadEndInRoom_polygon(voriGraph);  //会产生deadend不属于任何区域的情况
        labelpassages(voriGraph);
        saveRooms(alphaSP, voriGraph, poly);
//        generateNewRoom( alphaSP, voriGraph );
//        removeBorderNonRoomVertex( voriGraph );
//    }

    voriGraph.markDeadEnds();
}

void RoomDect::cutEdgeCrossingPolygons(AlphaShapePolygon &alphaSP, VoriGraph &voriGraph, Polygon_2 *poly) {

    std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > > edge_dist_map;
    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr;
    std::vector<double> dist;

    unsigned int sizeOfVectorBefore = voriGraph.vertices.size();
    //int c = 0;
    while (true) {
        //c++;
        //generate map for cut	
        for (unsigned int i = 0; i < alphaSP.sizeOfPolygons(); i++) {//遍历寻找要切割的点
            //is 0 always the biggest polygon?
            AlphaShapePolygon::Polygon_2 temp = alphaSP.getPolygon(i);
            for (pathEdgeItr = voriGraph.halfEdges.begin(); pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
                VoriGraphHalfEdge *edgeElected = &*pathEdgeItr;
                //not the biggest polygon
                if (temp != *poly) {
                    //check if the edgeElected intersects with the polygon i.

                    if (cutDist(edgeElected, &temp, dist)) {//需要切割返回true不需要切割返回false，dist为切割点与source的距离
                        for (std::vector<double>::iterator lengthItr = dist.begin();
                             lengthItr != dist.end(); lengthItr++) {
                            //push AlphaSP No. and the cutlength from source into the map
                            edge_dist_map[edgeElected].push_back(std::pair<unsigned int, double>(i, *lengthItr));
                        }
                    }
                }
            }
        }

        if (edge_dist_map.size() == 0)break;
        //travse edge_dist_map, remove twin edges in the list
        for (std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator mapItr = edge_dist_map.begin();
             mapItr != edge_dist_map.end(); mapItr++) {
            std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator mapItr2 = edge_dist_map.begin();
            while (true) {
                mapItr2++;
                if ((mapItr2 == edge_dist_map.end()) || mapItr2->first == mapItr->first->twin)break;
            }

            if (mapItr2 != edge_dist_map.end()) {
                edge_dist_map.erase(mapItr2);
            }
        }

        if (edge_dist_map.size() == 0)break;

        //cut
        for (std::map<VoriGraphHalfEdge *, std::list<std::pair<unsigned int, double> > >::iterator it2 = edge_dist_map.begin();
             it2 != edge_dist_map.end(); ++it2) {
            //cut the halfpath, give the middle vertex id, set it as room vertex
            //把要切的VoriGraphHalfEdge切成两段pathEdges，删除原来的pathEdges，根据分成的两段（若在首尾切割则为一段）
            // 对三个端点进行设置（包括markRoomVertex和setRoomId(i) ）
            voriGraph.cutHalfEdgeAtDistance(it2->second.front().second, it2->first, *(it2->first->source),
                                            it2->second.front().first);
        }

        //clear all for next loop
        dist.clear();
        edge_dist_map.clear();
    }
    unsigned int sizeOfVectorAfter = voriGraph.vertices.size();

    if (sizeOfVectorAfter > sizeOfVectorBefore) {
        for (int i = 0; i < alphaSP.sizeOfPolygons(); i++) {
            //is 0 always the biggest polygon?
            AlphaShapePolygon::Polygon_2 temp = alphaSP.getPolygon(i);
            for (pathEdgeItr = voriGraph.halfEdges.begin(); pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
                VoriGraphHalfEdge *edgeElected = &*pathEdgeItr;
                //not the biggest polygon
                if (temp != *poly) {//为edgeElected两个端点设置RoomId
                    setRoomIDForNonRoomVertex(edgeElected, &temp, i);
                }
            }
        }
        setRoomIDForPath(voriGraph,alphaSP);
        mergeDeadEndInRoom(voriGraph);
        saveRooms(alphaSP, voriGraph, poly);
        generateNewRoom(alphaSP, voriGraph);
        removeBorderNonRoomVertex(voriGraph);
    }

    voriGraph.markDeadEnds();
}

void RoomDect::drawPolygon(AlphaShapePolygon &alphaSP, QImage &pImg) {
    for (std::list<unsigned int>::iterator roomidItr = roomidList.begin(); roomidItr != roomidList.end(); roomidItr++) {
        alphaSP.drawPolygonByIndex(pImg, *roomidItr);
    }
}

