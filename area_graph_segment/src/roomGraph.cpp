#include "roomGraph.h"
#include "RoomDect.h"
//
//void coutpoint(topo_geometry::point p) {
//    double x, y;
//    x = topo_geometry::getX(p);
//    y = topo_geometry::getY(p);
//    std::cout << "(" << x << ", " << y << ") ";
//}

/*
 * class init
 */
RMG::AreaGraph::AreaGraph(VoriGraph &voriGraph) {
    //1. achieve those roomVertexes
    this->buildAreaGraph(voriGraph);
    //2. build a lineGraph
//    RMG::connectRoomVertexes(originSet);
}

/*
 * By Yijun
 *
RMG::roomGraph::roomGraph(VoriGraph &voriGraph){
    //1. achieve those roomVertexes
    RMG::build_oriSet(voriGraph, originSet);
    //2. build a lineGraph
    RMG::connectRoomVertexes(originSet);
}*/

RMG::roomVertex::roomVertex(int roomId, topo_geometry::point loc, topo_geometry::point st, topo_geometry::point ed)
        : roomId(roomId), center(loc), st(st), ed(ed) {
    parentV = NULL;
}

/*
 * roomVertex class function
 */
void RMG::roomVertex::init_areaInnerPPGraph() {
    for (std::list<VoriGraphHalfEdge *>::iterator it = this->areaInnerPathes.begin();
         it != this->areaInnerPathes.end(); it++) {
        PS::PPEdge *tmp_ppe = new PS::PPEdge((*it)->source, (*it)->target,
                                             (*it)->distance, &((*it)->pathEdges));
        this->areaInnerPPGraph.push_back(tmp_ppe);
    }
}




void RMG::AreaGraph::mergeAreas() {
    //1. traverse each roomVertex, find other points with the same roomId to put into roomToMerge,
    //   where build a new roomVertex as merged room to put at begin of roomToMerge
    //
    //Attention: the merged points will have roomId = -2 to indicate they are removed
    //          And also the new node don't have a in degree, will be build in the
    //          prunning step
    std::vector<roomVertex *> newNodeSet;//temporally store the new node
    std::map<int, std::vector<roomVertex *> > roomToMerge;

    for (std::vector<roomVertex *>::iterator it = originSet.begin(); it != originSet.end(); it++) {

        int groupRoomId = (*it)->roomId;
        //1.1 check
        if (groupRoomId == -1 or groupRoomId == -2)
            continue;   //because it is not belong to a roomCell or has already been chosed.

//        (*it)->roomId = -2;
        roomVertex *biggerRoom;
        std::map<int, std::vector<roomVertex *> >::iterator rM = roomToMerge.find(groupRoomId);
        if (rM == roomToMerge.end()) {   //a new roomId, we need to create a new roomVertex for a new big room
            roomVertex *tmp_bigroom(new roomVertex(groupRoomId, (*it)->center, (*it)->st, (*it)->ed));
            biggerRoom = tmp_bigroom;
            std::vector<roomVertex *> tmpVec; // store the vertexes with the same roomId
            tmpVec.push_back(biggerRoom);
            roomToMerge[groupRoomId] = tmpVec;
        } else {
            biggerRoom = *roomToMerge[groupRoomId].begin();
        }
        roomToMerge[groupRoomId].push_back(*it);
        for (std::list<VoriGraphHalfEdge *>::iterator inrm_ps_it = (*it)->areaInnerPathes.begin();
             inrm_ps_it != (*it)->areaInnerPathes.end(); inrm_ps_it++) {
            biggerRoom->areaInnerPathes.push_back(*inrm_ps_it);
            // to instead "biggerRoom->init_areaInnerPPGraph()": convert the halfedge into PPEdge
            PS::PPEdge *tmp_ppe(new PS::PPEdge((*inrm_ps_it)->source, (*inrm_ps_it)->target,
                                               (*inrm_ps_it)->distance, &((*inrm_ps_it)->pathEdges)));
            biggerRoom->areaInnerPPGraph.push_back(tmp_ppe);
        }
//        (*it)->parentV = biggerRoom;

        biggerRoom->polygons.insert(biggerRoom->polygons.end(), (*it)->polygons.begin(), (*it)->polygons.end());

        //2. check: if the passage is inside the big room, then it is not a passage of the big room, and delete the passage from roomGraph.passageEList;
        //          otherwise, delete the small area from passage.connectedAreas and add big room instead
        for (std::vector<passageEdge *>::iterator sitr = (*it)->passages.begin();
             sitr != (*it)->passages.end(); sitr++) {

            std::vector<roomVertex *>::iterator ritr;
            int rcnt = 0;
            bool innerpassage = true;
            for (std::vector<roomVertex *>::iterator vitr = (*sitr)->connectedAreas.begin();
                 vitr != (*sitr)->connectedAreas.end(); vitr++) {
                if (groupRoomId != (*vitr)->roomId) {
                    innerpassage = false;
                }
                rcnt++;
                ritr = vitr;
            }
            if (innerpassage == false) {    //not an inner passage
                if (rcnt > 1) {
                    bool first = true;
                    for (std::vector<roomVertex *>::iterator vitr = (*sitr)->connectedAreas.begin();
                         vitr != (*sitr)->connectedAreas.end();) {
                        if (groupRoomId == (*vitr)->roomId) {
                            if (first) {
                                first = false;
                                (*vitr) = biggerRoom;
                                vitr++;
                            } else {
                                (*sitr)->connectedAreas.erase(vitr);
                            }
                        } else {
                            vitr++;
                        }
                    }
                } else {  //Replace the original room with the bigger room
                    (*ritr) = biggerRoom;
                }
                biggerRoom->passages.push_back((*sitr));
            } else {  //a inner passage
                passageEList.remove(*sitr);
            }
        }

    }
    for (std::map<int, std::vector<roomVertex *> >::iterator mitr = roomToMerge.begin();
         mitr != roomToMerge.end(); mitr++) {
        std::vector<roomVertex *> tmpVec = mitr->second;

        //merge neigbhbours and polygons, point origin node to new node
        std::vector<roomVertex *>::iterator itr = tmpVec.begin();
        roomVertex *biggerRoom = *itr;
        itr++;
        for (; itr != tmpVec.end(); itr++) {
            roomVertex *rp = *itr;
            originSet.erase(std::remove(originSet.begin(), originSet.end(), (*itr)));
            delete rp;
        }
        originSet.push_back(biggerRoom);
    }
}


/*
 *roomGraph class function
 *
 */
void RMG::AreaGraph::mergeRoomCell() {
    //1. traverse each point, find other points with the same roomId
    //2. build a new roomGraph and build neighbours and polygons
    //Attention: the merged points will have roomId = -2 to indicate they are removed
    //          And also the new node don't have a in degree, will be build in the
    //          prunning step
    std::vector<roomVertex *> newNodeSet;//temporally store the new node

    for (std::vector<roomVertex *>::iterator it = originSet.begin();
         it != originSet.end(); it++) {

        int groupRoomId = (*it)->roomId;
        //1.1 check
        if (groupRoomId == -1 or groupRoomId == -2)
            continue;//because it is not belong to a roomCell or has already been chosed.


        //1.2 store the same roomId point
        std::vector<roomVertex *> tmpVec; // store the vertexes with the same roomId
        tmpVec.push_back((*it));
        (*it)->roomId = -2;


        std::vector<roomVertex *>::iterator itj = it;
        for (itj++; itj != originSet.end(); itj++) {
            //check
            if ((*itj)->roomId == -1 or (*itj)->roomId == -2)
                continue;//because it is not belong to a roomCell or has already been chosed.

            if ((*itj)->roomId == groupRoomId) {
                tmpVec.push_back((*itj));
                (*itj)->roomId = -2;
            }
        }

        //2 build a new roomV
        roomVertex *biggerRoom = new roomVertex(groupRoomId, (*(tmpVec.begin()))->center, (*(tmpVec.begin()))->st,
                                                (*(tmpVec.begin()))->ed);
        //append innerpathes into the new innerpathes list then transform to PPEdge list
        for (std::vector<roomVertex *>::iterator inrm_it = tmpVec.begin(); inrm_it != tmpVec.end(); inrm_it++) {
            for (std::list<VoriGraphHalfEdge *>::iterator inrm_ps_it = (*inrm_it)->areaInnerPathes.begin();
                 inrm_ps_it != (*inrm_it)->areaInnerPathes.end(); inrm_ps_it++) {
                biggerRoom->areaInnerPathes.push_back(*inrm_ps_it);
                biggerRoom->areaInnerPathes.push_back((*inrm_ps_it)->twin);
            }
        }
        biggerRoom->init_areaInnerPPGraph();

        //merge neigbhbours and polygons, point origin node to new node
        for (std::vector<roomVertex *>::iterator itr = tmpVec.begin(); itr != tmpVec.end(); itr++) {
            //biggerRoom->neighbours.merge((*itr)->neighbours);
            //biggerRoom->polygons.merge((*itr)->polygons);
            biggerRoom->neighbours.insert((*itr)->neighbours.begin(), (*itr)->neighbours.end());
            biggerRoom->polygons.insert(biggerRoom->polygons.begin(), (*itr)->polygons.begin(), (*itr)->polygons.end());
            (*itr)->parentV = biggerRoom;
        }
        newNodeSet.push_back(biggerRoom);
    }
    //merge new node into originSet
    originSet.insert(originSet.end(), newNodeSet.begin(), newNodeSet.end());
}

void RMG::AreaGraph::prunning() {
    //1. search each point to find if its neighbour have -2 roomId,
    //          if a neighbour is, rm this neighbour and point to its parent
    //          (the new node)
    //2. delete those point with -2 roomId
    //          (traverse through the originSet and build a delete vector in step one)
    std::set<roomVertex *> removeOriginSet;
    //1.
    for (std::vector<roomVertex *>::iterator it = originSet.begin(); it != originSet.end(); it++) {
        std::set<roomVertex *> removeNeibourSet;
        std::set<roomVertex *> insertNeibourSet;
        for (std::set<roomVertex *>::iterator its = (*it)->neighbours.begin();
             its != (*it)->neighbours.end(); its++) {
            if ((*its)->roomId == -2) {
                insertNeibourSet.insert((*its)->parentV);
                removeNeibourSet.insert((*its));
                removeOriginSet.insert((*its));
            }
        }
        //remove neighbour node
        for (std::set<roomVertex *>::iterator itr = removeNeibourSet.begin(); itr != removeNeibourSet.end(); itr++) {
            //(*it)->neighbours.extract((*itr));
            (*it)->neighbours.erase((*itr));
        }
        //insert neighbour node
        //(*it)->neighbours.merge(insertNeibourSet);
        (*it)->neighbours.insert(insertNeibourSet.begin(), insertNeibourSet.end());
        //clean the temporary set
        removeNeibourSet.clear();
        insertNeibourSet.clear();
    }

    //2. remove -2 node from originSet
    for (std::set<roomVertex *>::iterator itrmo = removeOriginSet.begin(); itrmo != removeOriginSet.end(); itrmo++) {
        originSet.erase(std::remove(originSet.begin(), originSet.end(), (*itrmo)), originSet.end());
    }
}

void RMG::AreaGraph::arrangeRoomId() {
    int roomId = 0;
    for (std::vector<roomVertex *>::iterator it = this->originSet.begin(); it != this->originSet.end(); it++) {
        (*it)->roomId = roomId++;
    }
}


void RMG::AreaGraph::show() {
    std::cout << "area number = " << (*this->originSet.rbegin())->roomId + 1 << std::endl;
//     for(std::vector<roomVertex*>::iterator it = this->originSet.begin(); it!=this->originSet.end(); it++){
//         std::cout << (*it)->roomId << " ";
//         if((*it)->parentV)
//             std::cout << "there is one room should be erased during prunning ";
//         std::cout << std::endl;
//     }
}

void RMG::AreaGraph::draw(QImage &image) {
    QPainter painter(&image);
    for (std::vector<roomVertex *>::iterator it = this->originSet.begin(); it != this->originSet.end(); it++) {

        //draw current polygons
        QBrush brush;
        QColor color = QColor(rand() % 255, rand() % 255, rand() % 255);
        brush.setColor(color);
        brush.setStyle(Qt::SolidPattern);
        painter.setBrush(brush);
        painter.setPen(color);

        QPolygon poly;
        for (std::list<topo_geometry::point>::iterator pointitr = (*it)->polygon.begin();
             pointitr != (*it)->polygon.end(); pointitr++) {
            int x = round(topo_geometry::getX(*pointitr));
            int y = round(topo_geometry::getY(*pointitr));
            //                    cout<<" point: "<<x<<", "<<y;
            poly << QPoint(x, y);
        }
        painter.drawPolygon(poly);
        //draw line
        for (std::set<roomVertex *>::iterator itj = (*it)->neighbours.begin(); itj != (*it)->neighbours.end(); itj++) {
            painter.setPen(qRgb(rand(), rand(), rand()));

            int x1 = (round(topo_geometry::getX((*itj)->center)));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY((*itj)->center)));
            int x2 = (round(topo_geometry::getX((*it)->center)));
            int y2 = (round(topo_geometry::getY((*it)->center)));
//        painter.drawLine(x1, y1, x2, y2);
        }
    }
}

//passage searching stuff




/*
 * AreaGraph namespace functions
 */
static bool equalLineVertex(const topo_geometry::point &a, const topo_geometry::point &b);

void RMG::connectRoomVertexes(std::vector<roomVertex *> &originSet) {
    for (std::vector<roomVertex *>::iterator it = originSet.begin();
         it != originSet.end(); it++) {
        topo_geometry::point st = (*it)->st;
        topo_geometry::point ed = (*it)->ed;
        std::vector<roomVertex *>::iterator tmpIt = it;//shoud double check (it should be a copy of it)
        for (std::vector<roomVertex *>::iterator itj = tmpIt;
             itj != originSet.end(); itj++) {
            if (equalLineVertex(st, (*itj)->st) ||
                equalLineVertex(st, (*itj)->ed) ||
                equalLineVertex(ed, (*itj)->st) ||
                equalLineVertex(ed, (*itj)->ed)) {

                (*it)->neighbours.insert((*itj));
                (*itj)->neighbours.insert((*it));
            }

        }


    }
}


//void RMG::build_oriSet(VoriGraph &voriGraph, std::vector<roomVertex *> &originSet) {
//    //build a line graph
//    std::set<VoriGraphHalfEdge *> halfEdgeSet;
//    for (std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr = voriGraph.halfEdges.begin();
//         voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr) {
//        if (voriHalfEdgeItr->isRay()) {
//            continue;
//        } else if (halfEdgeSet.find(&*voriHalfEdgeItr) == halfEdgeSet.end()) {
//            halfEdgeSet.insert(&*voriHalfEdgeItr);
//
//            VoriGraphPolygon *polygonPtr = voriHalfEdgeItr->pathFace;
//            int sumX = 0, sumY = 0;
//            if (polygonPtr != 0 /*&& polygonPtr->isRay*/) {
//                for (std::list<topo_geometry::point>::iterator pointitr = polygonPtr->polygonpoints.begin();
//                     pointitr != polygonPtr->polygonpoints.end();
//                     pointitr++) {
//                    sumX += round(topo_geometry::getX(*pointitr));
//                    sumY += round(topo_geometry::getY(*pointitr));
//                }
//
//                VoriGraphHalfEdge *twinHalfedge = voriHalfEdgeItr->twin;
//                if (twinHalfedge) {
//                    halfEdgeSet.insert(twinHalfedge);
//                    VoriGraphPolygon *twinpolygonPtr = twinHalfedge->pathFace;
//                    if (twinpolygonPtr != 0) {
//                        QPolygon twin_poly;
//                        for (std::list<topo_geometry::point>::iterator pointitr = twinpolygonPtr->polygonpoints.begin();
//                             pointitr != twinpolygonPtr->polygonpoints.end();
//                             pointitr++) {
//                            sumX += round(topo_geometry::getX(*pointitr));
//                            sumY += round(topo_geometry::getY(*pointitr));
//                        }
//                    }
//                }
//                sumX /= (polygonPtr->polygonpoints.size() + twinHalfedge->pathFace->polygonpoints.size());
//                sumY /= (polygonPtr->polygonpoints.size() + twinHalfedge->pathFace->polygonpoints.size());
//            }//if(polygonPtr != 0)
//            if ((sumX) * (sumY) < 0.00000001) {
//                std::cout << "This shouldn't happen, right";
//            }
//
//
//
//            //build a roomVertex for each edge
//            roomVertex *tmp_rv = new roomVertex(voriHalfEdgeItr->roomId, topo_geometry::point(sumX, sumY),
//                                                voriHalfEdgeItr->source->point, voriHalfEdgeItr->target->point);
//            //append edge into pathes list then transform to PPEdge
//            tmp_rv->areaInnerPathes.push_back(&*voriHalfEdgeItr);
//            tmp_rv->areaInnerPathes.push_back(voriHalfEdgeItr->twin);
//            tmp_rv->init_areaInnerPPGraph();
//
//
//            if (polygonPtr)
//                tmp_rv->polygons.push_back(polygonPtr);
//            if (voriHalfEdgeItr->twin->pathFace)
//                tmp_rv->polygons.push_back(voriHalfEdgeItr->twin->pathFace);
//            //insert roomVertex into the originSet
//            originSet.push_back(tmp_rv);
//
//        }//end else
//    }//end for
//}


void RMG::AreaGraph::buildAreaGraph(VoriGraph &voriGraph) {
    VoriGraph::VertexMap::iterator vertexItr;

    std::set<VoriGraphHalfEdge *> halfEdgeSet;
    std::map<VoriGraphHalfEdge *, roomVertex *> hE2rV;
    for (vertexItr = voriGraph.vertices.begin(); vertexItr != voriGraph.vertices.end(); vertexItr++) {
        int conCnt = vertexItr->second.edgesConnected.size();
        passageEdge *curr_passage;
        if (conCnt >= 4) {
            if (conCnt == 4) {
//                curr_passage = new passageEdge(vertexItr->first, false);
                passageEdge *tmp_passage(new passageEdge(vertexItr->first, false));
                curr_passage = tmp_passage;
            } else if (conCnt > 4) {
//                curr_passage = new passageEdge(vertexItr->first, true);
                passageEdge *tmp_passage(new passageEdge(vertexItr->first, true));
                curr_passage = tmp_passage;
            }
            passageEList.push_back(curr_passage);
        } else {    // if the vertex is a dead end or zero degree
//            std::cout<<"conCnt="<<conCnt<<" ( "<<vertexItr->first.x()<<" , "<<vertexItr->first.y()<<" ) "<<std::endl;
            continue;
        }
        //used to save the VoriGraphHalfEdge that have been visited (by its twin VoriGraphHalfEdge)
        for (std::list<VoriGraphHalfEdge *>::iterator hitr = vertexItr->second.edgesConnected.begin();
             hitr != vertexItr->second.edgesConnected.end(); hitr++) {
            if ((*hitr)->isRay()) {
                conCnt--;
                continue;
            }

            std::set<VoriGraphHalfEdge *>::iterator hfound = halfEdgeSet.find(
                    *hitr);   //WARNING: This check may cause the vertex not being recorded as a passage of this roomVertex
            if (hfound == halfEdgeSet.end()) {
                halfEdgeSet.insert(*hitr);
                VoriGraphPolygon *polygonPtr = (*hitr)->pathFace;
                if (polygonPtr) {
                    VoriGraphHalfEdge *twinHalfedge = (*hitr)->twin;
                    if (twinHalfedge) {
                        halfEdgeSet.insert(twinHalfedge);
                        VoriGraphPolygon *twpolygonPtr = twinHalfedge->pathFace;
                        if (twpolygonPtr) {
                            // CHANGE: just create this halfedge as a roomVertex when both its twin(must has) and it have and path face
                            double cx = (*hitr)->source->point.x() + (*hitr)->target->point.x();
                            cx /= 2.0;
                            double cy = (*hitr)->source->point.y() + (*hitr)->target->point.y();
                            cy /= 2.0;
                            topo_geometry::point c(cx, cy);
//                            std::cout<<"creating roomVertex: roomId="<<(*hitr)->roomId<<", center=";
//                            coutpoint(c); std::cout<<std::endl;
                            roomVertex *curr_rv(new roomVertex((*hitr)->roomId, c,
                                                               (*hitr)->source->point, (*hitr)->target->point));
                            curr_rv->areaInnerPathes.push_back(*hitr);
                            curr_rv->areaInnerPathes.push_back(twinHalfedge);
                            curr_rv->init_areaInnerPPGraph();
                            curr_rv->polygons.push_back(polygonPtr);
                            curr_rv->polygons.push_back(twpolygonPtr);
                            originSet.push_back(curr_rv);

                            hE2rV[*hitr] = curr_rv;
                            hE2rV[twinHalfedge] = curr_rv;


                            //push the new roomVertex as the passage's connected areas
                            curr_passage->connectedAreas.push_back(curr_rv);
//                            curr_rv->passages.push_back(curr_passage);
                            curr_rv->passages.push_back(curr_passage);

                        } else {
                            coutpoint(twinHalfedge->source->point);
                            std::cout << "->";
                            coutpoint(twinHalfedge->target->point);
                            std::cout << "has no path face!" << std::endl;
                        }
                    } else {
                        coutpoint((*hitr)->source->point);
                        std::cout << "->";
                        coutpoint((*hitr)->target->point);
                        std::cout << "has no twin halfedge!" << std::endl;
                    }

                } else {
                    coutpoint((*hitr)->source->point);
                    std::cout << "->";
                    coutpoint((*hitr)->target->point);
                    std::cout << "has no path face!" << std::endl;
                }

            } else {
                if (hE2rV.find(*hitr) != hE2rV.end()) {
                    roomVertex *f_rv = hE2rV[*hitr];

                    std::vector<passageEdge *>::iterator it = f_rv->passages.begin();
                    for (; it != f_rv->passages.end(); it++) {
                        if (*it == curr_passage)
                            break;
                    }
                    if (it == f_rv->passages.end()) {
                        curr_passage->connectedAreas.push_back(f_rv);
                        f_rv->passages.push_back(curr_passage);
                    }
                }
//                if ((*hitr)->pathFace && (*hitr)->twin->pathFace) {
//                    curr_passage->connectedAreas.push_back(hE2rV[*hitr]);
//                    hE2rV[*hitr]->passages.push_back(curr_passage);
//                }
            }
        }
    }
}


void RMG::AreaGraph::mergeRoomPolygons() {
    for (std::vector<roomVertex *>::iterator it = this->originSet.begin();
         it != this->originSet.end(); it++)
        (*it)->mergePolygons();
}


static void check_redun_pair(std::vector<std::pair<topo_geometry::point, topo_geometry::point> > &edges,
                             std::pair<topo_geometry::point, topo_geometry::point> new_pair);

static double calc_poly_area(std::list<topo_geometry::point> &polygon);

void RMG::roomVertex::mergePolygons() {
    //1. traverse all of the pairs(edge) and insert it into vector,
    //if there is a redundent, delete this edge
    //(Because considering the redun count can only be 0 or 1)
    //2. store those outer vertex in order
    if (this->polygons.size() < 2) {
        this->polygon = (*(this->polygons.begin()))->polygonpoints;
        return;
    }
    //1.
    std::vector<std::pair<topo_geometry::point, topo_geometry::point> > edges;//store all of those vertices
    //each polygon
    for (std::vector<VoriGraphPolygon *>::iterator it = this->polygons.begin(); it != this->polygons.end(); it++) {
        if ((*it)->polygonpoints.size() < 2)
            continue;
        topo_geometry::point firstGeoP = *((*it)->polygonpoints.begin());
        //each polygon vertex
        std::list<topo_geometry::point>::iterator itj = (*it)->polygonpoints.begin();
        std::list<topo_geometry::point>::iterator itj_next = itj;

        for (itj_next++; itj_next != (*it)->polygonpoints.end();) {


            std::pair<topo_geometry::point, topo_geometry::point> new_pair(*itj, *itj_next);
            //check redundent            
            check_redun_pair(edges, new_pair);
            itj_next = ++itj;
            itj_next++;
        }
        check_redun_pair(edges, std::pair<topo_geometry::point, topo_geometry::point>(firstGeoP, *itj));
    }
    //2.
    std::pair<topo_geometry::point, topo_geometry::point> first_pair = *(edges.rbegin());

    std::list<topo_geometry::point> tmp_polygon;
    tmp_polygon.push_back(first_pair.first);

    topo_geometry::point pair_tail = first_pair.second;
    double area_max = 0;
    while (!edges.empty()) {
        std::vector<std::pair<topo_geometry::point, topo_geometry::point> >::iterator itp = edges.begin();

        for (; itp != edges.end(); itp++) {
            if (equalLineVertex(pair_tail, itp->first)) {
                tmp_polygon.push_back(pair_tail);

                pair_tail = itp->second;
                // this->polygon.push_back(pair_tail);
                break;
            }
            if (equalLineVertex(pair_tail, itp->second)) {
                tmp_polygon.push_back(pair_tail);

                pair_tail = itp->first;
                // this->polygon.push_back(pair_tail);
                break;
            }
        }

        if (itp != edges.end()) {

            edges.erase(itp);
        } else {
            tmp_polygon.push_back(pair_tail);

            double tmp_area = calc_poly_area(tmp_polygon);
            //std::cout << tmp_area<<std::endl;
            if (tmp_area > area_max) {
                area_max = tmp_area;
                this->polygon = tmp_polygon;
            }
            tmp_polygon.clear();
            //inner poly or outter poly, new poly
            first_pair = *(edges.rbegin());
            //edges.pop_back();
            tmp_polygon.push_back(first_pair.first);
            pair_tail = first_pair.second;
        }
    }
    double tmp_area = calc_poly_area(tmp_polygon);
    //std::cout << tmp_area<<std::endl;   
    if (tmp_area > area_max) {
        area_max = tmp_area;
        this->polygon = tmp_polygon;
    }

}

/*
 *Tools only for this cpp
 */
static double calc_poly_area(std::list<topo_geometry::point> &polygon) {
    double area = 0;
    std::list<topo_geometry::point>::iterator itj = polygon.end();
    itj--;
    for (std::list<topo_geometry::point>::iterator it = polygon.begin(); it != polygon.end(); it++) {
        area += ((topo_geometry::getX(*itj) * topo_geometry::getX(*it)) *
                 (topo_geometry::getY(*itj) - topo_geometry::getY(*it)));
        itj = it;
    }
    return std::abs(area / 2.0);
}

static void check_redun_pair(std::vector<std::pair<topo_geometry::point, topo_geometry::point> > &edges,
                             std::pair<topo_geometry::point, topo_geometry::point> new_pair) {
//check redundent            
    std::vector<std::pair<topo_geometry::point, topo_geometry::point> >::iterator itk = edges.begin();
    for (; itk != edges.end(); itk++) {
        if ((equalLineVertex(itk->first, new_pair.first) && equalLineVertex(itk->second, new_pair.second)) ||
            (equalLineVertex(itk->first, new_pair.second) && equalLineVertex(itk->second, new_pair.first)))
            break;
    }
    //if fund redun, erase
    if (itk != edges.end()) {
        edges.erase(itk);
    }
        //if not found redun, insert
    else {
        //check self.connect edge
        if (!equalLineVertex(new_pair.first, new_pair.second))
            edges.push_back(new_pair);
    }
}

static bool equalLineVertex(const topo_geometry::point &a, const topo_geometry::point &b) {
    if ((topo_geometry::getX(a)) == (topo_geometry::getX(b))
        &&
        (topo_geometry::getY(a)) == (topo_geometry::getY(b))) {
        if ((topo_geometry::getX(a)) == 0 && (topo_geometry::getY(a)) == 0)
            /*
            if((round(topo_geometry::getX(a))) == (round(topo_geometry::getX(b)))
                    &&
            (round(topo_geometry::getY(a))) == (round(topo_geometry::getY(b))) ){
                if((round(topo_geometry::getX(a))) ==0 && (round(topo_geometry::getY(a))) == 0 )
            */
            return false;
        //std::cout << "True match: " << round(topo_geometry::getX(a))<<" " <<round(topo_geometry::getY(a))<<" " << round(topo_geometry::getX(b))<< " " << round(topo_geometry::getY(b)) << std::endl;
        return true;
    } else
        return false;
}

// 将笛卡尔坐标转换为经纬度
static std::pair<double, double> cartesianToLatLon(double x, double y, const topo_geometry::point& root_point)
{
    // 坐标缩放因子(根据实际地图大小调整)
    const double SCALE_FACTOR = 0.001;
    
    // 计算相对于根节点的偏移量，并转换为经纬度
    double lat = topo_geometry::getY(root_point) + y * SCALE_FACTOR;
    double lon = topo_geometry::getX(root_point) + x * SCALE_FACTOR;
    
    return std::make_pair(lat, lon);
}

// 优化房间多边形，使通道与房间边界重合
void RMG::AreaGraph::optimizeRoomPolygonsForPassages()
{
    // 保存所有通道的端点信息
    struct PassageEndpoints {
        topo_geometry::point pointA;
        topo_geometry::point pointB;
        roomVertex* roomA;
        roomVertex* roomB;
    };
    
    std::vector<PassageEndpoints> allPassages;
    
    // 第一步：收集所有通道的端点信息
    for (auto passageEdge : passageEList) {
        if (passageEdge->connectedAreas.size() == 2) {
            roomVertex* roomA = passageEdge->connectedAreas[0];
            roomVertex* roomB = passageEdge->connectedAreas[1];
            
            // 定义判断两个点是否接近的阈值
            const double POINT_PROXIMITY_THRESHOLD = 0.5; // 根据实际坐标系调整
            
            // 计算通道附近的点
            const int MAX_POINTS_TO_CONSIDER = 10;
            std::vector<std::pair<topo_geometry::point, double>> roomAPoints, roomBPoints;
            
            // 收集房间A中距离通道最近的点
            for (const auto& point : roomA->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomAPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomAPoints.begin(), roomAPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomAPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomAPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 收集房间B中距离通道最近的点
            for (const auto& point : roomB->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomBPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomBPoints.begin(), roomBPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomBPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomBPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 从这些点中找出两个房间的共有边界点（或相距非常近的点）
            std::vector<std::pair<topo_geometry::point, topo_geometry::point>> sharedPoints;
            
            for (const auto& pointA_pair : roomAPoints) {
                for (const auto& pointB_pair : roomBPoints) {
                    const auto& pointACandidate = pointA_pair.first;
                    const auto& pointBCandidate = pointB_pair.first;
                    
                    double pointDistance = boost::geometry::distance(pointACandidate, pointBCandidate);
                    if (pointDistance < POINT_PROXIMITY_THRESHOLD) {
                        sharedPoints.push_back(std::make_pair(pointACandidate, pointBCandidate));
                    }
                }
            }
            
            // 找到两个点作为通道端点
            topo_geometry::point pointA, pointB;
            
            // 如果找到了至少两对共有边界点，选择相距最远的两对
            if (sharedPoints.size() >= 2) {
                double maxDist = 0;
                size_t maxI = 0, maxJ = 1;
                
                for (size_t i = 0; i < sharedPoints.size(); ++i) {
                    for (size_t j = i + 1; j < sharedPoints.size(); ++j) {
                        double dist = boost::geometry::distance(sharedPoints[i].first, sharedPoints[j].first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            maxI = i;
                            maxJ = j;
                        }
                    }
                }
                
                pointA = sharedPoints[maxI].first;
                pointB = sharedPoints[maxJ].first;
            } 
            else if (sharedPoints.size() == 1) {
                pointA = sharedPoints[0].first;
                
                double maxDist = 0;
                for (const auto& pointB_pair : roomBPoints) {
                    double dist = boost::geometry::distance(pointA, pointB_pair.first);
                    if (dist > maxDist) {
                        maxDist = dist;
                        pointB = pointB_pair.first;
                    }
                }
                
                if (maxDist < 0.01) {
                    for (const auto& pointA_pair : roomAPoints) {
                        double dist = boost::geometry::distance(pointA, pointA_pair.first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            pointB = pointA_pair.first;
                        }
                    }
                }
            }
            else {
                if (!roomAPoints.empty() && !roomBPoints.empty()) {
                    pointA = roomAPoints[0].first;
                    pointB = roomBPoints[0].first;
                }
                else if (!passageEdge->line.cwline.empty()) {
                    pointA = passageEdge->line.cwline.front();
                    pointB = passageEdge->line.cwline.back();
                }
                else {
                    pointA = passageEdge->position;
                    double newX = topo_geometry::getX(passageEdge->position) + 0.01;
                    double newY = topo_geometry::getY(passageEdge->position) + 0.01;
                    pointB = topo_geometry::point(newX, newY);
                }
            }
            
            // 收集通道端点信息
            PassageEndpoints endpoints;
            endpoints.pointA = pointA;
            endpoints.pointB = pointB;
            endpoints.roomA = roomA;
            endpoints.roomB = roomB;
            allPassages.push_back(endpoints);
        }
    }
    
    // 第二步：优化每个房间的多边形
    for (auto roomVtx : originSet) {
        // 收集与该房间相关的所有通道端点
        std::vector<topo_geometry::point> passagePoints;
        for (const auto& passage : allPassages) {
            if (passage.roomA == roomVtx) {
                passagePoints.push_back(passage.pointA);
                passagePoints.push_back(passage.pointB);
            }
            else if (passage.roomB == roomVtx) {
                passagePoints.push_back(passage.pointA);
                passagePoints.push_back(passage.pointB);
            }
        }
        
        // 如果没有通道端点，跳过优化
        if (passagePoints.empty()) {
            continue;
        }
        
        // 为每对通道端点创建映射，用于后续处理
        std::vector<std::pair<topo_geometry::point, topo_geometry::point>> passageEndpointPairs;
        
        // 找出属于同一通道的端点对
        for (const auto& passage : allPassages) {
            if (passage.roomA == roomVtx || passage.roomB == roomVtx) {
                passageEndpointPairs.push_back(std::make_pair(passage.pointA, passage.pointB));
            }
        }
        
        // 先确保通道端点在房间多边形中
        std::list<topo_geometry::point> tempPolygon = roomVtx->polygon;
        
        // 先插入所有通道端点（如果尚未存在）
        for (const auto& passagePoint : passagePoints) {
            bool found = false;
            for (const auto& polygonPoint : tempPolygon) {
                if (equalLineVertex(passagePoint, polygonPoint)) {
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                // 找到最近的边并插入
                auto it = tempPolygon.begin();
                auto itNext = std::next(it);
                double minDist = std::numeric_limits<double>::max();
                auto bestPos = tempPolygon.end();
                
                while (itNext != tempPolygon.end()) {
                    double dist = boost::geometry::distance(*it, passagePoint) + 
                                 boost::geometry::distance(*itNext, passagePoint);
                    if (dist < minDist) {
                        minDist = dist;
                        bestPos = itNext;
                    }
                    ++it;
                    ++itNext;
                }
                
                double lastDist = boost::geometry::distance(tempPolygon.back(), passagePoint) + 
                               boost::geometry::distance(tempPolygon.front(), passagePoint);
                if (lastDist < minDist) {
                    bestPos = tempPolygon.begin();
                }
                
                if (bestPos != tempPolygon.end()) {
                    tempPolygon.insert(bestPos, passagePoint);
                }
            }
        }
        
        // 根据通道端点对重构多边形
        std::list<topo_geometry::point> optimizedPolygon;
        bool needsOptimization = !passageEndpointPairs.empty();
        
        if (needsOptimization) {
            // 将多边形转换为vector以便索引访问
            std::vector<topo_geometry::point> polygonPoints(tempPolygon.begin(), tempPolygon.end());
            int n = polygonPoints.size();
            
            // 找出所有通道端点在多边形中的索引位置
            std::map<topo_geometry::point, int, topo_geometry::Smaller> pointToIndex;
            for (int i = 0; i < n; ++i) {
                for (const auto& passagePoint : passagePoints) {
                    if (equalLineVertex(polygonPoints[i], passagePoint)) {
                        pointToIndex[passagePoint] = i;
                        break;
                    }
                }
            }
            
            // 创建保留点的mask
            std::vector<bool> keepPoint(n, true);
            
            // 对每对通道端点，删除它们之间的点（选择较短的路径）
            for (const auto& endpointPair : passageEndpointPairs) {
                // 找到点在多边形中的索引位置
                int idx1 = -1, idx2 = -1;
                
                // 手动查找索引，因为直接使用map的find可能会因为浮点比较精度问题失败
                for (int i = 0; i < n; ++i) {
                    if (equalLineVertex(polygonPoints[i], endpointPair.first)) {
                        idx1 = i;
                    }
                    if (equalLineVertex(polygonPoints[i], endpointPair.second)) {
                        idx2 = i;
                    }
                }
                
                // 确认两个端点都在多边形中
                if (idx1 != -1 && idx2 != -1) {
                    // 确保idx1 < idx2，如果需要则交换
                    if (idx1 > idx2) {
                        std::swap(idx1, idx2);
                    }
                    
                    // 计算两种路径的长度：idx1->idx2 和 idx2->idx1+n
                    int path1Length = idx2 - idx1 - 1;
                    int path2Length = (idx1 + n) - idx2 - 1;
                    
                    if (path1Length < path2Length) {
                        // 删除第一条路径上的点
                        for (int i = idx1 + 1; i < idx2; ++i) {
                            keepPoint[i] = false;
                        }
                    } else {
                        // 删除第二条路径上的点
                        for (int i = idx2 + 1; i < idx1 + n; ++i) {
                            keepPoint[i % n] = false;
                        }
                    }
                }
            }
            
            // 根据keepPoint构建新的多边形
            for (int i = 0; i < n; ++i) {
                if (keepPoint[i]) {
                    optimizedPolygon.push_back(polygonPoints[i]);
                }
            }
        } else {
            // 如果没有需要优化的通道端点对，使用tempPolygon
            optimizedPolygon = tempPolygon;
        }
        
        // 确保多边形仍然闭合
        if (!optimizedPolygon.empty() && !equalLineVertex(optimizedPolygon.front(), optimizedPolygon.back())) {
            optimizedPolygon.push_back(optimizedPolygon.front());
        }
        
        // 更新房间的多边形
        roomVtx->polygon = optimizedPolygon;
    }
}

// 将AreaGraph导出为osmAG.xml格式
void RMG::AreaGraph::exportToOsmAG(const std::string& filename)
{
    // 添加调试信息
    std::cout << "开始导出AreaGraph到" << filename << std::endl;
    
    // 检查originSet中是否有重复的房间ID
    std::map<int, int> roomIdCount;
    for (auto roomVtx : originSet) {
        roomIdCount[roomVtx->roomId]++;
    }
    
    for (const auto& pair : roomIdCount) {
        if (pair.second > 1) {
            std::cout << "警告: 房间ID " << pair.first << " 在originSet中出现了 " << pair.second << " 次!" << std::endl;
        }
    }
    
    // 创建XML文档
    std::ofstream osmFile(filename);
    osmFile << "<?xml version='1.0' encoding='UTF-8'?>\n";
    osmFile << "<osm version='0.6' generator='AreaGraph'>\n";
    
    // 创建一个负整数ID生成器(避免与OSM实际数据冲突)
    int nextId = -1;
    std::map<topo_geometry::point, int, topo_geometry::Smaller> pointToNodeId;
    
    // 1. 创建根节点作为坐标原点(0,0)
    // 直接使用构造函数创建点，不使用setX和setY
    topo_geometry::point root_point(0.01, 0.01);
    int rootId = nextId--;
    osmFile << "  <node id='" << rootId << "' action='modify' visible='true' lat='" 
            << topo_geometry::getY(root_point) << "' lon='" << topo_geometry::getX(root_point) << "'>\n";
    osmFile << "    <tag k='name' v='root' />\n";
    osmFile << "  </node>\n";
    
    // 2. 收集所有房间的点
    std::map<roomVertex*, std::vector<int>> roomVertexToNodeIds;
    
    // 2.1 遍历所有房间，创建各个点
    for (auto roomVtx : originSet) {
        std::vector<int> nodeIds;
        
        // 从房间的多边形中提取所有点
        for (auto it = roomVtx->polygon.begin(); it != roomVtx->polygon.end(); ++it) {
            topo_geometry::point point = *it;
            
            // 检查这个点是否已经创建过
            bool pointExists = false;
            int nodeId = nextId;
            
            for (const auto& pair : pointToNodeId) {
                if (equalLineVertex(pair.first, point)) {
                    pointExists = true;
                    nodeId = pair.second;
                    break;
                }
            }
            
            if (!pointExists) {
                nodeId = nextId--;
                pointToNodeId[point] = nodeId;
                
                // 转换为经纬度
                auto latLon = cartesianToLatLon(topo_geometry::getX(point), topo_geometry::getY(point), root_point);
                
                // 写入节点
                osmFile << "  <node id='" << nodeId << "' action='modify' visible='true' lat='" 
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }
            
            nodeIds.push_back(nodeId);
        }
        
        roomVertexToNodeIds[roomVtx] = nodeIds;
    }
    
    // 3. 创建房间way的ID映射（但暂不创建way，等优化后再创建）
    int nextWayId = -1;
    std::map<roomVertex*, int> roomToWayId;
    
    for (auto roomVtx : originSet) {
        int wayId = nextWayId--;
        roomToWayId[roomVtx] = wayId;
    }
    
    // 4. 获取所有通道端点信息
    struct PassagePoint {
        topo_geometry::point point;
        roomVertex* roomA;
        roomVertex* roomB;
        int nodeId;
    };
    
    std::vector<std::pair<PassagePoint, PassagePoint>> passagePoints;
    
    // 先遍历所有通道，找出并记录它们的正确端点
    for (auto passageEdge : passageEList) {
        // 只处理连接两个房间的通道
        if (passageEdge->connectedAreas.size() == 2) {
            roomVertex* roomA = passageEdge->connectedAreas[0];
            roomVertex* roomB = passageEdge->connectedAreas[1];
            
            // 找到两个房间共有边界点中相距最远的两个点作为通道两端
            topo_geometry::point pointA, pointB;
            
            // 定义判断两个点是否接近的阈值
            const double POINT_PROXIMITY_THRESHOLD = 0.5; // 根据实际坐标系调整
            
            // 计算通道附近的点（取两个房间中到通道距离最小的前N个点）
            const int MAX_POINTS_TO_CONSIDER = 10;
            std::vector<std::pair<topo_geometry::point, double>> roomAPoints, roomBPoints;
            
            // 收集房间A中距离通道最近的点
            for (const auto& point : roomA->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomAPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomAPoints.begin(), roomAPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomAPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomAPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 收集房间B中距离通道最近的点
            for (const auto& point : roomB->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomBPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomBPoints.begin(), roomBPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomBPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomBPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 从这些点中找出两个房间的共有边界点（或相距非常近的点）
            std::vector<std::pair<topo_geometry::point, topo_geometry::point>> sharedPoints;
            
            for (const auto& pointA_pair : roomAPoints) {
                for (const auto& pointB_pair : roomBPoints) {
                    const auto& pointACandidate = pointA_pair.first;
                    const auto& pointBCandidate = pointB_pair.first;
                    
                    double pointDistance = boost::geometry::distance(pointACandidate, pointBCandidate);
                    if (pointDistance < POINT_PROXIMITY_THRESHOLD) {
                        // 这两个点尽管不完全相同，但很接近，可以视为共有边界点
                        sharedPoints.push_back(std::make_pair(pointACandidate, pointBCandidate));
                    }
                }
            }
            
            // 如果找到了至少两对共有边界点，选择相距最远的两对
            if (sharedPoints.size() >= 2) {
                double maxDist = 0;
                size_t maxI = 0, maxJ = 1;
                
                for (size_t i = 0; i < sharedPoints.size(); ++i) {
                    for (size_t j = i + 1; j < sharedPoints.size(); ++j) {
                        double dist = boost::geometry::distance(sharedPoints[i].first, sharedPoints[j].first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            maxI = i;
                            maxJ = j;
                        }
                    }
                }
                
                // 使用相距最远的两对点
                pointA = sharedPoints[maxI].first;
                pointB = sharedPoints[maxJ].first;
            } 
            // 如果只有一对共有边界点，使用这对点和另一个房间的点
            else if (sharedPoints.size() == 1) {
                pointA = sharedPoints[0].first;
                
                // 根据距离选择另一个房间的点（与所选的共有点相距最远的点）
                double maxDist = 0;
                
                for (const auto& pointB_pair : roomBPoints) {
                    double dist = boost::geometry::distance(pointA, pointB_pair.first);
                    if (dist > maxDist) {
                        maxDist = dist;
                        pointB = pointB_pair.first;
                    }
                }
                
                if (maxDist < 0.01) { // 如果没找到合适的点
                    for (const auto& pointA_pair : roomAPoints) {
                        double dist = boost::geometry::distance(pointA, pointA_pair.first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            pointB = pointA_pair.first;
                        }
                    }
                }
            }
            // 如果没有共有边界点，使用每个房间距离通道最近的点
            else {
                if (!roomAPoints.empty() && !roomBPoints.empty()) {
                    pointA = roomAPoints[0].first;
                    pointB = roomBPoints[0].first;
                }
                // 如果集合为空，使用通道的线段端点（如果有）
                else if (!passageEdge->line.cwline.empty()) {
                    pointA = passageEdge->line.cwline.front();
                    pointB = passageEdge->line.cwline.back();
                }
                // 最后的备用方案，使用通道位置和偏移点
                else {
                    pointA = passageEdge->position;
                    double newX = topo_geometry::getX(passageEdge->position) + 0.01;
                    double newY = topo_geometry::getY(passageEdge->position) + 0.01;
                    pointB = topo_geometry::point(newX, newY);
                }
            }
            
            // 检查端点是否已存在，否则创建新节点
            int nodeIdA = -1;
            int nodeIdB = -1;
            
            // 查找点A是否存在
            bool pointAExists = false;
            for (const auto& pair : pointToNodeId) {
                if (equalLineVertex(pair.first, pointA)) {
                    pointAExists = true;
                    nodeIdA = pair.second;
                    break;
                }
            }
            
            if (!pointAExists) {
                nodeIdA = nextId--;
                pointToNodeId[pointA] = nodeIdA;
                
                auto latLon = cartesianToLatLon(topo_geometry::getX(pointA), topo_geometry::getY(pointA), root_point);
                osmFile << "  <node id='" << nodeIdA << "' action='modify' visible='true' lat='" 
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }
            
            // 查找点B是否存在
            bool pointBExists = false;
            if (!equalLineVertex(pointA, pointB)) { // 只有当点A和点B不同时才查找点B
                for (const auto& pair : pointToNodeId) {
                    if (equalLineVertex(pair.first, pointB)) {
                        pointBExists = true;
                        nodeIdB = pair.second;
                        break;
                    }
                }
                
                if (!pointBExists) {
                    nodeIdB = nextId--;
                    pointToNodeId[pointB] = nodeIdB;
                    
                    auto latLon = cartesianToLatLon(topo_geometry::getX(pointB), topo_geometry::getY(pointB), root_point);
                    osmFile << "  <node id='" << nodeIdB << "' action='modify' visible='true' lat='" 
                            << latLon.first << "' lon='" << latLon.second << "' />\n";
                }
            } else {
                // 如果点A和点B相同，则使用相同的nodeId
                nodeIdB = nodeIdA;
            }
            
            // 在这里记录通道端点信息，但先不创建通道way
            PassagePoint ptA, ptB;
            
            ptA.point = pointA;
            ptA.roomA = roomA;
            ptA.roomB = roomB;
            ptA.nodeId = nodeIdA;
            
            ptB.point = pointB;
            ptB.roomA = roomA;
            ptB.roomB = roomB;
            ptB.nodeId = nodeIdB;
            
            passagePoints.push_back(std::make_pair(ptA, ptB));
        }
    }
    
    // 5. 调用已有的函数优化房间多边形，使通道与房间边界重合
    // 输出优化前的房间信息
    std::cout << "优化前房间数量: " << originSet.size() << std::endl;
    for (auto roomVtx : originSet) {
        if (roomVtx->roomId == 25 || roomVtx->roomId == 3) {
            std::cout << "优化前房间ID: " << roomVtx->roomId << ", 多边形点数: " << roomVtx->polygon.size() << std::endl;
        }
    }
    
    optimizeRoomPolygonsForPassages();
    
    // 输出优化后的房间信息
    std::cout << "优化后房间数量: " << originSet.size() << std::endl;
    for (auto roomVtx : originSet) {
        if (roomVtx->roomId == 25 || roomVtx->roomId == 3) {
            std::cout << "优化后房间ID: " << roomVtx->roomId << ", 多边形点数: " << roomVtx->polygon.size() << std::endl;
        }
    }
    
    // 重新生成所有房间节点ID，因为多边形已经被优化
    roomVertexToNodeIds.clear(); // 清除所有现有的房间节点ID映射
    
    // 重新遍历所有房间，生成节点ID（仅使用优化后的多边形）
    for (auto roomVtx : originSet) {
        std::vector<int> nodeIds;
        
        // 从优化后的房间多边形中提取所有点
        for (auto it = roomVtx->polygon.begin(); it != roomVtx->polygon.end(); ++it) {
            topo_geometry::point point = *it;
            
            // 检查这个点是否已经创建过
            bool pointExists = false;
            int nodeId = nextId;
            
            for (const auto& pair : pointToNodeId) {
                if (equalLineVertex(pair.first, point)) {
                    pointExists = true;
                    nodeId = pair.second;
                    break;
                }
            }
            
            if (!pointExists) {
                nodeId = nextId--;
                pointToNodeId[point] = nodeId;
                
                // 转换为经纬度
                auto latLon = cartesianToLatLon(topo_geometry::getX(point), topo_geometry::getY(point), root_point);
                
                // 写入节点
                osmFile << "  <node id='" << nodeId << "' action='modify' visible='true' lat='" 
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }
            
            nodeIds.push_back(nodeId);
        }
        
        roomVertexToNodeIds[roomVtx] = nodeIds;
    }
    
    // 输出所有房间way，仅使用优化后的多边形
    // 创建一个集合来跟踪已经处理过的房间ID
    std::set<int> processedRoomIds;
    
    for (auto roomVtx : originSet) {
        // 调试输出，跟踪room_25和room_3
        if (roomVtx->roomId == 25 || roomVtx->roomId == 3) {
            std::cout << "正在处理房间ID: " << roomVtx->roomId << ", 多边形点数: " << roomVtx->polygon.size() << std::endl;
            
            // 输出多边形的点坐标，便于调试
            std::cout << "多边形坐标: ";
            for (const auto& point : roomVtx->polygon) {
                std::cout << "(" << topo_geometry::getX(point) << "," << topo_geometry::getY(point) << ") ";
            }
            std::cout << std::endl;
        }
        
        // 检查这个房间ID是否已经处理过
        if (processedRoomIds.find(roomVtx->roomId) != processedRoomIds.end()) {
            std::cout << "警告: 房间ID " << roomVtx->roomId << " 重复出现在originSet中!" << std::endl;
            continue; // 跳过重复的房间ID
        }
        
        // 记录这个房间ID已经被处理
        processedRoomIds.insert(roomVtx->roomId);
        
        int wayId = roomToWayId[roomVtx];
        
        osmFile << "  <way id='" << wayId << "' action='modify' visible='true'>\n";
        
        // 添加所有节点引用
        auto& nodeIds = roomVertexToNodeIds[roomVtx];
        for (int nodeId : nodeIds) {
            osmFile << "    <nd ref='" << nodeId << "' />\n";
        }
        // 确保闭合（第一个点和最后一个点相同）
        if (!nodeIds.empty() && nodeIds.front() != nodeIds.back()) {
            osmFile << "    <nd ref='" << nodeIds.front() << "' />\n";
        }
        
        // 添加房间标签
        osmFile << "    <tag k='indoor' v='room' />\n";
        osmFile << "    <tag k='name' v='room_" << roomVtx->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:areaType' v='room' />\n";
        osmFile << "    <tag k='osmAG:type' v='area' />\n";
        osmFile << "    <tag k='osmAG:optimized' v='true' />\n"; // 添加标记表明这是优化后的多边形
        osmFile << "  </way>\n";
    }
    
    // 6. 输出通道way
    int passageCount = 1;
    for (const auto& passage : passagePoints) {
        int wayId = nextWayId--;
        const PassagePoint& ptA = passage.first;
        const PassagePoint& ptB = passage.second;
        
        osmFile << "  <way id='" << wayId << "' action='modify' visible='true'>\n";
        osmFile << "    <nd ref='" << ptA.nodeId << "' />\n";
        
        // 只有当两个点不同时才添加第二个点
        if (ptA.nodeId != ptB.nodeId) {
            osmFile << "    <nd ref='" << ptB.nodeId << "' />\n";
        }
        
        // 添加通道标签
        osmFile << "    <tag k='name' v='p_" << passageCount++ << "' />\n";
        osmFile << "    <tag k='osmAG:from' v='room_" << ptA.roomA->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:to' v='room_" << ptA.roomB->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:type' v='passage' />\n";
        osmFile << "  </way>\n";
    }
    
    // 结束文档
    osmFile << "</osm>\n";
    osmFile.close();
}
