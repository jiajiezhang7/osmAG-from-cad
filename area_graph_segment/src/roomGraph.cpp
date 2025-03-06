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

