
#include "VoriGraph.h"

// #include <QImage>
// #include <QPainter>

#include <limits>

using namespace std;


double dist(double ax, double ay, double bx, double by) {
    double dx = ax - bx;
    double dy = ay - by;
    return sqrt( dx * dx + dy * dy );
}

double dist_gp(topo_geometry::point a, topo_geometry::point b);

/* Jiawei: also join the faces here!! */
std::list<topo_geometry::point> VoriGraphHalfEdge::joinPolygon(VoriGraphHalfEdge *pFirst, VoriGraphHalfEdge *pSecond) {
    std::list<topo_geometry::point> result_list;
//    if(!(pFirst->pathFace&&pSecond->pathFace))return result_list;
    result_list.insert( result_list.end(), pFirst->pathFace->polygonpoints.begin(),
                        pFirst->pathFace->polygonpoints.end());
    std::list<topo_geometry::point>::iterator Ftarget, Fobs= result_list.begin();
    double minp=1.0;
    for (std::list<topo_geometry::point>::iterator itrF = result_list.begin();
         (itrF != result_list.end()); itrF++) {
        if (fabs( itrF->x() - pFirst->target->point.x()) < EPSINON &&
            fabs( itrF->y() - pFirst->target->point.y()) < EPSINON) {
//        if (fabs( itrF->x() - pFirst->target->point.x()) +
//            fabs( itrF->y() - pFirst->target->point.y()) < minp) {
            Ftarget = itrF;
            itrF++;
            Fobs = itrF;
            break;
        }
    }
    if(pSecond->pathFace->polygonpoints.empty())std::cout<<"pSecond is empty!!"<<std::endl;
    if(Fobs== result_list.begin())std::cout<<"Fobs not exist!!"<<std::endl;
    result_list.insert( Fobs, pSecond->pathFace->polygonpoints.begin(), pSecond->pathFace->polygonpoints.end());
    return result_list;
}
void coutpoint(topo_geometry::point p) {
    double x, y;
    x = topo_geometry::getX(p);
    y = topo_geometry::getY(p);
    std::cout << "(" << x << ", " << y << ") ";
}
//void couthalfedge(VoriGraphHalfEdge HF){
//    coutpoint(HF.pathEdges.front().s());
//    for(std::list<topo_geometry::Halfedge>::iterator ei=HF.pathEdges.begin();ei!=HF.pathEdges.end();ei++){
//        coutpoint(ei->t());
//    }
//    std::cout<<std::endl;
//}
void coutpolygon(std::list<topo_geometry::point> polygonpoints){
    for(std::list<topo_geometry::point>::iterator pi=polygonpoints.begin();pi!=polygonpoints.end();pi++){
        coutpoint(*pi);
    }
    std::cout<<std::endl;
}

void VoriGraph::joinHalfEdges(VoriGraphHalfEdge *pFirst, VoriGraphHalfEdge *pSecond) {
    if (pFirst->target != pSecond->source) {
        cerr << "Error joining edges!!! (not adjacents in correct order)" << endl;
        return;
    }
    if (pFirst->isRay() || pSecond->isRay()) {
        cerr << "Error joining edges!!! (cannot joing rays)" << endl;
        return;
    }
    if (pFirst->target->edgesConnected.size() > 4) {
        cerr << "Error joining edges!!! (middle vertex has additional edge)" << endl;
        return;
    }
    //create new half Edge:
    VoriGraphHalfEdge newHalfEdge;
//   newHalfEdge.halfEdges = pSecond->halfEdges;
//   newHalfEdge.halfEdges.insert(newHalfEdge.halfEdges.begin(), pFirst->halfEdges.begin(), pFirst->halfEdges.end());

    newHalfEdge.pathEdges = pSecond->pathEdges;
    newHalfEdge.pathEdges.insert( newHalfEdge.pathEdges.begin(), pFirst->pathEdges.begin(), pFirst->pathEdges.end());

    newHalfEdge.source = pFirst->source;
    newHalfEdge.target = pSecond->target;
    newHalfEdge.distance = pFirst->distance + pSecond->distance;
    newHalfEdge.obstacleMinimum = min( pFirst->obstacleMinimum, pSecond->obstacleMinimum );
    // calculate the new average distance to obstacles - as good as we can wieghed on the distance (lengths) of the parts...
    newHalfEdge.obstacleAverage = pFirst->obstacleAverage * pFirst->distance / (pFirst->distance + pSecond->distance) +
                                  pSecond->obstacleAverage * pSecond->distance / (pFirst->distance + pSecond->distance);

    //   remove from vertexes
    pFirst->source->removeHalfEdge( pFirst );
    pFirst->target->removeHalfEdge( pFirst );
    pSecond->source->removeHalfEdge( pSecond );
    pSecond->target->removeHalfEdge( pSecond );

    //if(mergeRoomDeadEnd) cout<<newHalfEdge.target->edgesConnected.size()<<endl;

    // check if middle vertex has to be deleted
    if (pFirst->target->edgesConnected.empty()) {
        //     remove vertex from Graph
        vertices.erase( pFirst->target->point );
//     verticesList.remove(*pFirst->target);

    }
    // remove edges
    for (std::list<VoriGraphHalfEdge>::iterator itr = halfEdges.begin(); itr != halfEdges.end();) {
        if (&*itr == pFirst || &*itr == pSecond) {
            itr = halfEdges.erase( itr );
        } else ++itr;
    }


    // add new half Edge to list
    halfEdges.push_back( newHalfEdge );
    // add new half Edge to vertices
    VoriGraphHalfEdge *edgePtr = &*halfEdges.rbegin();
    assert( edgePtr != 0 );
    // question here!!!

    newHalfEdge.target->edgesConnected.push_back( edgePtr );
    newHalfEdge.source->edgesConnected.push_back( edgePtr );
    // see if the twin is already there - to mark it...
    newHalfEdge.target->markTwins();
}

void VoriGraph::joinHalfEdges_tianyan(VoriGraphHalfEdge *pFirst, VoriGraphHalfEdge *pSecond, bool mergeRoomDeadEnd) {
    if (pFirst->target != pSecond->source) {
        cerr << "Error joining edges!!! (not adjacents in correct order)" << endl;
        return;
    }
    if (pFirst->isRay() || pSecond->isRay()) {
        cerr << "Error joining edges!!! (cannot joing rays)" << endl;
        return;
    }
    if (pFirst->target->edgesConnected.size() > 4) {
        cerr << "Error joining edges!!! (middle vertex has additional edge)" << endl;
        return;
    }
    //create new half Edge:
    VoriGraphHalfEdge newHalfEdge;

    //for Room----ID
    if (mergeRoomDeadEnd) {
        if (pFirst->roomId == pSecond->roomId) {
            newHalfEdge.setRoomId( pFirst->roomId );
        }
    }
//   newHalfEdge.halfEdges = pSecond->halfEdges;
//   newHalfEdge.halfEdges.insert(newHalfEdge.halfEdges.begin(), pFirst->halfEdges.begin(), pFirst->halfEdges.end());

    newHalfEdge.pathEdges = pSecond->pathEdges;
    newHalfEdge.pathEdges.insert( newHalfEdge.pathEdges.begin(), pFirst->pathEdges.begin(), pFirst->pathEdges.end());

    newHalfEdge.source = pFirst->source;
    newHalfEdge.target = pSecond->target;
    newHalfEdge.distance = pFirst->distance + pSecond->distance;
    newHalfEdge.obstacleMinimum = min( pFirst->obstacleMinimum, pSecond->obstacleMinimum );
    // calculate the new average distance to obstacles - as good as we can wieghed on the distance (lengths) of the parts...
    newHalfEdge.obstacleAverage = pFirst->obstacleAverage * pFirst->distance / (pFirst->distance + pSecond->distance) +
                                  pSecond->obstacleAverage * pSecond->distance / (pFirst->distance + pSecond->distance);

    //   remove from vertexes
    pFirst->source->removeHalfEdge( pFirst );
    pFirst->target->removeHalfEdge( pFirst );
    pSecond->source->removeHalfEdge( pSecond );
    pSecond->target->removeHalfEdge( pSecond );

    //if(mergeRoomDeadEnd) cout<<newHalfEdge.target->edgesConnected.size()<<endl;

    // check if middle vertex has to be deleted
    if (pFirst->target->edgesConnected.empty()) {
        //     remove vertex from Graph
        vertices.erase( pFirst->target->point );
//     verticesList.remove(*pFirst->target);

    }
    // remove edges
    for (std::list<VoriGraphHalfEdge>::iterator itr = halfEdges.begin(); itr != halfEdges.end();) {
        if (&*itr == pFirst || &*itr == pSecond) {
            itr = halfEdges.erase( itr );
        } else ++itr;
    }


    // add new half Edge to list
    halfEdges.push_back( newHalfEdge );
    // add new half Edge to vertices
    VoriGraphHalfEdge *edgePtr = &*halfEdges.rbegin();
    assert( edgePtr != 0 );
    // question here!!!

    newHalfEdge.target->edgesConnected.push_back( edgePtr );
    newHalfEdge.source->edgesConnected.push_back( edgePtr );
    // see if the twin is already there - to mark it...
    newHalfEdge.target->markTwins();

    //for Room----Border
    if (mergeRoomDeadEnd) {
        //after merging, deadend should be regarded as room and set the same roomid as path
        if (newHalfEdge.source->edgesConnected.size() == 2) {
            newHalfEdge.source->markBorderVertex();
            newHalfEdge.source->setRoomId( newHalfEdge.getRoomId());
        }
        //dead end set as border
        if (newHalfEdge.target->edgesConnected.size() == 2) {
            newHalfEdge.target->markBorderVertex();
            newHalfEdge.target->setRoomId( newHalfEdge.getRoomId());
        }
    }
}

void VoriGraph::joinHalfEdges_jiawei(VoriGraphHalfEdge *pFirst, VoriGraphHalfEdge *pSecond, bool mergeRoomDeadEnd) {
    if (pFirst->target != pSecond->source) {    //pFirst的终结点必须是pSecond的始节点
        cerr << "Error joining edges!!! (not adjacents in correct order)" << endl;
        return;
    }
    if (pFirst->isRay() || pSecond->isRay()) {  //pFirst或pSecond为射线则无法合并
        cerr << "Error joining edges!!! (cannot joing rays)" << endl;
        return;
    }
    if (pFirst->target->edgesConnected.size() > 4) {    //pFirst的终结点所连路径超过4条则无法合并；相连的4条路径：pFirst及其对偶路径和pSecond及其对偶路径
        cerr << "Error joining edges!!! (middle vertex has additional edge)" << endl;
        return;
    }
    if (!(pFirst->pathFace && pSecond->pathFace)) {
        cerr << "Error joining edges!!! no pathFace!! (joinHalfEdges_jiawei)" << endl;
        return;
    }
    //create new half Edge:
    VoriGraphHalfEdge newHalfEdge;
    //   newHalfEdge.halfEdges = pSecond->halfEdges;
    //   newHalfEdge.halfEdges.insert(newHalfEdge.halfEdges.begin(), pFirst->halfEdges.begin(), pFirst->halfEdges.end());


    //for Room----ID
    if (mergeRoomDeadEnd) {
        if (pFirst->roomId == pSecond->roomId) {
            newHalfEdge.setRoomId( pFirst->roomId );
        }
    }

    //  新路径的Halfedge列表由pFirst的列表与pSecond的列表拼接而成
    newHalfEdge.pathEdges = pSecond->pathEdges;
    newHalfEdge.pathEdges.insert( newHalfEdge.pathEdges.begin(), pFirst->pathEdges.begin(), pFirst->pathEdges.end());

    newHalfEdge.source = pFirst->source;
    newHalfEdge.target = pSecond->target;
    newHalfEdge.distance = pFirst->distance + pSecond->distance;
    newHalfEdge.obstacleMinimum = min( pFirst->obstacleMinimum, pSecond->obstacleMinimum );
    // calculate the new average distance to obstacles - as good as we can wieghed on the distance (lengths) of the parts...
    // 新路径的障碍物平均距离为原俩路径的障碍物平均距离的加权平均
    newHalfEdge.obstacleAverage = pFirst->obstacleAverage * pFirst->distance / (pFirst->distance + pSecond->distance) +
                                  pSecond->obstacleAverage * pSecond->distance / (pFirst->distance + pSecond->distance);

    // join the polygons of two paths!
    VoriGraphPolygon newPolygon;
    std::list<topo_geometry::point> newpolygonpoints = newHalfEdge.joinPolygon( pFirst, pSecond );
    newPolygon.polygonpoints.splice( newPolygon.polygonpoints.end(), newpolygonpoints );

    newPolygon.sites.splice( newPolygon.sites.end(), pFirst->pathFace->sites );
    newPolygon.sites.splice( newPolygon.sites.end(), pSecond->pathFace->sites );

    //   remove from vertexes 从source和target的列表里删除pFirst和pSecond
    pFirst->source->removeHalfEdge( pFirst );
    pFirst->target->removeHalfEdge( pFirst );
    pSecond->source->removeHalfEdge( pSecond );
    pSecond->target->removeHalfEdge( pSecond );
    // check if middle vertex has to be deleted
    if (pFirst->target->edgesConnected.empty()) {   //从全图删除pFirst的终节点（或pSecond的始节点）
        //     remove vertex from Graph
        vertices.erase( pFirst->target->point );
        //     verticesList.remove(*pFirst->target);

    }

    //从全图删除pFirst和pSecond的polygon
    for (std::list<VoriGraphPolygon>::iterator itr = pathFaces.begin(); itr != pathFaces.end();) {
        if (&*itr == pFirst->pathFace || &*itr == pSecond->pathFace) {
            itr = pathFaces.erase( itr );
        } else ++itr;
    }
    // remove edges 从全图删除pFirst和pSecond
    for (std::list<VoriGraphHalfEdge>::iterator itr = halfEdges.begin(); itr != halfEdges.end();) {
        if (&*itr == pFirst || &*itr == pSecond) {
            itr = halfEdges.erase( itr );
        } else ++itr;
    }
    // add new half Edge to list
    halfEdges.push_back( newHalfEdge );
    // add new half Edge to vertices
    VoriGraphHalfEdge *edgePtr = &*halfEdges.rbegin();   //rbegin()返回该iterator的最后一个位置的指针：edgePtr为newHalfEdge的指针
    assert( edgePtr != 0 );
    newHalfEdge.target->edgesConnected.push_back( edgePtr );
    newHalfEdge.source->edgesConnected.push_back( edgePtr );
    newPolygon.belongpaths.push_back( edgePtr );

    pathFaces.push_back( newPolygon );
    VoriGraphPolygon *polygonPtr = &*pathFaces.rbegin();
    assert( polygonPtr != 0 );
    edgePtr->pathFace = polygonPtr;

    // see if the twin is already there - to mark it...
    newHalfEdge.target->markTwins();


    //for Room----Border
    if (mergeRoomDeadEnd) {
        //after merging, deadend should be regarded as room and set the same roomid as path
        if (newHalfEdge.source->edgesConnected.size() == 2) {
            newHalfEdge.source->markBorderVertex();
            newHalfEdge.source->setRoomId( newHalfEdge.getRoomId());
        }
        //dead end set as border
        if (newHalfEdge.target->edgesConnected.size() == 2) {
            newHalfEdge.target->markBorderVertex();
            newHalfEdge.target->setRoomId( newHalfEdge.getRoomId());
        }
    }
}


void VoriGraph::joinHalfEdges() {    //遍历全图找出只连接了两条路径（不算对偶路径）的节点，把其上两条路径join起来（两边的半边分别join）
    for (std::map<topo_geometry::point, VoriGraphVertex>::iterator itr = vertices.begin(); itr != vertices.end();) {
        // check that there are only 4 halfEdges
        if (itr->second.edgesConnected.size() == 4) { // 该节点上连了4条path才可合并：pFirst和pSecond及其各自对偶路径
            // check that all halfEdges are not rays
            bool continueAfterwards = false;
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->isRay()) {
                    ++itr;
                    continueAfterwards = true;
                    break;
                }
            }
            if (continueAfterwards) continue;  //节点上连了一条ray则不合并
            // itr will be invalidated because its entry will be deleted ... save the next one already here.
            map<topo_geometry::point, VoriGraphVertex>::iterator next = itr;
            ++next;   //指向下一个节点
            // find the two edges for which this vertex is the target and the two for which this vertex is the source
            VoriGraphHalfEdge *targetFirst = 0;
            VoriGraphHalfEdge *targetSecond = 0;
            VoriGraphHalfEdge *sourceFirst = 0;
            VoriGraphHalfEdge *sourceSecond = 0;
            //遍历 itr节点的四条连接路径，两条为以itr为始节点的source edge，两条为以itr为终结点的target edge
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->source == &itr->second) {
                    // this is a source edge
                    if (sourceFirst == 0) sourceFirst = *itr2; else sourceSecond = *itr2;
                } else {
                    // this is a target edge
                    if (targetFirst == 0) targetFirst = *itr2; else targetSecond = *itr2;
                }
            }
            if (!(sourceFirst && sourceSecond && targetFirst && targetSecond)) {
                //Strange - this DOES happen - why?
//         cerr<<"something is really fishy here"<<sourceFirst << " " <<sourceSecond <<" "<< targetFirst <<" "<< targetSecond<<endl;
//         assert(0);
                ++itr;
                continue;
            }
            // ok find the two to be joined pairs - not the twins...
            //分别连接两次半边
            if (targetFirst->twin == sourceFirst) {
                // make targetFirst+sourceSecond   and   targetSecond+sourceFirst
                joinHalfEdges( targetFirst, sourceSecond );
                joinHalfEdges( targetSecond, sourceFirst );
            } else {
                // make targetFrist+sourceFirst  and  targetSecond+sourceSecond
                joinHalfEdges( targetFirst, sourceFirst );
                joinHalfEdges( targetSecond, sourceSecond );
            }
            itr = next;
        } else { // if 4 edges connected
            ++itr;
        }
    }
    markDeadEnds();
}


void VoriGraph::joinHalfEdges_jiawei() {    //遍历全图找出只连接了两条路径（不算对偶路径）的节点，把其上两条路径join起来（两边的半边分别join）
    for (std::map<topo_geometry::point, VoriGraphVertex>::iterator itr = vertices.begin(); itr != vertices.end();) {
        // check that there are only 4 halfEdges
        if (itr->second.edgesConnected.size() == 4) { // 该节点上连了4条path才可合并：pFirst和pSecond及其各自对偶路径
            // check that all halfEdges are not rays
            bool continueAfterwards = false;
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->isRay()) {
                    ++itr;
                    continueAfterwards = true;
                    break;
                }
            }
            if (continueAfterwards) continue;  //节点上连了一条ray则不合并
            // itr will be invalidated because its entry will be deleted ... save the next one already here.
            map<topo_geometry::point, VoriGraphVertex>::iterator next = itr;
            ++next;   //指向下一个节点
            // find the two edges for which this vertex is the target and the two for which this vertex is the source
            VoriGraphHalfEdge *targetFirst = 0;
            VoriGraphHalfEdge *targetSecond = 0;
            VoriGraphHalfEdge *sourceFirst = 0;
            VoriGraphHalfEdge *sourceSecond = 0;
            //遍历 itr节点的四条连接路径，两条为以itr为始节点的source edge，两条为以itr为终结点的target edge
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->source == &itr->second) {
                    // this is a source edge
                    if (sourceFirst == 0) sourceFirst = *itr2; else sourceSecond = *itr2;
                } else {
                    // this is a target edge
                    if (targetFirst == 0) targetFirst = *itr2; else targetSecond = *itr2;
                }
            }
            if (!(sourceFirst && sourceSecond && targetFirst && targetSecond)) {
                //Strange - this DOES happen - why?
//         cerr<<"something is really fishy here"<<sourceFirst << " " <<sourceSecond <<" "<< targetFirst <<" "<< targetSecond<<endl;
//         assert(0);
                ++itr;
                continue;
            }
            // ok find the two to be joined pairs - not the twins...
            //分别连接两次半边
            if (targetFirst->twin == sourceFirst) {
                // make targetFirst+sourceSecond   and   targetSecond+sourceFirst
                joinHalfEdges_jiawei( targetFirst, sourceSecond );
                joinHalfEdges_jiawei( targetSecond, sourceFirst );
            } else {
                // make targetFrist+sourceFirst  and  targetSecond+sourceSecond
                joinHalfEdges_jiawei( targetFirst, sourceFirst );
                joinHalfEdges_jiawei( targetSecond, sourceSecond );
            }
            itr = next;
        } else { // if 4 edges connected
            ++itr;
        }
    }
    markDeadEnds();
}

void VoriGraph::joinHalfEdges_tianyan() {    //遍历全图找出只连接了两条路径（不算对偶路径）的节点，把其上两条路径join起来（两边的半边分别join）
    for (std::map<topo_geometry::point, VoriGraphVertex>::iterator itr = vertices.begin(); itr != vertices.end();) {
        // check that there are only 4 halfEdges
        if (itr->second.edgesConnected.size() == 4) { // 该节点上连了4条path才可合并：pFirst和pSecond及其各自对偶路径
            // check that all halfEdges are not rays
            bool continueAfterwards = false;
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->isRay()) {
                    ++itr;
                    continueAfterwards = true;
                    break;
                }
            }

            //room vertex
            if (itr->second.roomVertex) {
                continueAfterwards = true;
            }
            if (continueAfterwards) continue;  //节点上连了一条ray则不合并
            // itr will be invalidated because its entry will be deleted ... save the next one already here.
            map<topo_geometry::point, VoriGraphVertex>::iterator next = itr;
            ++next;   //指向下一个节点
            // find the two edges for which this vertex is the target and the two for which this vertex is the source
            VoriGraphHalfEdge *targetFirst = 0;
            VoriGraphHalfEdge *targetSecond = 0;
            VoriGraphHalfEdge *sourceFirst = 0;
            VoriGraphHalfEdge *sourceSecond = 0;
            //遍历 itr节点的四条连接路径，两条为以itr为始节点的source edge，两条为以itr为终结点的target edge
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = itr->second.edgesConnected.begin();
                 itr2 != itr->second.edgesConnected.end(); ++itr2) {
                if ((*itr2)->source == &itr->second) {
                    // this is a source edge
                    if (sourceFirst == 0) sourceFirst = *itr2; else sourceSecond = *itr2;
                } else {
                    // this is a target edge
                    if (targetFirst == 0) targetFirst = *itr2; else targetSecond = *itr2;
                }
            }
            if (!(sourceFirst && sourceSecond && targetFirst && targetSecond)) {
                //Strange - this DOES happen - why?
//         cerr<<"something is really fishy here"<<sourceFirst << " " <<sourceSecond <<" "<< targetFirst <<" "<< targetSecond<<endl;
//         assert(0);
                ++itr;
                continue;
            }
            // ok find the two to be joined pairs - not the twins...
            //分别连接两次半边
            if (targetFirst->twin == sourceFirst) {
                // make targetFirst+sourceSecond   and   targetSecond+sourceFirst
                joinHalfEdges_tianyan( targetFirst, sourceSecond );
                joinHalfEdges_tianyan( targetSecond, sourceFirst );
            } else {
                // make targetFrist+sourceFirst  and  targetSecond+sourceSecond
                joinHalfEdges_tianyan( targetFirst, sourceFirst );
                joinHalfEdges_tianyan( targetSecond, sourceSecond );
            }
            itr = next;
        } else { // if 4 edges connected
            ++itr;
        }
    }
    markDeadEnds();
}

void VoriGraph::markDeadEnds_isRoomVertex() {   //遍历全图mark出deadend路径
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = halfEdges.begin(); itr != halfEdges.end(); ++itr) {
        //该路径是ray 或者 路径连接的始（终）节点上连接了<=2条路径(2条：同一条边的对偶边) 则标记 该路径为deadend
        if (itr->isRay()) {
            itr->deadEnd = true;
            continue;
        }
        if (itr->source->edgesConnected.size() < 3) {
            itr->deadEnd = true;
            itr->source->markBorderVertex();
        }
        if (itr->target->edgesConnected.size() < 3) {
            itr->deadEnd = true;
            itr->target->markBorderVertex();
        }
    }
}

void VoriGraph::markDeadEnds() {   //遍历全图mark出deadend路径
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = halfEdges.begin(); itr != halfEdges.end(); ++itr) {
        //该路径是ray 或者 路径连接的始（终）节点上连接了<=2条路径(2条：同一条边的对偶边) 则标记 该路径为deadend
        if (itr->isRay()) {
            itr->deadEnd = true;
            continue;
        }
        if (itr->source->edgesConnected.size() < 3) itr->deadEnd = true;
        if (itr->target->edgesConnected.size() < 3) itr->deadEnd = true;
    }
}

// 从该节点的edgesConnected列表里删去路径edge
bool VoriGraphVertex::removeHalfEdge(VoriGraphHalfEdge *edge) {
    for (std::list<VoriGraphHalfEdge *>::iterator itr = edgesConnected.begin(); itr != edgesConnected.end(); ++itr) {
        if (*itr == edge) {
            edgesConnected.erase( itr );
            return true;
        }
    }
    return false;
}

void VoriGraphVertex::markTwins() {  //从该节点的edgesConnected里面找出对偶路径
    for (std::list<VoriGraphHalfEdge *>::iterator itr = edgesConnected.begin(); itr != edgesConnected.end(); ++itr) {
        if ((*itr)->twin == 0) {
            //look for its twin
            for (std::list<VoriGraphHalfEdge *>::iterator itr2 = edgesConnected.begin();
                 itr2 != edgesConnected.end(); ++itr2) {
                if (((*itr)->target == (*itr2)->source) && ((*itr)->source == (*itr2)->target)
                    && ((*itr)->pathEdges.begin()->t().y()) == ((*itr2)->pathEdges.rbegin()->s().y())
                    && ((*itr)->pathEdges.begin()->t().x()) == ((*itr2)->pathEdges.rbegin()->s().x())) {
                    // this is the twin - mark both!
                    (*itr)->twin = *itr2;
                    (*itr2)->twin = *itr;
                }
            }
        }
    }
}


std::list<VoriGraphHalfEdge>::iterator
VoriGraph::removeHalfEdge(std::list<VoriGraphHalfEdge>::iterator &remove) {
    // remove yourself from the vertices - and delete those if you are the last one..
    if (remove->target) {   //从target节点的edgesConnected列表里删去remove，如果删去后target上没有其他连接的路径则删去target
        remove->target->removeHalfEdge( &*remove );
        if (remove->target->edgesConnected.empty()) {
            vertices.erase( remove->target->point );
            remove->target = 0;
        }
    }
    if (remove->source) {   //从source节点的edgesConnected列表里删去remove，如果删去后source上没有其他连接的路径则删去target
        remove->source->removeHalfEdge( &*remove );
        if (remove->source->edgesConnected.empty()) {
            vertices.erase( remove->source->point );
            remove->source = 0;
        }
    }
    // remove yourself from the list
    remove = halfEdges.erase( remove );
    return remove;
}

std::list<VoriGraphHalfEdge>::iterator
VoriGraph::removeHalfEdge_tianyan(std::list<VoriGraphHalfEdge>::iterator &remove, bool deleteEmpty,
                                  bool deleteRoomBorder) {
    // remove yourself from the vertices - and delete those if you are the last one..
    if (remove->target) {
        remove->target->removeHalfEdge( &*remove );
        if (deleteEmpty && remove->target->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->target->isBorderVertex()))) {
                vertices.erase( remove->target->point );
                remove->target = 0;
            }
        }
    }
    if (remove->source) {
        remove->source->removeHalfEdge( &*remove );
        if (deleteEmpty && remove->source->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->source->isBorderVertex()))) {
                vertices.erase( remove->source->point );
                remove->source = 0;
            }
        }
    }
    // remove yourself from the list
    remove = halfEdges.erase( remove );
    return remove;
}

std::list<VoriGraphHalfEdge>::iterator
VoriGraph::removeHalfEdge_roomPolygon(std::list<VoriGraphHalfEdge>::iterator &remove,
                                      bool deleteEmpty, //default:true
                                      bool deleteRoomBorder) {  //default:true
    // remove yourself from the vertices - and delete those if you are the last one..
    if (remove->target) {
        remove->target->removeHalfEdge( &*remove );
        if (deleteEmpty && remove->target->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->target->isBorderVertex()))) {
                vertices.erase( remove->target->point );
                remove->target = 0;
            }
        }
    }
    if (remove->source) {
        remove->source->removeHalfEdge( &*remove );
        if (deleteEmpty && remove->source->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->source->isBorderVertex()))) {
                vertices.erase( remove->source->point );
                remove->source = 0;
            }
        }
    }
    //jiawei:remove its polygon from graph
    if (remove->pathFace) {
        pathFaces.remove( *remove->pathFace );
        remove->pathFace = 0;
    }
    // remove yourself from the list
    remove = halfEdges.erase( remove );
    return remove;
}
void VoriGraph::removeHalfEdge_roomPolygon(VoriGraphHalfEdge *remove,
                                      bool deleteEmpty, //default:true
                                      bool deleteRoomBorder) {  //default:true
    // remove yourself from the vertices - and delete those if you are the last one..
    if (remove->target) {
        remove->target->removeHalfEdge( remove );
        if (deleteEmpty && remove->target->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->target->isBorderVertex()))) {
                vertices.erase( remove->target->point );
                remove->target = 0;
            }
        }
    }
    if (remove->source) {
        remove->source->removeHalfEdge( remove );
        if (deleteEmpty && remove->source->edgesConnected.empty()) {
            if (deleteRoomBorder || ((!deleteRoomBorder) && !(remove->source->isBorderVertex()))) {
                vertices.erase( remove->source->point );
                remove->source = 0;
            }
        }
    }
    //jiawei:remove its polygon from graph
    if (remove->pathFace) {
        pathFaces.remove( *(remove->pathFace) );
        remove->pathFace = 0;
    }
    // remove yourself from the list
    halfEdges.remove( *remove );
//    return remove;
}

std::list<VoriGraphHalfEdge>::iterator
VoriGraph::removeHalfEdge_jiawei(std::list<VoriGraphHalfEdge>::iterator &remove) {
    // remove yourself from the vertices - and delete those if you are the last one..
    if (remove->target) {   //从target节点的edgesConnected列表里删去remove，如果删去后target上没有其他连接的路径则删去target
        remove->target->removeHalfEdge( &*remove );
        if (remove->target->edgesConnected.empty()) {
            vertices.erase( remove->target->point );
            remove->target = 0;
        }
    }
    if (remove->source) {   //从source节点的edgesConnected列表里删去remove，如果删去后source上没有其他连接的路径则删去target
        remove->source->removeHalfEdge( &*remove );
        if (remove->source->edgesConnected.empty()) {
            vertices.erase( remove->source->point );
            remove->source = 0;
        }
    }
    //jiawei:remove its polygon from graph
    if (remove->pathFace) {
        pathFaces.remove( *remove->pathFace );
        remove->pathFace = 0;
    }
    // remove yourself from the list
    remove = halfEdges.erase( remove );     // 把remove从VoriGraph里的 VoriGraphHalfEdge列表里删去
    return remove;
}


//遍历group计算dist，并把group的边标相应的groupId
double traverseGroupCalcDist(VoriGraph &voriGraph, VoriGraphHalfEdge *const &edge, const unsigned int &groupId) {
    if (edge->groupId != 0 && edge->groupId != groupId) {
        cout << "something is really fishy here!!" << endl;
        assert( 0 );
    }
    if (edge->groupId != 0) return 0.;
    double dist = edge->distance;
    if (edge->isRay()) dist = 0.; // 0 distance for rays!
    edge->groupId = groupId;
    if (edge->source) {
        edge->source->groupId = groupId;
        for (std::list<VoriGraphHalfEdge *>::iterator itr = edge->source->edgesConnected.begin();
             itr != edge->source->edgesConnected.end(); ++itr) {
            dist += traverseGroupCalcDist( voriGraph, *itr, groupId );
        }
    }
    if (edge->target) {
        edge->target->groupId = groupId;
        for (std::list<VoriGraphHalfEdge *>::iterator itr = edge->target->edgesConnected.begin();
             itr != edge->target->edgesConnected.end(); ++itr) {
            dist += traverseGroupCalcDist( voriGraph, *itr, groupId );
        }
    }
    return dist;
}

//为所有边分组并标记相应的groupId,计算每个组的边总长存进其中一条边及其Id，全部组存进groups
void gernerateGroupId(VoriGraph &voriGraph) {
    // first get rid of all (previous) groups
    voriGraph.groups.clear();

    removeGroupId( voriGraph );
    unsigned int currentGroupId = 0;
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end(); ++itr) {
        if (itr->groupId == 0) {
            //start a new group
            ++currentGroupId;
            double distance = traverseGroupCalcDist( voriGraph, &*itr, currentGroupId );
            VoriGroup group;
            group.edge = &*itr;
            group.groupId = currentGroupId;
            group.distance = distance;
            voriGraph.groups.push_back( group );
        }
    }
}

void removeGroupId(VoriGraph &voriGraph) {
    for (std::list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin();
         itr != voriGraph.halfEdges.end(); ++itr) {
        itr->groupId = 0;
    }
    for (VoriGraph::VertexMap::iterator itr = voriGraph.vertices.begin(); itr != voriGraph.vertices.end(); ++itr) {
        itr->second.groupId = 0;
    }
}

//分别删除voriGraph里halfEdges、vertices、groups里标号不是 groupId的路径、节点、组
void removeAllGroupsBut(VoriGraph &voriGraph, unsigned int groupId) {
    for (std::list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end();) {
        if (itr->groupId == groupId) {
            //keep
            ++itr;
            continue;
        }
        //remove
        itr = voriGraph.halfEdges.erase( itr );
    }
    for (VoriGraph::VertexMap::iterator itr = voriGraph.vertices.begin(); itr != voriGraph.vertices.end();) {
        if (itr->second.groupId == groupId) {
            //keep
            ++itr;
            continue;
        }
        //remove
        VoriGraph::VertexMap::iterator toRemove = itr;
        ++itr;
        voriGraph.vertices.erase( toRemove );
    }
    VoriGroup keep;
    for (list<VoriGroup>::iterator itr = voriGraph.groups.begin(); itr != voriGraph.groups.end(); ++itr) {
        if (itr->groupId == groupId) {
            keep = *itr;
        }
    }
    voriGraph.groups.clear();
    voriGraph.groups.push_back( keep );
}

bool compareGroups(const VoriGroup &g1, const VoriGroup &g2) {
    return g1.distance > g2.distance;
}

void keepBiggestGroup(VoriGraph &voriGraph) {
    voriGraph.groups.sort( compareGroups );//按照各个group的总边长从大到小排序
    cout << " keeping " << voriGraph.groups.begin()->groupId << endl;
    removeAllGroupsBut( voriGraph, voriGraph.groups.begin()->groupId );
}

void printGraphStatistics(VoriGraph &voriGraph, std::string str) {
//    cout << str << " - graph statistics: number of half edges " << voriGraph.halfEdges.size() << "  number of vertices "
//         << voriGraph.vertices.size();
    double distance = 0.;
    for (std::list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin();
         itr != voriGraph.halfEdges.end(); ++itr) {
        distance += itr->distance;
    }
//    cout << " distance/2: " << distance / 2 << endl;  //把全图路径（不包括对偶路径）的长度和打印出来
}


void removeRays(VoriGraph &voriGraph) {
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end();) {
        if (itr->isRay()) {
            // remove it from vertexs
            if (itr->source) itr->source->removeHalfEdge( &*itr );
            if (itr->target) itr->target->removeHalfEdge( &*itr );
            // remove from graph
            itr = voriGraph.halfEdges.erase( itr );
        } else {
            ++itr;
        }
    }
}

void printGraph(VoriGraph &voriGraph) {
    unsigned int county = 0;
    for (std::list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin();
         itr != voriGraph.halfEdges.end(); ++itr, ++county) {
        cout << county << " Half edge ";
        if (itr->isRay()) cout << "(ray)";
        else if (itr->deadEnd) cout << "deadEnd" << endl; else cout << endl;
        cout << "\tfrom: ";
        if (itr->source) cout << topo_geometry::print( itr->source->point ); else cout << "INF";
        if (itr->source) cout << topo_geometry::print( itr->source->point ); else cout << "INF";
        cout << " to: ";
        if (itr->target) cout << topo_geometry::print( itr->target->point ); else cout << "INF";
        cout << endl;
    }
    cout << endl << "---- Vertices ---- " << endl;
    county = 0;
    for (map<topo_geometry::point, VoriGraphVertex>::iterator itr = voriGraph.vertices.begin();
         itr != voriGraph.vertices.end(); ++itr) {
        cout << county << " Vertex with " << itr->second.edgesConnected.size() << " half edges connected" << endl;
    }
}

double dist_gp(topo_geometry::point a, topo_geometry::point b) {
    double dx = a.x() - b.x();
    double dy = a.y() - b.y();
    return sqrt( dx * dx + dy * dy );
}

double computeAngle_de(topo_geometry::point o, topo_geometry::point p) {//计算向量op与x轴的逆时针夹角（角度制）
    double dx = p.x() - o.x();
    double dy = p.y() - o.y();
    double cosa = fabs( dx ) / dist_gp( o, p );
    double angle, result = acos( cosa ) * 180.0 / M_PI;
    if (dx >= 0 && dy >= 0) {//第一象限
        angle = result;
    } else if (dx < 0 && dy >= 0) {//第二象限
        angle = 180 - result;
    } else if (dx < 0 && dy < 0) {//第三象限
        angle = 180 + result;
    } else {// 第四象限
        angle = 360 - result;
    }
    return angle;
}

void removeDeadEnds_addFacetoPolygon(VoriGraph &voriGraph, double maxDist) {
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end(); itr++) {
        //从图中删去该deadEnd，若其端点只连了该deadEnd则删去该节点
        if (itr->deadEnd && (!itr->isRay()) && itr->distance < maxDist) {
            // remove it from vertices
            if (itr->source->edgesConnected.size() <= 2 && itr->target->edgesConnected.size() <= 6 &&
                itr->pathFace) {
//                std::cout<<"itr->target->edgesConnected.size() <= 6, whose position is "<<itr->target->point.x()<<", "<<itr->target->point.y();
                double min_angle = 361;
                VoriGraphHalfEdge *joint_h = 0;
                double deadend_angle = computeAngle_de( itr->target->point, itr->source->point );
                //该for循环用于寻找deadend右边的第一条边
                for (std::list<VoriGraphHalfEdge *>::iterator eitr = itr->target->edgesConnected.begin();
                     eitr != itr->target->edgesConnected.end(); eitr++) {
                    if ((*eitr) != (*itr).twin && (*eitr)->source == itr->target && !(*eitr)->isRay()) {
                        double itr_angle = computeAngle_de((*eitr)->source->point, (*eitr)->target->point );
                        //deadend_angle - itr_angle： 从deadend旋转 逆时针角度最小
                        double d_angle = deadend_angle < itr_angle ? (deadend_angle + 360 - itr_angle) : deadend_angle -
                                                                                                         itr_angle;
//                        double d_angle = deadend_angle > itr_angle ? (itr_angle + 360 - deadend_angle) : itr_angle - deadend_angle;
                        if (d_angle < min_angle) {
                            min_angle = d_angle;
                            joint_h = (*eitr);
                        }
                    }
                }

                //优先向右合并polygon，如果这条deadend的右边第一条边joint_h是一条deadend的话就向左合并
                if (joint_h) {//找到了它右边的边
                    VoriGraphHalfEdge *twinHalfedge = (*itr).twin;
                    if (twinHalfedge) {
                        VoriGraphPolygon *twinpolygonPtr = twinHalfedge->pathFace;
                        if (twinpolygonPtr != 0) {
                            std::list<topo_geometry::point>::iterator pitr = itr->pathFace->polygonpoints.begin();
//                                VoriGraph::Polygon_2 tem_poly;
//                                for (; pitr != itr->pathFace->polygonpoints.end(); pitr++) {
//                                    tem_poly.push_back(VoriGraph::Point(pitr->x(),pitr->y()));
//                                }
//                                std::cout<<"edge "<<(*itr).source->point.x()<<","<<(*itr).source->point.y()<<"-"
//                                         <<(*itr).target->point.x()<<","<<(*itr).target->point.y()<<"'s polygon order in clockwise: "
//                                         <<tem_poly.is_counterclockwise_oriented()<<std::endl;
                            for (; pitr != itr->pathFace->polygonpoints.end(); pitr++) {
                                if (topo_geometry::operator==( *pitr, itr->target->point )) {
                                    pitr++;
                                    break;
                                }
                            }//pitr:deadend的polygonpoints的target+1的位置
                            std::list<topo_geometry::point>::iterator pitr2 = twinpolygonPtr->polygonpoints.begin();
//                            VoriGraph::Polygon_2 tem_poly;
//                            for (; pitr2 != twinHalfedge->pathFace->polygonpoints.end(); pitr2++) {
//                                tem_poly.push_back(VoriGraph::Point(pitr2->x(),pitr2->y()));
//                            }
//                            std::cout<<"edge "<<(*twinHalfedge).source->point.x()<<","<<(*twinHalfedge).source->point.y()<<"-"
//                                     <<(*twinHalfedge).target->point.x()<<","<<(*twinHalfedge).target->point.y()<<"'s polygon order in clockwise: "
//                                     <<tem_poly.is_counterclockwise_oriented()<<std::endl;
                            for (; pitr2 != twinpolygonPtr->polygonpoints.end(); pitr2++) {
                                if (topo_geometry::operator==( *pitr2, twinHalfedge->target->point )) {
                                    pitr2++;
                                    break;
                                }
                            }//pitr2:deadend的twin的polygonpoints的target+1的位置
                            std::list<topo_geometry::point> deadend_sites;
                            deadend_sites.splice( deadend_sites.end(), twinpolygonPtr->sites );
                            deadend_sites.splice( deadend_sites.end(), itr->pathFace->sites );
                            if (joint_h->deadEnd) {
                                //deadend右边的第一条边是deadend： 把deadend向左合并—— 把deadend及其twin的polygon都合并到左边的polygon

                                double min_anglel = 361;
                                for (std::list<VoriGraphHalfEdge *>::iterator eitr = twinHalfedge->source->edgesConnected.begin();
                                     eitr != twinHalfedge->source->edgesConnected.end(); eitr++) {
                                    if ((*eitr) != (*twinHalfedge).twin && (*eitr)->target == twinHalfedge->source &&
                                        !(*eitr)->isRay()) {
                                        double itr_angle = computeAngle_de((*eitr)->target->point,
                                                                           (*eitr)->source->point );
                                        double d_angle = deadend_angle > itr_angle ? (itr_angle + 360 - deadend_angle) :
                                                         itr_angle - deadend_angle;

//                                        double d_angle = deadend_angle < itr_angle ? (deadend_angle + 360 - itr_angle) : deadend_angle -itr_angle;
                                        if (d_angle < min_anglel) {
                                            min_anglel = d_angle;
                                            joint_h = (*eitr);
                                        }
                                    }
                                }//找到deadend左边的边
//                                std::cout<<"size of deadend_sites is "<<deadend_sites.size()<<std::endl;
                                joint_h->pathFace->sites.splice( joint_h->pathFace->sites.end(), deadend_sites );
                                std::list<topo_geometry::point>::iterator epitr = joint_h->pathFace->polygonpoints.begin();
                                for (; epitr != joint_h->pathFace->polygonpoints.end(); epitr++) {
                                    if (topo_geometry::operator==( *epitr, joint_h->target->point )) {
                                        epitr++;
                                        break;
                                    }
                                }
                                if (pitr != itr->pathFace->polygonpoints.end() ||
                                    pitr2 != twinpolygonPtr->polygonpoints.end()) {
                                    joint_h->pathFace->polygonpoints.splice( epitr, itr->pathFace->polygonpoints, pitr,
                                                                             itr->pathFace->polygonpoints.end());
                                    joint_h->pathFace->polygonpoints.splice( epitr, twinpolygonPtr->polygonpoints,
                                                                             pitr2,
                                                                             twinpolygonPtr->polygonpoints.end());
                                }
                            } else {
                                //把deadend向右合并
                                joint_h->pathFace->sites.splice( joint_h->pathFace->sites.begin(),
                                                                 deadend_sites );
                                if (pitr != itr->pathFace->polygonpoints.end() ||
                                    pitr2 != twinpolygonPtr->polygonpoints.end()) {
//                                    joint_h->pathFace->polygonpoints.splice(joint_h->pathFace->polygonpoints.end(),
//                                                                            itr->pathFace->polygonpoints,pitr,
//                                                                            itr->pathFace->polygonpoints.end());
//                                    joint_h->pathFace->polygonpoints.splice(joint_h->pathFace->polygonpoints.end(),
//                                                                            twinpolygonPtr->polygonpoints,pitr2,
//                                                                            twinpolygonPtr->polygonpoints.end());
                                    for (; pitr != itr->pathFace->polygonpoints.end(); pitr++) {
                                        joint_h->pathFace->polygonpoints.insert( joint_h->pathFace->polygonpoints.end(),
                                                                                 *pitr );
                                    }
                                    for (; pitr2 != twinpolygonPtr->polygonpoints.end(); pitr2++) {
                                        joint_h->pathFace->polygonpoints.insert( joint_h->pathFace->polygonpoints.end(),
                                                                                 *pitr2 );
                                    }
                                }
                            }
                        }//if (twinpolygonPtr != 0)
                    }//if(twinHalfedge)
                }//if(joint_h)
            }//if(itr->source->edgesConnected.size()<=2&&itr->target->edgesConnected.size()<=6)
        }//if(itr->deadEnd)
    }//for(itr)
    removeDeadEnds( voriGraph, maxDist );
}

void removeDeadEnds(VoriGraph &voriGraph, double maxDist) {
    std::list<VoriGraphHalfEdge>::iterator itr;
    for (itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end();) {
        //从图中删去该deadEnd，若其端点只连了该deadEnd则删去该节点
        if (itr->deadEnd && (!itr->isRay()) && itr->distance < maxDist) {
            // remove it from vertices
            itr->source->removeHalfEdge( &*itr ); //从itr的始节点的edgesConnected删去该边
            if (itr->source->edgesConnected.empty()) voriGraph.vertices.erase( itr->source->point );
            itr->target->removeHalfEdge( &*itr ); //从itr的终节点的edgesConnected删去该边
            if (itr->target->edgesConnected.empty()) voriGraph.vertices.erase( itr->target->point );
            // remove from graph
            itr = voriGraph.halfEdges.erase( itr );
        } else {
            ++itr;
        }
    }
}

bool isInEdges(VoriGraphHalfEdge *search, VoriGraph &voriGraph) {
    for (list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end(); ++itr) {
        if (&*itr == search) return true;
    }
    return false;
}

bool isInVertices(VoriGraphVertex *search, VoriGraph &voriGraph) {
    for (map<topo_geometry::point, VoriGraphVertex>::iterator itrVertices = voriGraph.vertices.begin();
         itrVertices != voriGraph.vertices.end(); ++itrVertices) {
        if (&itrVertices->second == search) return true;
    }
    return false;
}


// 寻找距离该路径始节点为pDistance远的点
bool VoriGraphHalfEdge::getPointForDistance(double pDistance, topo_geometry::point &pPoint) {
    if (pDistance > distance) return false;
    double currDistance = 0.;

    std::list<topo_geometry::Halfedge>::iterator pathEdgeItr = pathEdges.begin();
    for (; pathEdgeItr != pathEdges.end(); pathEdgeItr++) {
        topo_geometry::point source = pathEdgeItr->s();
        topo_geometry::point target = pathEdgeItr->t();

        double d = pathEdgeItr->length();
        if (d + currDistance >= pDistance) {
            double xDiff = topo_geometry::getX( target ) - topo_geometry::getX( source );
            double yDiff = topo_geometry::getY( target ) - topo_geometry::getY( source );
            double para = (pDistance - currDistance) / d;
            topo_geometry::point rtn( topo_geometry::getX( source ) + xDiff * para,
                                      topo_geometry::getY( source ) + yDiff * para );
            pPoint = rtn;
            return true;
        }
        currDistance += d;
    }

    //add from yutianyan
    if (fabs( currDistance - pDistance ) < thresholdForCut) {
        pPoint = pathEdgeItr->t();
        return true;
    } else {
        cerr << "What!? we should never reach here!!!!" << endl;
        return true;
    }
}


std::list<VoriGraphHalfEdge> VoriGraphHalfEdge::cutVoriGraphHalfEdge_Polygon_accruay(
        double cutlength,
        VoriGraphVertex &pPoint,    //should be the source, let me try
        std::list<VoriGraphPolygon> &cuttedPolygons_list) {
    cuttedPolygons_list.clear();
    std::list<VoriGraphHalfEdge> VoriGraphHalfEdgeCutted;
    VoriGraphHalfEdgeCutted.clear();
    if ((cutlength - EPSINON > distance) || (cutlength + EPSINON < 0)) {
        //0. can't cut (size of the returned list is 0)
        return VoriGraphHalfEdgeCutted;
    }
    if ((cutlength - EPSINON > 0) && (cutlength + EPSINON < distance)) {

        //1. cut the halfedge and save in VoriGraphHalfEdgeCut_first and VoriGraphHalfEdgeCut_second
        double cutDistancefromsource = 0.;//要剪的长度（与source距离）

        if (pPoint == *source) {
            cutDistancefromsource = cutlength;
        } else {
            if (pPoint == *target) {
                cutDistancefromsource = distance - cutlength;
            } else {
                //cut from neither source nor target...error(size of the returned list is 0)
                cout << "cut from neither source nor target...error (VoriGraph.cpp)" << endl;
                return VoriGraphHalfEdgeCutted;
            }
        }
        double currDistance = 0.;   //目前遍历过的小短边的长度和
        std::list<topo_geometry::Halfedge>::iterator pathEdgeItr = pathEdges.begin();
        topo_geometry::point cutPoint = pathEdges.begin()->s();
        std::list<topo_geometry::Halfedge>::iterator cutEdge = pathEdges.begin();
        cutEdge--;
        for (; pathEdgeItr != pathEdges.end(); pathEdgeItr++) {//遍历每一段看切割点是否在其上
            double d = pathEdgeItr->length();
            currDistance += d;
            if (//fabs( cutDistancefromsource - currDistance ) < minCutError &&
                    cutDistancefromsource > currDistance) {
//                cutPoint = pathEdgeItr->t();
                cutEdge = pathEdgeItr;    //到此edge为第一段，后面为另一段
            } else {
//                if(cutEdge == pathEdges.begin()) continue;
                cutEdge++;
                break;
            }
        }


        topo_geometry::point tempMiddle;
        getPointForDistance( cutDistancefromsource, tempMiddle );

//        cout<<source->point.x()<<","<<source->point.y()<<"-"
//            <<target->point.x()<<","<<target->point.y()<<": cut at ("<<tempMiddle.x()<<","<<tempMiddle.y()<<") "<<endl;
        double temdist = dist( tempMiddle.x(), tempMiddle.y(), cutEdge->o().x(),
                               cutEdge->o().y());// the distance to obstacle is not accuracy
        topo_geometry::Halfedge leftmidH( cutEdge->s(), tempMiddle, cutEdge->o(), temdist );    //not accuracy
        topo_geometry::Halfedge rightmidH( tempMiddle, cutEdge->t(), cutEdge->o(), temdist );

        VoriGraphHalfEdge VoriGraphHalfEdgeCut_first;
        VoriGraphHalfEdge VoriGraphHalfEdgeCut_second;
        //cutEdge： 到此edge为第一段，后面为另一段
        //cutSite： 剪切的path点在polygonpoints里的位置
        //cutP： 剪切的site点在polygonpoints里的位置
        VoriGraphHalfEdgeCut_first.pathEdges.insert( VoriGraphHalfEdgeCut_first.pathEdges.begin(),
                                                     pathEdges.begin(), cutEdge );
        VoriGraphHalfEdgeCut_first.pathEdges.push_back( leftmidH );

        VoriGraphHalfEdgeCut_second.pathEdges.push_back( rightmidH );
        VoriGraphHalfEdgeCut_second.pathEdges.insert( VoriGraphHalfEdgeCut_second.pathEdges.end(),
                                                      ++cutEdge, pathEdges.end());//从cutEdge后面一个pathEdge开始
        cutEdge--;
//        std::cout<<" cutEdge.s= ";coutpoint(cutEdge->s());
//        std::cout<<" cutEdge.t= ";coutpoint(cutEdge->t());std::cout<<std::endl;
//        std::cout<<"cut as two edges: "<<std::endl;
//        couthalfedge(VoriGraphHalfEdgeCut_first);
//        couthalfedge(VoriGraphHalfEdgeCut_second);
//        //vailded: edge cutting correct

        //2. if the halfedge has pathFace, split it into newPolygon_first and newPolygon_second
        if (pathFace) {
            std::list<topo_geometry::point>::iterator pItr = pathFace->polygonpoints.begin();
            std::list<topo_geometry::point>::iterator cutP = pathFace->polygonpoints.begin();
            std::list<topo_geometry::point>::iterator cutSite = pathFace->polygonpoints.end();
            cutSite--;
            double minPError = 10000, minsiteError = 10000;
            bool isSite = 0;
            for (; pItr != pathFace->polygonpoints.end(); pItr++) {//遍历每一段看切割点是否在其上
                if (isSite) {
                    if (dist_gp( *pItr, tempMiddle ) < minsiteError) {
                        minsiteError = dist_gp( *pItr, tempMiddle );
                        cutSite = pItr;   //剪切的site点在polygonpoints里的位置
                    }
                } else {
                    if (dist_gp( *pItr, cutEdge->s() ) < minPError) {
                        minPError = dist_gp( *pItr, cutEdge->s() );
                        cutP = pItr;  //剪切的path点在polygonpoints里的位置
                    }
                    if (//topo_geometry::operator==( *pItr, target->point )){ //直接用==发现会出现找不到target的情况，即只切了“半边”房间
                            fabs( pItr->x() - target->point.x()) < EPSINON &&
                            fabs( pItr->y() - target->point.y()) < EPSINON) {
                        isSite = 1;
                    }
                }
            }

            VoriGraphPolygon newPolygon_first, newPolygon_second;
            newPolygon_first.polygonpoints.insert(
                    newPolygon_first.polygonpoints.begin(),
                    pathFace->polygonpoints.begin(), ++cutP );
            newPolygon_first.polygonpoints.push_back( tempMiddle );
            newPolygon_first.polygonpoints.insert(
                    newPolygon_first.polygonpoints.end(),
                    cutSite, pathFace->polygonpoints.end());


            newPolygon_second.polygonpoints.insert(
                    newPolygon_second.polygonpoints.begin(),
                    cutP, ++cutSite );
            newPolygon_second.polygonpoints.push_front( tempMiddle );
            cutSite--;
            cutP--;
            cuttedPolygons_list.push_back( newPolygon_first );
            cuttedPolygons_list.push_back( newPolygon_second );
//            coutpolygon(pathFace->polygonpoints);
        }


        VoriGraphHalfEdgeCut_first.distance = cutDistancefromsource;
        VoriGraphHalfEdgeCut_second.distance = distance - cutDistancefromsource;

        //3. compute average and minimum of obstacle distance
        double obstacleAveragetemp = 0.;
        int count = 0;
        std::list<topo_geometry::Halfedge>::iterator pathEdgeItrforDist = VoriGraphHalfEdgeCut_first.pathEdges.begin();
        double obstacleMinimumtemp = pathEdgeItrforDist->dist();
        for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_first.pathEdges.end(); pathEdgeItrforDist++) {
            obstacleAveragetemp += pathEdgeItrforDist->dist();
            if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                obstacleMinimumtemp = pathEdgeItrforDist->dist();
            }
            count++;
        }
        VoriGraphHalfEdgeCut_first.obstacleAverage = obstacleAveragetemp / count;
        VoriGraphHalfEdgeCut_first.obstacleMinimum = obstacleMinimumtemp;

        pathEdgeItrforDist = VoriGraphHalfEdgeCut_second.pathEdges.begin();
        obstacleMinimumtemp = pathEdgeItrforDist->dist();
        obstacleAveragetemp = 0.;
        count = 0;
        for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_second.pathEdges.end(); pathEdgeItrforDist++) {
            obstacleAveragetemp += pathEdgeItrforDist->dist();
            if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                obstacleMinimumtemp = pathEdgeItrforDist->dist();
            }
            count++;
        }
        VoriGraphHalfEdgeCut_second.obstacleAverage = obstacleAveragetemp / count;
        VoriGraphHalfEdgeCut_second.obstacleMinimum = obstacleMinimumtemp;

        VoriGraphHalfEdgeCut_first.groupId = groupId;
        VoriGraphHalfEdgeCut_second.groupId = groupId;


        VoriGraphHalfEdgeCut_first.source = source;
        VoriGraphHalfEdgeCut_second.target = target;

        if (!source) {
            VoriGraphHalfEdgeCut_first.topo_ray = VoriGraphHalfEdgeCut_first.pathEdges.front();
        }
        if (!target) {
            VoriGraphHalfEdgeCut_second.topo_ray = VoriGraphHalfEdgeCut_second.pathEdges.back();
        }

        VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_first );
        VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_second );


        return VoriGraphHalfEdgeCutted;

    } else {
        //cut at source or target
        VoriGraphHalfEdgeCutted.push_back( *this );
        return VoriGraphHalfEdgeCutted;
    }
}

void checkConnectedEdgesForError(VoriGraph &voriGraph) {
    cout << "check connected edges for errors:" << endl;
    for (map<topo_geometry::point, VoriGraphVertex>::iterator itrVertices = voriGraph.vertices.begin();
         itrVertices != voriGraph.vertices.end(); ++itrVertices) {
        cout << "checking vertex " << &itrVertices << " groupId: " << itrVertices->second.groupId;
        cout << "  conn edges size: " << itrVertices->second.edgesConnected.size() << endl;
        for (list<VoriGraphHalfEdge *>::iterator itrEdges = itrVertices->second.edgesConnected.begin();
             itrEdges != itrVertices->second.edgesConnected.end(); ++itrEdges) {
            cout << "    edge: " << *itrEdges << " groupId: " << (*itrEdges)->groupId;
            bool isInE = isInEdges( *itrEdges, voriGraph );
            cout << " isInEdges: " << isInE;
            if (!isInE) {
                cout << endl;
                static unsigned int county = 0;
                county++;
                if (county > 5) assert( 0 );
            }
            cout << " source: " << (*itrEdges)->source;
            if ((*itrEdges)->source) {
                bool isIn = isInVertices((*itrEdges)->source, voriGraph );
                cout << " isInVertices: " << isIn;
                cout << " goupId: " << (*itrEdges)->source->groupId;
            }
            cout << " target: " << (*itrEdges)->target;
            if ((*itrEdges)->target) {
                bool isIn = isInVertices((*itrEdges)->target, voriGraph );
                cout << " isInVertices: " << isIn;
                cout << " goupId: " << (*itrEdges)->target->groupId;
                if (!isIn) {
                    cout << endl;
//             assert(0);
                } else {
                    // search for the target in vertices
                    cout << " edgesConnected in target " << (*itrEdges)->target->edgesConnected.size();
                }
            }
            cout << endl;

        }
    }
}

std::list<VoriGraphHalfEdge> VoriGraphHalfEdge::cutVoriGraphHalfEdge_Polygon(
        double cutlength,
        VoriGraphVertex &pPoint,
        std::list<VoriGraphPolygon> &cuttedPolygons_list) {
    std::list<VoriGraphHalfEdge> VoriGraphHalfEdgeCutted;
    if ((cutlength - EPSINON > distance) || (cutlength + EPSINON < 0)) {
        //0. can't cut (size of the returned list is 0)
        return VoriGraphHalfEdgeCutted;
    }
    if ((cutlength - EPSINON > 0) && (cutlength + EPSINON < distance)) {

        double currDistance = 0.;   //目前遍历过的小短边的长度和
        double cutDistancefromsource = 0.;//要剪的长度（与source距离）

        if (pPoint == *source) {
            cutDistancefromsource = cutlength;
        } else {
            if (pPoint == *target) {
                cutDistancefromsource = distance - cutlength;
            } else {
                //cut from neither source nor target...error(size of the returned list is 0)
                return VoriGraphHalfEdgeCutted;
            }
        }

        std::list<topo_geometry::Halfedge>::iterator pathEdgeItr = pathEdges.begin();
        topo_geometry::point cutPoint = pathEdges.begin()->s();
        std::list<topo_geometry::Halfedge>::iterator cutEdge = pathEdges.begin();
        cutEdge--;
        double minCutError = cutDistancefromsource;
        cutlength = 0;
        for (; pathEdgeItr != pathEdges.end(); pathEdgeItr++) {//遍历每一段看切割点是否在其上
            double d = pathEdgeItr->length();
            currDistance += d;
            if (fabs( cutDistancefromsource - currDistance ) < minCutError) {
                cutPoint = pathEdgeItr->t();
                minCutError = cutDistancefromsource - currDistance;
                cutEdge = pathEdgeItr;    //到此edge为第一段，后面为另一段
                cutlength = currDistance;
            }
        }

//        if(cutPoint==pathEdges.begin()->s()||cutPoint==pathEdges.rbegin()->t()){
        if (topo_geometry::operator==( pathEdges.begin()->s(), cutPoint ) ||
            topo_geometry::operator==( pathEdges.rbegin()->t(), cutPoint )) {
            VoriGraphHalfEdgeCutted.push_back( *this );
            return VoriGraphHalfEdgeCutted;
        }


        VoriGraphHalfEdge VoriGraphHalfEdgeCut_first;
        VoriGraphHalfEdge VoriGraphHalfEdgeCut_second;
        //cutEdge： 到此edge为第一段，后面为另一段
        //cutSite： 剪切的path点在polygonpoints里的位置
        //cutP： 剪切的site点在polygonpoints里的位置
        VoriGraphHalfEdgeCut_first.pathEdges.insert( VoriGraphHalfEdgeCut_first.pathEdges.begin(),
                                                     pathEdges.begin(), ++cutEdge );
        VoriGraphHalfEdgeCut_second.pathEdges.insert( VoriGraphHalfEdgeCut_second.pathEdges.begin(),
                                                      cutEdge, pathEdges.end());

        if (pathFace) {
            std::list<topo_geometry::point>::iterator pItr = pathFace->polygonpoints.begin();
            std::list<topo_geometry::point>::iterator cutP = pathFace->polygonpoints.begin();
            std::list<topo_geometry::point>::iterator cutSite = pathFace->polygonpoints.end();
            cutSite--;
            double minPError = 10000, minsiteError = 10000;
            bool isSite = 0;
            std::list<topo_geometry::point>::iterator targetItr;
            for (; pItr != pathFace->polygonpoints.end(); pItr++) {//遍历每一段看切割点是否在其上
                double tempDist = dist_gp( *pItr, cutPoint );
                if (isSite) {
                    if (tempDist < minsiteError) {
                        minsiteError = tempDist;
                        cutSite = pItr;   //剪切的site点在polygonpoints里的位置
                    }
                } else {
                    if (tempDist < minPError) {
                        minPError = tempDist;
                        cutP = pItr;  //剪切的path点在polygonpoints里的位置
                    }
                    if (round( pItr->x()) == round( target->point.x()) &&
                        round( pItr->y()) == round( target->point.y())) {
                        isSite = 1;
                        targetItr = pItr;
                    }
                }
            }


            VoriGraphPolygon newPolygon_first, newPolygon_second;
            newPolygon_first.polygonpoints.insert(
                    newPolygon_first.polygonpoints.begin(),
                    pathFace->polygonpoints.begin(), ++cutP );
            cutP--;
            newPolygon_first.polygonpoints.insert(
                    newPolygon_first.polygonpoints.end(),
                    cutSite, pathFace->polygonpoints.end());


            newPolygon_second.polygonpoints.insert(
                    newPolygon_second.polygonpoints.begin(),
                    cutP, ++cutSite );
            cutSite--;


            newPolygon_first.sites.insert( newPolygon_first.sites.begin(),
                                           cutSite, pathFace->polygonpoints.end());
            newPolygon_first.sites.reverse();
            newPolygon_second.sites.insert( newPolygon_second.sites.begin(),
                                            ++targetItr, ++cutSite );
            cutSite--;
            targetItr--;
            newPolygon_second.sites.reverse();
            cuttedPolygons_list.push_back( newPolygon_first );
            cuttedPolygons_list.push_back( newPolygon_second );


            //if cutP is source or target, don't need to cut
            if (cutP == pathFace->polygonpoints.begin() || cutP == targetItr) {
//                cout<<"if cutP is source or target, don't need to cut!"<<endl;
                VoriGraphHalfEdgeCutted.push_back( *this );
                cout << "cutlength= " << cutlength << "; "
                     << "distance= " << distance << "; "
                             "pathEdges.begin()->length()=" << pathEdges.begin()->length()
                     << "; "
                             "pathEdges.rbegin()->length()=" << pathEdges.rbegin()->length()
                     << endl;
                cout << "1520 pHalfEdge (" << roomId << ") : "
                     << source->point.x() << ", " << source->point.y()
                     << " --> " << target->point.x() << ", " << target->point.y() << endl;
                return VoriGraphHalfEdgeCutted;
            }
        }


        VoriGraphHalfEdgeCut_first.distance = cutlength;
        VoriGraphHalfEdgeCut_second.distance = distance - cutlength;

        double obstacleAveragetemp = 0.;
        int count = 0;
        std::list<topo_geometry::Halfedge>::iterator pathEdgeItrforDist = VoriGraphHalfEdgeCut_first.pathEdges.begin();
        double obstacleMinimumtemp = pathEdgeItrforDist->dist();
        for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_first.pathEdges.end(); pathEdgeItrforDist++) {
            obstacleAveragetemp += pathEdgeItrforDist->dist();
            if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                obstacleMinimumtemp = pathEdgeItrforDist->dist();
            }
            count++;
        }
        VoriGraphHalfEdgeCut_first.obstacleAverage = obstacleAveragetemp / count;
        VoriGraphHalfEdgeCut_first.obstacleMinimum = obstacleMinimumtemp;

        pathEdgeItrforDist = VoriGraphHalfEdgeCut_second.pathEdges.begin();
        obstacleMinimumtemp = pathEdgeItrforDist->dist();
        obstacleAveragetemp = 0.;
        count = 0;
        for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_second.pathEdges.end(); pathEdgeItrforDist++) {
            obstacleAveragetemp += pathEdgeItrforDist->dist();
            if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                obstacleMinimumtemp = pathEdgeItrforDist->dist();
            }
            count++;
        }
        VoriGraphHalfEdgeCut_second.obstacleAverage = obstacleAveragetemp / count;
        VoriGraphHalfEdgeCut_second.obstacleMinimum = obstacleMinimumtemp;

        VoriGraphHalfEdgeCut_first.groupId = groupId;
        VoriGraphHalfEdgeCut_second.groupId = groupId;


        VoriGraphHalfEdgeCut_first.source = source;
        VoriGraphHalfEdgeCut_second.target = target;

        if (!source) {
//        if (VoriGraphHalfEdgeCut_first.isRay()) {
            VoriGraphHalfEdgeCut_first.topo_ray = VoriGraphHalfEdgeCut_first.pathEdges.front();
        }
        if (!target) {
//        if (VoriGraphHalfEdgeCut_second.isRay()) {
            VoriGraphHalfEdgeCut_second.topo_ray = VoriGraphHalfEdgeCut_second.pathEdges.back();
        }

        VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_first );
        VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_second );

        return VoriGraphHalfEdgeCutted;

    } else {
        //cut at source or target
        VoriGraphHalfEdgeCutted.push_back( *this );
        cout << "1583 cutlength= " << cutlength << "; "
             << "distance= " << distance << "; "
                     "pathEdges.begin()->length()=" << pathEdges.begin()->length() << "; "
                     "pathEdges.rbegin()->length()="
             << pathEdges.rbegin()->length()
             << endl;
        cout << "pHalfEdge (" << roomId << ") : "
             << source->point.x() << ", " << source->point.y()
             << " --> " << target->point.x() << ", " << target->point.y() << endl;
        return VoriGraphHalfEdgeCutted;
    }
}

//add from yutianyan
std::list<VoriGraphHalfEdge> VoriGraphHalfEdge::cutVoriGraphHalfEdge(double cutlength, VoriGraphVertex &pPoint) {

    //list to save the cut vorigraph halfedge
    std::list<VoriGraphHalfEdge> VoriGraphHalfEdgeCutted;

    if ((cutlength - EPSINON > distance) || (cutlength + EPSINON < 0)) {
        //0. can't cut (size of the returned list is 0)
        return VoriGraphHalfEdgeCutted;
    } else {
        if ((cutlength - EPSINON > 0) && (cutlength + EPSINON < distance)) {
            //1. normal cutting start
            double currDistance = 0.;
            double cutDistancefromsource = 0.;

            if (pPoint == *source) {
                cutDistancefromsource = cutlength;
            } else {
                if (pPoint == *target) {
                    cutDistancefromsource = distance - cutlength;
                } else {
                    //cut from neither source nor target...error(size of the returned list is 0)
                    return VoriGraphHalfEdgeCutted;
                }
            }

            std::list<topo_geometry::Halfedge>::iterator pathEdgeItr = pathEdges.begin();
            for (; pathEdgeItr != pathEdges.end(); pathEdgeItr++) {//遍历每一段看切割点是否在其上
                double d = pathEdgeItr->length();
                //if( d + currDistance - cutDistancefromsource >= 0 )
                if (d + currDistance - cutDistancefromsource + EPSINON > 0) {
                    double para = cutDistancefromsource - currDistance; //在段上要切的距离
                    std::list<topo_geometry::Halfedge> cutresult = pathEdgeItr->cutHalfedge( pathEdgeItr->s(), para );

                    VoriGraphHalfEdge VoriGraphHalfEdgeCut_first;
                    VoriGraphHalfEdge VoriGraphHalfEdgeCut_second;

                    //insert new halfedges to first and second, keep sequence
                    //do not include pathEdgeItr

                    if (cutresult.size() == 1) {//没切，还是原来那个段
                        //not include pathEdgeItr
                        VoriGraphHalfEdgeCut_first.pathEdges.insert( VoriGraphHalfEdgeCut_first.pathEdges.begin(),
                                                                     pathEdges.begin(), pathEdgeItr );
                        //include pathEdgeItr
                        VoriGraphHalfEdgeCut_second.pathEdges.insert( VoriGraphHalfEdgeCut_second.pathEdges.begin(),
                                                                      pathEdgeItr, pathEdges.end());

                        if (fabs( para ) <= EPSINON) {
                            //do nothing
                        } else {
                            if (fabs( para - pathEdgeItr->length()) <= EPSINON) {
                                //add halfedge to first part
                                VoriGraphHalfEdgeCut_first.pathEdges.push_back( cutresult.front());
                                //remove halfedge from second part
                                VoriGraphHalfEdgeCut_second.pathEdges.pop_front();
                            } else {
                                cerr << "We should not reach here in single cutting" << endl;
                                exit( 1 );
                            }
                        }
                    } else {
                        //normal cut
                        if (cutresult.size() == 2) {//一个段被切成了两段
                            VoriGraphHalfEdgeCut_first.pathEdges.insert( VoriGraphHalfEdgeCut_first.pathEdges.begin(),
                                                                         pathEdges.begin(), pathEdgeItr );
                            //add first part
                            VoriGraphHalfEdgeCut_first.pathEdges.push_back( cutresult.front());

                            //include pathEdgeItr
                            VoriGraphHalfEdgeCut_second.pathEdges.insert( VoriGraphHalfEdgeCut_second.pathEdges.begin(),
                                                                          pathEdgeItr, pathEdges.end());
                            //remove pathEdgeItr
                            VoriGraphHalfEdgeCut_second.pathEdges.pop_front();
                            //add second part
                            VoriGraphHalfEdgeCut_second.pathEdges.push_front( cutresult.back());
                        } else {
                            cerr << "We should not reach here when cutting" << endl;
                            exit( 1 );
                        }
                    }

                    //distance along edge
                    VoriGraphHalfEdgeCut_first.distance = cutDistancefromsource;

                    VoriGraphHalfEdgeCut_second.distance = distance - cutDistancefromsource;

                    //distance to obstacle
                    double obstacleAveragetemp = 0.;
                    int count = 0;
                    std::list<topo_geometry::Halfedge>::iterator pathEdgeItrforDist = VoriGraphHalfEdgeCut_first.pathEdges.begin();
                    double obstacleMinimumtemp = pathEdgeItrforDist->dist();
                    for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_first.pathEdges.end(); pathEdgeItrforDist++) {
                        obstacleAveragetemp += pathEdgeItrforDist->dist();
                        if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                            obstacleMinimumtemp = pathEdgeItrforDist->dist();
                        }
                        count++;
                    }
                    VoriGraphHalfEdgeCut_first.obstacleAverage = obstacleAveragetemp / count;
                    VoriGraphHalfEdgeCut_first.obstacleMinimum = obstacleMinimumtemp;
                    //std::cout<<VoriGraphHalfEdgeCut_first.obstacleAverage<<endl;

                    pathEdgeItrforDist = VoriGraphHalfEdgeCut_second.pathEdges.begin();
                    obstacleMinimumtemp = pathEdgeItrforDist->dist();
                    obstacleAveragetemp = 0.;
                    count = 0;
                    for (; pathEdgeItrforDist != VoriGraphHalfEdgeCut_second.pathEdges.end(); pathEdgeItrforDist++) {
                        obstacleAveragetemp += pathEdgeItrforDist->dist();
                        if (pathEdgeItrforDist->dist() < obstacleMinimumtemp) {
                            obstacleMinimumtemp = pathEdgeItrforDist->dist();
                        }
                        count++;
                    }
                    VoriGraphHalfEdgeCut_second.obstacleAverage = obstacleAveragetemp / count;
                    VoriGraphHalfEdgeCut_second.obstacleMinimum = obstacleMinimumtemp;

                    //groupid
                    VoriGraphHalfEdgeCut_first.groupId = groupId;
                    VoriGraphHalfEdgeCut_second.groupId = groupId;


                    //
                    if (VoriGraphHalfEdgeCut_first.isRay()) {
                        VoriGraphHalfEdgeCut_first.topo_ray = VoriGraphHalfEdgeCut_first.pathEdges.front();
                    }

                    if (VoriGraphHalfEdgeCut_second.isRay()) {
                        VoriGraphHalfEdgeCut_second.topo_ray = VoriGraphHalfEdgeCut_second.pathEdges.back();
                    }

                    //change source
                    VoriGraphHalfEdgeCut_first.source = source;
                    //change target
                    VoriGraphHalfEdgeCut_second.target = target;


                    //add to the list
                    VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_first );
                    VoriGraphHalfEdgeCutted.push_back( VoriGraphHalfEdgeCut_second );

                    return VoriGraphHalfEdgeCutted;
                }
                currDistance += d;
            }
        } else {
            //cut at source or target
            VoriGraphHalfEdgeCutted.push_back( *this );

            return VoriGraphHalfEdgeCutted;
        }
    }
}


bool VoriGraph::cutHalfEdgeAtDistance_Polygonbk(double cutlength, //要切割的长度（与source距离）
                                              VoriGraphHalfEdge *pHalfEdge, //要切割的边
                                              VoriGraphVertex &pPoint,  //要切割的边的source
                                              unsigned int roomId) {

    if ((cutlength - EPSINON > pHalfEdge->distance) || (cutlength + EPSINON < 0)) {
        return false;
    }

    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = halfEdges.begin();
    std::list<VoriGraphHalfEdge> cutresult;
    std::list<VoriGraphHalfEdge> cutresultTwin;
    std::list<VoriGraphPolygon> cuttedPolygons_list;
    std::list<VoriGraphPolygon> cuttedPolygons_twin_list;

    if(pHalfEdge->deadEnd || pHalfEdge->isRay())return true;
    //remove pHalfEdge and its twin
//    cout<<"size of halfEdges: "<<halfEdges.size()<<endl;
    int cnt = halfEdges.size();
    bool pHF = false, pHFT = false;
    if (pHalfEdge->pathFace) { pHF = true; }
    if (pHalfEdge->twin) {
        if (pHalfEdge->twin->pathFace) { pHFT = true; }
    }
    while (cnt--) {
//        cout<<"cnt= "<<cnt<<endl;
        if (&*pathEdgeItr == pHalfEdge || &*pathEdgeItr == pHalfEdge->twin) {
//        if (pathEdgeItr->source==pHalfEdge->source && pathEdgeItr->target==pHalfEdge->target
//            || pathEdgeItr->source==pHalfEdge->target && pathEdgeItr->target==pHalfEdge->source) {
            if (&*pathEdgeItr == pHalfEdge) {
//                std::cout<<" to cut ";coutpoint(pathEdgeItr->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->target->point);
//                std::cout<<" twin: ";coutpoint(pathEdgeItr->twin->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->twin->target->point);
//            if (pathEdgeItr->source==pHalfEdge->source && pathEdgeItr->target==pHalfEdge->target) {
                cutresult = pathEdgeItr->cutVoriGraphHalfEdge_Polygon_accruay( cutlength, pPoint,
                                                                               cuttedPolygons_list );
                ++pathEdgeItr;
            }
            if (&*pathEdgeItr == pHalfEdge->twin) {
//                std::cout<<" to cut ";coutpoint(pathEdgeItr->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->target->point);
//                std::cout<<" twin: ";coutpoint(pathEdgeItr->twin->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->twin->target->point);
//            if (pathEdgeItr->source==pHalfEdge->target && pathEdgeItr->target==pHalfEdge->source) {
                cutresultTwin = pathEdgeItr->cutVoriGraphHalfEdge_Polygon_accruay( cutlength, pPoint,
                                                                                   cuttedPolygons_twin_list );
                ++pathEdgeItr;
            }
//                pathEdgeItr = removeHalfEdge_jiawei( pathEdgeItr);
            //好气哦！这里居然从halfEdges删除了切割在末端的halfedge！尤其是deadend!
//                pathEdgeItr = removeHalfEdge_roomPolygon( pathEdgeItr, false ); //为什么不删除末端点呢？？

//            if (cutresult.size() == 2)
//                || cutresultTwin.size() == 2
//                    ) {
//               pathEdgeItr = removeHalfEdge_roomPolygon( pathEdgeItr, false );
//            } else
//            if (cutresult.size() == 1 || cutresultTwin.size() == 1) { ++pathEdgeItr; }
//            if (cutresult.size() != 2 && cutresultTwin.size() != 2) { ++pathEdgeItr; }
//            } else {
//                break;
//            }
//            pathEdgeItr = removeHalfEdge_roomPolygon( pathEdgeItr, false );
            std::cout<<" size: "<<cutresult.size()<<std::endl;
        } else {
            ++pathEdgeItr;
        }
    }
    if (cutresult.size() == 2)  removeHalfEdge_roomPolygon( pHalfEdge, false );
    if (cutresultTwin.size() == 2)  removeHalfEdge_roomPolygon( pHalfEdge->twin, false );

    //fail to cut
    if (cutresult.size() == 0 || cutresultTwin.size() == 0) {
        return false;
    } else {
//        if (cutresult.size() >= 1)
//        for(std::list<VoriGraphHalfEdge>::iterator cutitr=cutresult.begin();cutitr!=cutresult.end();cutitr++){
//            coutpoint(cutitr->source->point);std::cout<<" - ";coutpoint(cutitr->target->point);std::cout<<endl;
//        }
//        if (cutresultTwin.size() >= 1)
//        for(std::list<VoriGraphHalfEdge>::iterator cutitr=cutresultTwin.begin();cutitr!=cutresultTwin.end();cutitr++){
//            coutpoint(cutitr->source->point);std::cout<<" - ";coutpoint(cutitr->target->point);std::cout<<endl;
//        }
        if (cutresult.size() == 1 ||
             cutresultTwin.size() == 1) {//cut at source or target of VoriHalfEdge

            if (topo_geometry::operator==( pHalfEdge->target->point, pPoint.point )) {

                cutlength = pHalfEdge->distance - cutlength;
            }
            if (fabs( cutlength ) <= pHalfEdge->pathEdges.begin()->length() + EPSINON) {
            if(fabs( cutlength )<fabs( pHalfEdge->distance - cutlength )){
//                if (abs( cutlength ) <= pHalfEdge->pathEdges.begin()->length() + EPSINON) {
//                cout << "cut at source " << endl;
//                pPoint.markRoomVertex();
//                pPoint.setRoomId( roomId );
                    pHalfEdge->source->markRoomVertex();
                    pHalfEdge->source->setRoomId( roomId );
                    return true;
                } else {    //we reach here when "alphaShapeRemovalSquaredSize" = 822
                    cerr << "We should not reach here(VoriGraph.cpp)" << endl;
                    exit( 1 );
                }
            } else {
                if (fabs( pHalfEdge->distance - cutlength ) <= pHalfEdge->pathEdges.rbegin()->length() + EPSINON) {
//                    cout << "cut at target " << endl;
                    pHalfEdge->target->markRoomVertex();
                    pHalfEdge->target->setRoomId( roomId );
//                    if (topo_geometry::operator==( pHalfEdge->source->point, pPoint.point )) {
//                        pHalfEdge->target->markRoomVertex();
//                        pHalfEdge->target->setRoomId( roomId );
//                    } else {
//                        pHalfEdge->source->markRoomVertex();
//                        pHalfEdge->source->setRoomId( roomId );
//                    }
                    return true;
                } else {    //we reach here when "alphaShapeRemovalSquaredSize" = 822
                    cerr << "We should not reach here in vorigraphhalfedge cutting 1839" << endl;
                    exit( 1 );
                }
            }
        } else {
            if (cutresult.size() == 2 && cutresultTwin.size() == 2) {
                //normal cut
                if (pHF) {
//                    VoriGraphPolygon *polygonPtr = &*pathFaces.rbegin();
//                    assert( pathFaces.rbegin() != 0 );
//                    edgePtr->pathFace = polygonPtr;
                    pathFaces.push_back( cuttedPolygons_list.front());
                    cutresult.front().pathFace = &*pathFaces.rbegin();
                    pathFaces.push_back( cuttedPolygons_list.back());
                    cutresult.back().pathFace = &*pathFaces.rbegin();
                } else { cout << "not (pathEdgeItr->pathFace)!" << endl; }
                if (pHFT) {
                    pathFaces.push_back( cuttedPolygons_twin_list.front());
                    cutresultTwin.front().pathFace = &*pathFaces.rbegin();
                    pathFaces.push_back( cuttedPolygons_twin_list.back());
                    cutresultTwin.back().pathFace = &*pathFaces.rbegin();
                } else { cout << "not (pathEdgeItr->twin->pathFace)!" << endl; }
                halfEdges.push_back( cutresult.front());//first half
                halfEdges.push_back( cutresult.back());//second half

                halfEdges.push_back( cutresultTwin.front());//second half's twin
                halfEdges.push_back( cutresultTwin.back());//first half's twin


                std::list<VoriGraphHalfEdge>::iterator edgeItr = --halfEdges.end();

                VoriGraphHalfEdge *firstHalfTwin = &(*edgeItr);
                VoriGraphHalfEdge *secondHalfTwin = &*(--edgeItr);
                VoriGraphHalfEdge *secondHalf = &*(--edgeItr);
                VoriGraphHalfEdge *firstHalf = &*(--edgeItr);
                if (pHF) {
                    cutresult.front().pathFace->belongpaths.push_back( firstHalf );
                    cutresult.back().pathFace->belongpaths.push_back( secondHalf );
                }
                if (pHFT) {
                    cutresultTwin.front().pathFace->belongpaths.push_back( secondHalfTwin );
                    cutresultTwin.back().pathFace->belongpaths.push_back( firstHalfTwin );
                }

                //start vertex
                topo_geometry::point start = firstHalf->source->point;
                //create middle vertex
                topo_geometry::point middle = cutresult.front().pathEdges.back().t();
                //end vertex
                topo_geometry::point end = secondHalf->target->point;

                VoriGraphVertex cutVertex;
                cutVertex.point = middle;
                //last halfedge in first vorigraphhalfedge cutresult
                cutVertex.obstacleDist = cutresult.front().pathEdges.back().dist();
                cutVertex.groupId = cutresult.front().groupId;

                vertices[middle] = cutVertex;

                //source and target (8 halfedges)
                //start
                firstHalf->source = &vertices[start];
                firstHalfTwin->target = firstHalf->source;
                //middle
                firstHalf->target = &vertices[middle];
                secondHalf->source = &vertices[middle];
                firstHalfTwin->source = firstHalf->target;
                secondHalfTwin->target = secondHalf->source;
                //end
                secondHalf->target = &vertices[end];
                secondHalfTwin->source = secondHalf->target;

                //edgeConnected list
                //start (2 additional)
                vertices[start].edgesConnected.push_back( firstHalf );
                vertices[start].edgesConnected.push_back( firstHalfTwin );
                //vertices[start].markTwins();

                //middle(4 additional)
                vertices[middle].edgesConnected.push_back( firstHalf );
                vertices[middle].edgesConnected.push_back( firstHalfTwin );
                vertices[middle].edgesConnected.push_back( secondHalf );
                vertices[middle].edgesConnected.push_back( secondHalfTwin );

                //end(2 additional)
                vertices[end].edgesConnected.push_back( secondHalf );
                vertices[end].edgesConnected.push_back( secondHalfTwin );


                vertices[start].markTwins();
                vertices[middle].markTwins();
                vertices[end].markTwins();
                if (!firstHalf->pathFace || firstHalf->pathFace->polygonpoints.empty()
                    || !firstHalfTwin->pathFace || firstHalfTwin->pathFace->polygonpoints.empty()) {
                    cout << "firstHalf and its twin has no pathface!(VoriGraph.cpp)" << endl;
                }
                if (!secondHalf->pathFace || secondHalf->pathFace->polygonpoints.empty()
                    || !secondHalfTwin->pathFace || secondHalfTwin->pathFace->polygonpoints.empty()) {
                    cout << "secondHalf and its twin has no pathface!(VoriGraph.cpp)" << endl;
                }

                //mark roomvertex
                vertices[middle].markRoomVertex();
                //set roomId
                vertices[middle].setRoomId( roomId );
                //TODO:怎么没有设置middle为borderVertex, RoomVertex是边界点的意思吗？

                markDeadEnds();

                return true;
            } else {
                cerr << "We should not reach here! in vorigraphhalfedge cutting 1939" << endl;
                exit( 1 );
            }
        }
    }
}

bool VoriGraph::cutHalfEdgeAtDistance_Polygon(double cutlength, //要切割的长度（与source距离）
                                              VoriGraphHalfEdge *pHalfEdge, //要切割的边
                                              VoriGraphVertex &pPoint,  //要切割的边的source
                                              unsigned int roomId) {

    if ((cutlength - EPSINON > pHalfEdge->distance) || (cutlength + EPSINON < 0)) {
        return false;
    }

    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = halfEdges.begin();
    std::list<VoriGraphHalfEdge> cutresult;
    std::list<VoriGraphHalfEdge> cutresultTwin;
    std::list<VoriGraphPolygon> cuttedPolygons_list;
    std::list<VoriGraphPolygon> cuttedPolygons_twin_list;

    //remove pHalfEdge and its twin
//    cout<<"size of halfEdges: "<<halfEdges.size()<<endl;
    int cnt = halfEdges.size();
    bool pHF = false, pHFT = false;
    if (pHalfEdge->pathFace) { pHF = true; }
    if (pHalfEdge->twin) {
        if (pHalfEdge->twin->pathFace) { pHFT = true; }
    }
    if(!pHF || !pHFT){
        coutpoint(pHalfEdge->source->point);coutpoint(pHalfEdge->target->point);cout<<"has no twin or face! (from VoriGraph::cutHalfEdgeAtDistance_Polygon)"<<endl;
        return false;
    }
    for(;pathEdgeItr!=halfEdges.end();pathEdgeItr++) {
            if (&*pathEdgeItr == pHalfEdge) {
//                std::cout<<" to cut ";coutpoint(pathEdgeItr->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->target->point);
//                std::cout<<" twin: ";coutpoint(pathEdgeItr->twin->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->twin->target->point);
//                std::cout<<"\n polygon: ";
//                coutpolygon(pathEdgeItr->pathFace->polygonpoints);
                cutresult = pathEdgeItr->cutVoriGraphHalfEdge_Polygon_accruay( cutlength, pPoint,
                                                                               cuttedPolygons_list );
//                std::cout<<" size: "<<cutresult.size()<<"; to polygons "<<std::endl;
//                coutpolygon(cuttedPolygons_list.front().polygonpoints);
//                std::cout<<" and ";
//                coutpolygon(cuttedPolygons_list.back().polygonpoints);
//                std::cout<<std::endl;
            }
            if (&*pathEdgeItr == pHalfEdge->twin) {
//                std::cout<<" to cut ";coutpoint(pathEdgeItr->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->target->point);
//                std::cout<<" twin: ";coutpoint(pathEdgeItr->twin->source->point);std::cout<<" - ";coutpoint(pathEdgeItr->twin->target->point);
//                std::cout<<"\n polygon: ";
//                coutpolygon(pathEdgeItr->pathFace->polygonpoints);
                cutresultTwin = pathEdgeItr->cutVoriGraphHalfEdge_Polygon_accruay( cutlength, pPoint,
                                                                                   cuttedPolygons_twin_list );
//                std::cout<<" size: "<<cutresultTwin.size()<<"; to polygons "<<std::endl;
//                coutpolygon(cuttedPolygons_twin_list.front().polygonpoints);
//                std::cout<<" and ";
//                coutpolygon(cuttedPolygons_twin_list.back().polygonpoints);
//                std::cout<<std::endl;
            }

    }
    //fail to cut
    if (cutresult.size() == 0 || cutresultTwin.size() == 0) {
        return false;
    } else {
        if (cutresult.size() == 2)  removeHalfEdge_roomPolygon( pHalfEdge, false );
        if (cutresultTwin.size() == 2)  removeHalfEdge_roomPolygon( pHalfEdge->twin, false );

        if (cutresult.size() == 1 ||
            cutresultTwin.size() == 1) {//cut at source or target of VoriHalfEdge

            if (topo_geometry::operator==( pHalfEdge->target->point, pPoint.point )) {

                cutlength = pHalfEdge->distance - cutlength;
            }
            if (fabs( cutlength ) <= pHalfEdge->pathEdges.begin()->length() + EPSINON) {
                if(fabs( cutlength )<fabs( pHalfEdge->distance - cutlength )){
//                if (abs( cutlength ) <= pHalfEdge->pathEdges.begin()->length() + EPSINON) {
//                cout << "cut at source " << endl;
//                pPoint.markRoomVertex();
//                pPoint.setRoomId( roomId );
                    pHalfEdge->source->markRoomVertex();
                    pHalfEdge->source->setRoomId( roomId );
                    return true;
                } else {    //we reach here when "alphaShapeRemovalSquaredSize" = 822
                    cerr << "We should not reach here(VoriGraph.cpp)" << endl;
                    exit( 1 );
                }
            } else {
                if (fabs( pHalfEdge->distance - cutlength ) <= pHalfEdge->pathEdges.rbegin()->length() + EPSINON) {
//                    cout << "cut at target " << endl;
                    pHalfEdge->target->markRoomVertex();
                    pHalfEdge->target->setRoomId( roomId );
//                    if (topo_geometry::operator==( pHalfEdge->source->point, pPoint.point )) {
//                        pHalfEdge->target->markRoomVertex();
//                        pHalfEdge->target->setRoomId( roomId );
//                    } else {
//                        pHalfEdge->source->markRoomVertex();
//                        pHalfEdge->source->setRoomId( roomId );
//                    }
                    return true;
                } else {    //we reach here when "alphaShapeRemovalSquaredSize" = 822
                    cerr << "We should not reach here in vorigraphhalfedge cutting 1839" << endl;
                    exit( 1 );
                }
            }
        } else {
            if (cutresult.size() == 2 && cutresultTwin.size() == 2) {
                //normal cut
                if (pHF) {
//                    VoriGraphPolygon *polygonPtr = &*pathFaces.rbegin();
//                    assert( pathFaces.rbegin() != 0 );
//                    edgePtr->pathFace = polygonPtr;
                    pathFaces.push_back( cuttedPolygons_list.front());
                    cutresult.front().pathFace = &*pathFaces.rbegin();
                    pathFaces.push_back( cuttedPolygons_list.back());
                    cutresult.back().pathFace = &*pathFaces.rbegin();
                } else { cout << "not (pathEdgeItr->pathFace)!" << endl; }
                if (pHFT) {
                    pathFaces.push_back( cuttedPolygons_twin_list.front());
                    cutresultTwin.front().pathFace = &*pathFaces.rbegin();
                    pathFaces.push_back( cuttedPolygons_twin_list.back());
                    cutresultTwin.back().pathFace = &*pathFaces.rbegin();
                } else { cout << "not (pathEdgeItr->twin->pathFace)!" << endl; }
                halfEdges.push_back( cutresult.front());//first half
                halfEdges.push_back( cutresult.back());//second half

                halfEdges.push_back( cutresultTwin.front());//second half's twin
                halfEdges.push_back( cutresultTwin.back());//first half's twin


                std::list<VoriGraphHalfEdge>::iterator edgeItr = --halfEdges.end();

                VoriGraphHalfEdge *firstHalfTwin = &(*edgeItr);
                VoriGraphHalfEdge *secondHalfTwin = &*(--edgeItr);
                VoriGraphHalfEdge *secondHalf = &*(--edgeItr);
                VoriGraphHalfEdge *firstHalf = &*(--edgeItr);
                if (pHF) {
                    cutresult.front().pathFace->belongpaths.push_back( firstHalf );
                    cutresult.back().pathFace->belongpaths.push_back( secondHalf );
                }
                if (pHFT) {
                    cutresultTwin.front().pathFace->belongpaths.push_back( secondHalfTwin );
                    cutresultTwin.back().pathFace->belongpaths.push_back( firstHalfTwin );
                }

                //start vertex
                topo_geometry::point start = firstHalf->source->point;
                //create middle vertex
                topo_geometry::point middle = cutresult.front().pathEdges.back().t();
                //end vertex
                topo_geometry::point end = secondHalf->target->point;

                VoriGraphVertex cutVertex;
                cutVertex.point = middle;
                //last halfedge in first vorigraphhalfedge cutresult
                cutVertex.obstacleDist = cutresult.front().pathEdges.back().dist();
                cutVertex.groupId = cutresult.front().groupId;

                vertices[middle] = cutVertex;

                //source and target (8 halfedges)
                //start
                firstHalf->source = &vertices[start];
                firstHalfTwin->target = firstHalf->source;
                //middle
                firstHalf->target = &vertices[middle];
                secondHalf->source = &vertices[middle];
                firstHalfTwin->source = firstHalf->target;
                secondHalfTwin->target = secondHalf->source;
                //end
                secondHalf->target = &vertices[end];
                secondHalfTwin->source = secondHalf->target;

                //edgeConnected list
                //start (2 additional)
                vertices[start].edgesConnected.push_back( firstHalf );
                vertices[start].edgesConnected.push_back( firstHalfTwin );
                //vertices[start].markTwins();

                //middle(4 additional)
                vertices[middle].edgesConnected.push_back( firstHalf );
                vertices[middle].edgesConnected.push_back( firstHalfTwin );
                vertices[middle].edgesConnected.push_back( secondHalf );
                vertices[middle].edgesConnected.push_back( secondHalfTwin );

                //end(2 additional)
                vertices[end].edgesConnected.push_back( secondHalf );
                vertices[end].edgesConnected.push_back( secondHalfTwin );


                vertices[start].markTwins();
                vertices[middle].markTwins();
                vertices[end].markTwins();
                if (!firstHalf->pathFace || firstHalf->pathFace->polygonpoints.empty()
                    || !firstHalfTwin->pathFace || firstHalfTwin->pathFace->polygonpoints.empty()) {
                    cout << "firstHalf and its twin has no pathface!(VoriGraph.cpp)" << endl;
                }
                if (!secondHalf->pathFace || secondHalf->pathFace->polygonpoints.empty()
                    || !secondHalfTwin->pathFace || secondHalfTwin->pathFace->polygonpoints.empty()) {
                    cout << "secondHalf and its twin has no pathface!(VoriGraph.cpp)" << endl;
                }
//                std::cout<<" become ";coutpoint(firstHalf->source->point);std::cout<<" - ";coutpoint(firstHalf->target->point);
//                std::cout<<" and ";coutpoint(secondHalf->source->point);std::cout<<" - ";coutpoint(secondHalf->target->point);
//                std::cout<<"\n twin is ";coutpoint(secondHalfTwin->source->point);std::cout<<" - ";coutpoint(secondHalfTwin->target->point);
//                std::cout<<" and ";coutpoint(firstHalfTwin->source->point);std::cout<<" - ";coutpoint(firstHalfTwin->target->point);std::cout<<std::endl;

                //mark roomvertex
                vertices[middle].markRoomVertex();
                //set roomId
                vertices[middle].setRoomId( roomId );
                //TODO:怎么没有设置middle为borderVertex, RoomVertex是边界点的意思吗？

                markDeadEnds();

                return true;
            } else {
                cerr << "We should not reach here! in vorigraphhalfedge cutting 1939" << endl;
                exit( 1 );
            }
        }
    }
}

VoriGraphHalfEdge *
pathToEdge(VoriGraph &voriGraph, double x, double y, double &Pmindist, topo_geometry::point &closestP) {
    list<VoriGraphHalfEdge>::iterator Hitr = voriGraph.halfEdges.begin();
    double Hmindist = 10000;
    Pmindist = 10000;
    VoriGraphHalfEdge *minH;
    for (; Hitr != voriGraph.halfEdges.end(); Hitr++) {
        if (Hitr->isRay())continue;
        double distH = dist( x, y, (*Hitr).source->point.x(), (*Hitr).source->point.y());
        double tempdist = dist( x, y, (*Hitr).target->point.x(), (*Hitr).target->point.y());
//        distH=distH>tempdist?tempdist:distH;
        if (distH + tempdist < Hmindist) {
            minH = &(*Hitr);
            Hmindist = distH + tempdist;
            if (distH > tempdist) {
                Pmindist = tempdist;
                topo_geometry::point pt((*Hitr).target->point.x(), (*Hitr).target->point.y());
                closestP = pt;
            }
        }
    }
    list<topo_geometry::Halfedge>::iterator pitr = minH->pathEdges.begin();
    for (; pitr != minH->pathEdges.end(); pitr++) {
        double distS = dist( x, y, pitr->s().x(), pitr->s().y()), distT = dist( x, y, pitr->t().x(), pitr->t().y());
//                distS=distS>distT?distT:distS;
        if (Pmindist > distS) {
            Pmindist = distS;
            closestP = pitr->s();
        }
    }
    return minH;
}

//add from yutianyan
bool VoriGraph::cutHalfEdgeAtDistance(double cutlength, //要切割的长度（与source距离）
                                      VoriGraphHalfEdge *pHalfEdge, //要切割的边
                                      VoriGraphVertex &pPoint,  //要切割的边的source
                                      unsigned int roomId) {

    if ((cutlength - EPSINON > pHalfEdge->distance) || (cutlength + EPSINON < 0)) {
        return false;
    }

    std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = halfEdges.begin();
    std::list<VoriGraphHalfEdge> cutresult;
    std::list<VoriGraphHalfEdge> cutresultTwin;

    //remove pHalfEdge and its twin
    while (true) {
        if (&*pathEdgeItr == pHalfEdge || &*pathEdgeItr == pHalfEdge->twin || (pathEdgeItr == halfEdges.end())) {
            if (&*pathEdgeItr == pHalfEdge || &*pathEdgeItr == pHalfEdge->twin) {
                if (&*pathEdgeItr == pHalfEdge) {
                    cutresult = pathEdgeItr->cutVoriGraphHalfEdge( cutlength, pPoint );
                }
                if (&*pathEdgeItr == pHalfEdge->twin) {
                    cutresultTwin = pathEdgeItr->cutVoriGraphHalfEdge( cutlength, pPoint );
                }
                pathEdgeItr = removeHalfEdge_tianyan( pathEdgeItr, false );
            } else {
                break;
            }
        } else {
            ++pathEdgeItr;
        }
    }

    //fail to cut
    if (cutresult.size() == 0 || cutresultTwin.size() == 0) {
        return false;
    } else {
        if (cutresult.size() == 1) {//cut at source or target of VoriHalfEdge
            if (fabs( cutlength ) <= EPSINON) {
                pPoint.markRoomVertex();
                pPoint.setRoomId( roomId );
                return true;
            } else {
                if (fabs( cutlength - pHalfEdge->distance ) <= EPSINON) {
                    if (topo_geometry::operator==( pHalfEdge->source->point, pPoint.point )) {
                        pHalfEdge->target->markRoomVertex();
                        pHalfEdge->target->setRoomId( roomId );
                    } else {
                        pHalfEdge->source->markRoomVertex();
                        pHalfEdge->source->setRoomId( roomId );
                    }
                    return true;
                } else {
                    cerr << "We should not reach here in vorigraphhalfedge cutting" << endl;
                    exit( 1 );
                }
            }
        } else {
            if (cutresult.size() == 2) {
                //normal cut
                halfEdges.push_back( cutresult.front());//first half
                halfEdges.push_back( cutresult.back());//second half

                halfEdges.push_back( cutresultTwin.front());//second half's twin
                halfEdges.push_back( cutresultTwin.back());//first half's twin

                std::list<VoriGraphHalfEdge>::iterator edgeItr = --halfEdges.end();

                VoriGraphHalfEdge *firstHalfTwin = &(*edgeItr);
                VoriGraphHalfEdge *secondHalfTwin = &*(--edgeItr);
                VoriGraphHalfEdge *secondHalf = &*(--edgeItr);
                VoriGraphHalfEdge *firstHalf = &*(--edgeItr);

                //start vertex
                topo_geometry::point start = firstHalf->source->point;
                //create middle vertex
                topo_geometry::point middle = cutresult.front().pathEdges.back().t();
                //end vertex
                topo_geometry::point end = secondHalf->target->point;

                VoriGraphVertex cutVertex;
                cutVertex.point = middle;
                //last halfedge in first vorigraphhalfedge cutresult
                cutVertex.obstacleDist = cutresult.front().pathEdges.back().dist();
                cutVertex.groupId = cutresult.front().groupId;

                vertices[middle] = cutVertex;

                //source and target (8 halfedges)
                //start
                firstHalf->source = &vertices[start];
                firstHalfTwin->target = firstHalf->source;
                //middle
                firstHalf->target = &vertices[middle];
                secondHalf->source = &vertices[middle];
                firstHalfTwin->source = firstHalf->target;
                secondHalfTwin->target = secondHalf->source;
                //end
                secondHalf->target = &vertices[end];
                secondHalfTwin->source = secondHalf->target;

                //edgeConnected list
                //start (2 additional)
                vertices[start].edgesConnected.push_back( firstHalf );
                vertices[start].edgesConnected.push_back( firstHalfTwin );
                //vertices[start].markTwins();

                //middle(4 additional)
                vertices[middle].edgesConnected.push_back( firstHalf );
                vertices[middle].edgesConnected.push_back( firstHalfTwin );
                vertices[middle].edgesConnected.push_back( secondHalf );
                vertices[middle].edgesConnected.push_back( secondHalfTwin );

                //end(2 additional)
                vertices[end].edgesConnected.push_back( secondHalf );
                vertices[end].edgesConnected.push_back( secondHalfTwin );


                vertices[start].markTwins();
                vertices[middle].markTwins();
                vertices[end].markTwins();

                //mark roomvertex
                vertices[middle].markRoomVertex();
                //set roomId
                vertices[middle].setRoomId( roomId );

                markDeadEnds();

                return true;
            } else {
                cerr << "We should not reach here in vorigraphhalfedge cutting" << endl;
                exit( 1 );
            }
        }
    }
}
