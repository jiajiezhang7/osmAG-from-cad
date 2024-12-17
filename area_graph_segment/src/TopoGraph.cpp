
#include "TopoGraph.h"

// #include "VoronoiPlugin.h"

// #include <QDebug>

using namespace std;


TopoGraph::TopoGraph(VoriGraph &pVoriGraph) : aVoriGraph(pVoriGraph) {
}


void findCloseVertices(VoriGraphVertex *start, map<VoriGraphVertex *, double> &add) {
    // if this is an end point of a dead end we are not interested in joining...
    if (start->edgesConnected.size() < 3) return;
    std::list<VoriGraphHalfEdge *>::iterator itrConnectedEdges;
    for (itrConnectedEdges = start->edgesConnected.begin();
         itrConnectedEdges != start->edgesConnected.end(); ++itrConnectedEdges) {
        cout.flush();
        if ((*itrConnectedEdges)->isRay()) continue;
        // we are only interested in those edges which have this vertex as source... (e.g. ignore the twins)
        if ((*itrConnectedEdges)->source != start) continue;
//     cout<<&(*itrConnectedEdges)<<" dist: "<<(*itrConnectedEdges)->distance<<" twin dist "<<(*itrConnectedEdges)->twin->distance<<endl;
        if ((*itrConnectedEdges)->distance <= sConfig->topoGraphDistanceToJoinVertices()) {
            //first check if the vertex has already been taken care of (should not happen!?)
            if ((*itrConnectedEdges)->target->groupId != 0) {
                cout << "Vertex to be joined but already taken care of :( " << (*itrConnectedEdges)->target;
                continue;
            }
            // ok we found a short one - first check if this one is already in the list!
            map<VoriGraphVertex *, double>::iterator found = add.find((*itrConnectedEdges)->target);
            if (found == add.end()) {
                // if this is an end point of a dead end we are not interested in joining...
                if ((*itrConnectedEdges)->target->edgesConnected.size() < 3) continue;

                //this is a new one - mark to be joined!
                add[(*itrConnectedEdges)->target] = (*itrConnectedEdges)->distance;
                // also mark the joined away edges...
                (*itrConnectedEdges)->groupId = 1;
                (*itrConnectedEdges)->twin->groupId = 1;
                // and recursively also check this one
                findCloseVertices((*itrConnectedEdges)->target, add);
            }
        }
    }

}

void TopoGraph::createFromVoriGraph() {
    aExits.clear();
    aVertices.clear();
    aHalfEdges.clear();

    // groupId 1 will be set for all entries which has been taken care of
    removeGroupId(aVoriGraph);    //遍历voriGraph.halfEdges和voriGraph.vertices把它们的groupId置为0

    // create a translation entry from voriVertices to TopoVertices
    map<VoriGraphVertex *, TopoVertex *> mapVoriTopoVertex;

    VoriGraph::VertexMap::iterator itrVertices;
    for (itrVertices = aVoriGraph.vertices.begin(); itrVertices != aVoriGraph.vertices.end(); ++itrVertices) {
        cout.flush();
        // check if this vertex was already taken care of (due to joining)
        if (itrVertices->second.groupId != 0) {
            continue;
        }
        // the second double is the distance of said vertice
        map<VoriGraphVertex *, double> verticesToJoin;
        // add this one of course:
        verticesToJoin[&itrVertices->second] = 0.;
        // first check the distances
        findCloseVertices(&itrVertices->second, verticesToJoin);
        // now we know which VoriGraph vertices to used to create the TopoVertex - do it (most often its just one vertex)

        //add the vertex
        {
            TopoVertex newVertex;
            aVertices.push_back(newVertex);
        }
        TopoVertex &vertex = *aVertices.rbegin();

        vertex.averageDistanceToObstacles = 0.;
        double averageX = 0.;
        double averageY = 0.;
        vertex.distanceOfJoinedVertices = 0.;
        map<VoriGraphVertex *, double>::iterator itrToJoin;
        for (itrToJoin = verticesToJoin.begin(); itrToJoin != verticesToJoin.end(); ++itrToJoin) {
            vertex.averageDistanceToObstacles += itrToJoin->first->obstacleDist;
            averageX += topo_geometry::getX(itrToJoin->first->point);
//       averageY += itrToJoin->first->vertex->point().y();
            averageY += topo_geometry::getY(itrToJoin->first->point);
            vertex.aVoriVertices.push_back(itrToJoin->first);
            vertex.distanceOfJoinedVertices += itrToJoin->second;
            // mark as already taken care of
            itrToJoin->first->groupId = 1;
            mapVoriTopoVertex[itrToJoin->first] = &vertex;
        }
        vertex.averageDistanceToObstacles /= verticesToJoin.size();
        averageX /= verticesToJoin.size();
        averageY /= verticesToJoin.size();
        vertex.point = topo_geometry::point(averageX, averageY);
    }

    // now we have all the vertices - next create the HalfEdges

    list<VoriGraphHalfEdge>::iterator itrHalfEdges;
    for (itrHalfEdges = aVoriGraph.halfEdges.begin(); itrHalfEdges != aVoriGraph.halfEdges.end(); ++itrHalfEdges) {
        // if this edge was joined away ignore it...
        if (itrHalfEdges->groupId != 0) continue;
        aHalfEdges.push_back(TopoHalfEdge());
        TopoHalfEdge &edge = *aHalfEdges.rbegin();
        if (itrHalfEdges->source) edge.sourceVertex = mapVoriTopoVertex[itrHalfEdges->source];
        if (itrHalfEdges->target) edge.targetVertex = mapVoriTopoVertex[itrHalfEdges->target];
        // for now there is only one half edge...
        edge.distance = itrHalfEdges->distance;
        edge.voriHalfEdges.push_back(&*itrHalfEdges);
    }

    // now create the exits (could theoretically be done in the above step - but this way it is cleaner)
    list<TopoHalfEdge>::iterator itrTopoHalfEdges;
    for (itrTopoHalfEdges = aHalfEdges.begin(); itrTopoHalfEdges != aHalfEdges.end(); ++itrTopoHalfEdges) {
        // take care of rays ;)
        if (itrTopoHalfEdges->sourceVertex == 0) continue;
        aExits.push_back(TopoExit());
        TopoExit &exit = *aExits.rbegin();
        exit.exitEdge = &*itrTopoHalfEdges;
        itrTopoHalfEdges->sourceVertex->aExits.push_back(&exit);
        // calculate the distance...
        //TODO: get the distance   boost::geometry::distance
//     exit.vertexEdgeDistance = sqrt(squared_distance( exit.exitEdge->getFirst()->source->vertex->point(), exit.source()->point ));
        exit.vertexEdgeDistance = boost::geometry::distance(exit.exitEdge->getFirst()->source->point,
                                                            exit.source()->point);

    }
    // now that all exits have proper vertex distances we can calculate the new edge distances (with vertex distances on both ends!)
    for (list<TopoExit>::iterator itrExits = aExits.begin(); itrExits != aExits.end(); ++itrExits) {
        itrExits->totalDistance = itrExits->vertexEdgeDistance + itrExits->exitEdge->distance;
        if (itrExits->exitEdge->sourceExit) itrExits->totalDistance += itrExits->exitEdge->sourceExit->vertexEdgeDistance;
    }


    // now that all exits are there we can create the twin entries in the halfEdges
    for (itrTopoHalfEdges = aHalfEdges.begin(); itrTopoHalfEdges != aHalfEdges.end(); ++itrTopoHalfEdges) {
        // take care of rays...
        if (itrTopoHalfEdges->targetVertex == 0) continue;
        // search for the exit in the target which has the source as source
        list<TopoExit *>::iterator itrExits;
        for (itrExits = itrTopoHalfEdges->targetVertex->aExits.begin();
             itrExits != itrTopoHalfEdges->targetVertex->aExits.end(); ++itrExits) {
            if ((*itrExits)->target() == itrTopoHalfEdges->sourceVertex) {
                // this is the correct one...
                (*itrExits)->exitEdge->twin = &*itrTopoHalfEdges;
                // also other way around - make most of them double but otherwise we would miss some of the rays!
                itrTopoHalfEdges->twin = (*itrExits)->exitEdge;
                // we can also mark our twin
                break;
            }
        }
    }
    cout << "now we have " << aVertices.size() << " vertices, " << aHalfEdges.size() << " halfEdges and "
         << aExits.size() << " exits." << endl;

    // remove strange empty vertices from rays and calculate the angles...
    list<TopoVertex>::iterator itrTopoVertices;
    for (itrTopoVertices = aVertices.begin(); itrTopoVertices != aVertices.end();) {
        if (itrTopoVertices->aExits.empty()) {
            itrTopoVertices = aVertices.erase(itrTopoVertices);
        } else {
            itrTopoVertices->calculateAngles();
            ++itrTopoVertices;
        }
    }

    calcAllDistances();

}


bool compareVertexPositions(const TopoVertex *first, const TopoVertex *second) {
    if (first->point.x() == second->point.x()) return first->point.y() < second->point.y();
    return first->point.x() < second->point.x();
}

void TopoGraph::assignVertexIds() {

    list<TopoVertex *> vertices;
    for (list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        vertices.push_back(&*itrVertices);
    }
    vertices.sort(compareVertexPositions);
    unsigned int counter = 1;
    for (list<TopoVertex *>::iterator itr = vertices.begin(); itr != vertices.end(); ++itr) {
        (*itr)->id = counter++;
    }
}


double clockWiseAngleRad(double start, double end) {
    if (start < 0.) start += 2 * M_PI;
    if (start >= 2 * M_PI) start -= 2 * M_PI;
    if (end < 0.) end += 2 * M_PI;
    if (end >= 2 * M_PI) end -= 2 * M_PI;
    if (start < end) {
        return 2 * M_PI - end + start;
    } else {
        return start - end;
    }
}

bool smallerThan(pair<double, TopoExit *> &first, pair<double, TopoExit *> &second) {
    return first.first < second.first;
}

void TopoVertex::calculateAngles() {
    // special case with just one exits first...
    if (aExits.size() < 2) {
        biggestExitAngleRad = 2 * M_PI;
        smallestExitAngleRad = 2 * M_PI;
        (*aExits.begin())->nextTopoExit = *aExits.begin();
        return;
    }
    // calculate the global angles ...
    list<pair<double, TopoExit *> > globalAnglesRad;
    for (list<TopoExit *>::iterator itrExits = aExits.begin(); itrExits != aExits.end(); ++itrExits) {
        topo_geometry::point otherPoint;
        double startDistance = sConfig->topoGraphAngleCalcStartDistance() - (*itrExits)->vertexEdgeDistance;
        if (startDistance < 0.) startDistance = 0.;
        double endDistance = sConfig->topoGraphAngleCalcEndDistance() - (*itrExits)->vertexEdgeDistance;
        if (endDistance < 0.) endDistance = 0.;
        list<double> angles; // between 0 and 2*M_PI
        for (double di = endDistance; di >= startDistance; di -= sConfig->topoGraphAngleCalcStepSize()) {
            if ((*itrExits)->exitEdge->getPointForDistance(di, otherPoint)) {
                double ang = atan2(point.y() - topo_geometry::getY(otherPoint),
                                   point.x() - topo_geometry::getX(otherPoint));
                if (ang < 0.) ang += 2 * M_PI;
                angles.push_back(ang);
            }
        }
        if (angles.empty()) {
            cerr << "Cannot calculate angle of edge - check your configuration!!" << endl;
            return;
        }
        list<double>::iterator itrAngles = angles.begin();
        double startAngle = *itrAngles;
        ++itrAngles;
        double error = 0.;
        unsigned int count = 1;
        for (; itrAngles != angles.end(); ++itrAngles, ++count) {
            error += min((2 * M_PI) - fabs(*itrAngles - startAngle), fabs(*itrAngles - startAngle));
        }
        startAngle = startAngle + error / count;
        if (startAngle < 0.) startAngle += 2 * M_PI;
        if (startAngle >= 2 * M_PI) startAngle -= 2 * M_PI;
        globalAnglesRad.push_back(pair<double, TopoExit *>(startAngle, *itrExits));
    }
    // now we have the global angles - sort and put in...
    globalAnglesRad.sort(smallerThan);
    list<pair<double, TopoExit *> >::iterator itrAngles = globalAnglesRad.begin();
    TopoExit *currentExit = itrAngles->second;
    double currentAngle = itrAngles->first;
    ++itrAngles;

    for (; itrAngles != globalAnglesRad.end(); ++itrAngles) {
        currentExit->nextTopoExit = itrAngles->second;
        currentExit->angleToNextTopoExitRad = clockWiseAngleRad(itrAngles->first, currentAngle);
        if (currentExit->angleToNextTopoExitRad < 0.) currentExit->angleToNextTopoExitRad += 2 * M_PI;
        if (currentExit->angleToNextTopoExitRad >= 2 * M_PI) currentExit->angleToNextTopoExitRad -= 2 * M_PI;
        currentExit = itrAngles->second;
        currentAngle = itrAngles->first;
    }
    // the last one has to point to the first one...
    currentExit->nextTopoExit = globalAnglesRad.begin()->second;
    currentExit->angleToNextTopoExitRad = clockWiseAngleRad(globalAnglesRad.begin()->first, currentAngle);
    if (currentExit->angleToNextTopoExitRad < 0.) currentExit->angleToNextTopoExitRad += 2 * M_PI;
    if (currentExit->angleToNextTopoExitRad >= 2 * M_PI) currentExit->angleToNextTopoExitRad -= 2 * M_PI;

    // now mark the biggest and the smallest angles in the vertex
    biggestExitAngleRad = 0.;
    smallestExitAngleRad = 2 * M_PI;
    for (list<TopoExit *>::iterator itrExits = aExits.begin(); itrExits != aExits.end(); ++itrExits) {
        if ((*itrExits)->angleToNextTopoExitRad > biggestExitAngleRad)
            biggestExitAngleRad = (*itrExits)->angleToNextTopoExitRad;
        if ((*itrExits)->angleToNextTopoExitRad < smallestExitAngleRad)
            smallestExitAngleRad = (*itrExits)->angleToNextTopoExitRad;
    }
}

bool TopoHalfEdge::getPointForDistance(double distance, topo_geometry::point &pPoint) {
    if (voriHalfEdges.size() != 1) {
        cerr << "not yet implemented!" << endl;
        assert(0);
    }
    return (*voriHalfEdges.begin())->getPointForDistance(distance, pPoint);
}


//
// checks everything that exits from the first vertex
void TopoGraph::checkFirstVertexInList(map<TopoVertex *, bool> &workList) {
    if (workList.empty()) return; // should never happen
    TopoVertex *curr = workList.begin()->first;
    // remove this one from the list
    workList.erase(workList.begin());
    // first the easy case - this is the end of a dead end:
    if (curr->aExits.size() == 1) {
        unsigned int flags = TopoHalfEdge::DEAD_END | TopoHalfEdge::DEAD_ENDISH;
        // check the length
        if ((*curr->aExits.begin())->exitEdge->distance <= sConfig->topoGraphMarkAsFeatureEdgeLength()) {
            flags = flags | TopoHalfEdge::FEATURE_END;
        }
        // now set the properties and add the target to the work list
        (*curr->aExits.begin())->twinEdge()->edgeFlags = flags;
        // in the very unlikely event that this is a ray...
        if ((*curr->aExits.begin())->exitEdge->targetVertex) {
            workList[(*curr->aExits.begin())->exitEdge->targetVertex] = true;
        }
    } else {
        // more complicated case of multiple exits - first check what is coming in
        // find out what is coming on on all the exits
        unsigned int numIncomingDeadEndish = 0;
        unsigned int numIncomingOutsideisch = 0;
        unsigned int numIncomingEmpties = 0;
        // check every exit
        for (list<TopoExit *>::iterator itrExits = curr->aExits.begin(); itrExits != curr->aExits.end(); ++itrExits) {
            TopoExit *topoExit = *itrExits;
            // first check if this is a ray
            if (topoExit->exitEdge->isRay()) {
                ++numIncomingOutsideisch;
                // set the ray properties
                topoExit->exitEdge->edgeFlags = TopoHalfEdge::OUTSIDE | TopoHalfEdge::OUTSIDEISH;
                continue;
            }
            if (topoExit->exitEdge->edgeFlags & TopoHalfEdge::DEAD_ENDISH) ++numIncomingDeadEndish;
            if (topoExit->exitEdge->edgeFlags & TopoHalfEdge::OUTSIDEISH) ++numIncomingOutsideisch;
            if ((topoExit->exitEdge->edgeFlags & TopoHalfEdge::OUTSIDEISH) == 0 &&
                (topoExit->exitEdge->edgeFlags & TopoHalfEdge::DEAD_ENDISH) == 0) {
                ++numIncomingEmpties;
            }
        }
        // now lets see if we can do stuff
        if (numIncomingEmpties < 2) {
            // we have one or no empty exits - "send" the information to all exits
            for (list<TopoExit *>::iterator itrExits = curr->aExits.begin();
                 itrExits != curr->aExits.end(); ++itrExits) {
                TopoExit *topoExit = *itrExits;
                if (topoExit->exitEdge->isRay()) continue;
                unsigned int flags = 0;
                unsigned int isDeadEndish = topoExit->twinEdge()->edgeFlags & TopoHalfEdge::DEAD_ENDISH;
                unsigned int isOutsideish = topoExit->twinEdge()->edgeFlags & TopoHalfEdge::OUTSIDEISH;
                if (numIncomingDeadEndish - isDeadEndish) {
                    flags = flags | TopoHalfEdge::DEAD_ENDISH;
                }
                if (numIncomingOutsideisch - isOutsideish) {
                    flags = flags | TopoHalfEdge::OUTSIDEISH;
                }
                // check if the flag we want to set differs!
                if ((topoExit->twinEdge()->edgeFlags & flags) != flags) {
                    // we have to set and add to work list
                    topoExit->twinEdge()->edgeFlags = topoExit->twinEdge()->edgeFlags | flags;
                    workList[topoExit->target()] = true;
                }
            }
        }
    }
}

void TopoGraph::markGraph() {
    map<TopoVertex *, bool> workList;
    // fill the work list with all dead ends
    list<TopoVertex>::iterator itrVertices;
    for (itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        if (itrVertices->aExits.size() < 2) {
            // this is a dead end - add to the list
            workList[&*itrVertices] = true;
        }
    }
    // now work on the list....
    while (!workList.empty()) {
        checkFirstVertexInList(workList);
    }
    // mark the vertices, too
    for (itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        unsigned int countNonFeatureExits = 0;
        for (list<TopoExit *>::iterator itrExits = itrVertices->aExits.begin();
             itrExits != itrVertices->aExits.end(); ++itrExits) {
            if (!((*itrExits)->exitEdge->edgeFlags & TopoHalfEdge::FEATURE_END)) ++countNonFeatureExits;
        }
        itrVertices->isFeatureVertex = (countNonFeatureExits == 2);
    }
}


void TopoGraph::printInfo() {
    for (list<TopoHalfEdge>::iterator itrTopoHalfEdges = aHalfEdges.begin();
         itrTopoHalfEdges != aHalfEdges.end(); ++itrTopoHalfEdges) {
        cout << " edge: ";
        if (itrTopoHalfEdges->sourceVertex) cout << topo_geometry::print(itrTopoHalfEdges->sourceVertex->point);
        else
            cout << "INF";
        cout << " to ";
        if (itrTopoHalfEdges->targetVertex) cout << topo_geometry::print(itrTopoHalfEdges->targetVertex->point);
        else
            cout << "INF";
        cout << " : ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::DEAD_END) cout << "deadEnd ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::DEAD_ENDISH) cout << "deadEndish ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::FEATURE_END) cout << "feature ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::OUTSIDE) cout << "outside ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::OUTSIDEISH) cout << "outsideish ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::LOOP) cout << "loop ";
        if (itrTopoHalfEdges->edgeFlags & TopoHalfEdge::LOOP_BACK) cout << "loopBack ";
        cout << endl;
    }
}

void DistanceCalcHelper::clear() {
    distance = -1.;
    hops = 0;
    majorHops = 0;
}


void TopoGraph::removeDistanceMarks() {
    for (list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        itrVertices->distanceCalcHelper.clear();
    }
}

void TopoGraph::calcAllDistances() {
    markGraph();
    for (list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        for (list<TopoExit *>::iterator itrExits = itrVertices->aExits.begin();
             itrExits != itrVertices->aExits.end(); ++itrExits) {
            calcDistancesFor(*itrExits);
        }
    }
}

void TopoGraph::setInconsistencyMarks(bool set) {
    for (list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        itrVertices->inconsistent = set;
    }
}

void TopoGraph::addTargetToWorkList(TopoExit *currExit, set<TopoExit *> &workList, TopoVertex *startVertex) {
    //first check if the target is not the start vertex
    if (currExit->target() == startVertex) return;
    // add all exits on the target to the work list - except the twin of currExit...
    for (list<TopoExit *>::iterator itrExits = currExit->target()->aExits.begin();
         itrExits != currExit->target()->aExits.end(); ++itrExits) {
        if ((*itrExits)->target() == currExit->source()) continue;
        workList.insert(*itrExits);
    }
}

TopoExit *TopoVertex::findDirectExitTo(TopoVertex *vertex) {
    for (list<TopoExit *>::iterator itr = aExits.begin(); itr != aExits.end(); ++itr) {
        if ((*itr)->target() == vertex) return *itr;
    }
    return 0;
}

TopoExit *TopoVertex::findExitTo(TopoVertex *vertex, bool *wasMajor) {
    for (list<TopoExit *>::iterator itr = aExits.begin(); itr != aExits.end(); ++itr) {
        if ((*itr)->target() == vertex) {
            if (wasMajor) *wasMajor = false;
            return *itr;
        }
        if ((*itr)->nextMajorVertex == vertex) {
            if (wasMajor) *wasMajor = true;
            return *itr;
        }
    }
    return 0;
}

void TopoGraph::calcDistancesFor(TopoExit *startExit) {

    removeDistanceMarks();

    TopoVertex *startVertex = startExit->source();
    bool thereIsALoop = false;

    map<TopoVertex *, DistanceCalcHelper> loopingInVia;

    startVertex->distanceCalcHelper.distance = 0.;

    set<TopoExit *> workList;
    workList.insert(startExit);

    while (!workList.empty()) {
        TopoExit *currExit = *workList.begin();
        workList.erase(workList.begin());

        if (currExit->exitEdge->isRay()) continue;

        DistanceCalcHelper distCalc = currExit->source()->distanceCalcHelper;
        distCalc.distance += currExit->distance();
        distCalc.hops++;
        //check if this is a major hop
        if (!startVertex->isFeatureVertex) ++distCalc.majorHops;

        // check if a loop occured
        if (currExit->target()->distanceCalcHelper.distance != -1) thereIsALoop = true;

        // check if the goal is unset or has a longer distance...
        if (currExit->target()->distanceCalcHelper.distance == -1 ||
            currExit->target()->distanceCalcHelper.distance > distCalc.distance) {
            // we update the target and add the exits there to the work list
            currExit->target()->distanceCalcHelper = distCalc;
            addTargetToWorkList(currExit, workList, startVertex);
        }
        // if this is the startVertex again we want to save from where we came:
        if (currExit->target() == startVertex) {
            if (loopingInVia[currExit->source()].distance == -1 ||
                loopingInVia[currExit->source()].distance > distCalc.distance) {
                loopingInVia[currExit->source()] = distCalc;
            }
        }
    } // while
    // add the loop info we gathered to the edge
    if (thereIsALoop) {
        startExit->exitEdge->edgeFlags = startExit->exitEdge->edgeFlags | TopoHalfEdge::LOOP;
    }
    if (!loopingInVia.empty()) {
        startExit->exitEdge->edgeFlags = startExit->exitEdge->edgeFlags | TopoHalfEdge::LOOP_BACK;
    }
    // add the loop info to the vertex
    if (!loopingInVia.empty()) {
        for (map<TopoVertex *, DistanceCalcHelper>::iterator itr = loopingInVia.begin();
             itr != loopingInVia.end(); ++itr) {
            // find the exit in that direction:
            TopoExit *first = startVertex->findDirectExitTo(itr->first);
            TopoExit *second = startExit;
            if (second < first) {
                second = first;
                first = startExit;
            }
            if (first == second) {
//         cout<<"Grosse schweinerei! "<<itr->second.distance<<"  "<<itr->second.hops<<endl;
//         assert(0);
            } else {
                startVertex->loops[pair<TopoExit *, TopoExit *>(first, second)] = itr->second;
            }
        }
    }

    double nextMajorVertexDist = -1.;
    TopoVertex *nextMajorVertex = 0;
    //add the distnace info to the exit
    for (list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices) {
        if ((itrVertices->distanceCalcHelper.distance != -1.) && (&*itrVertices != startVertex)) {
            startExit->distances[&*itrVertices] = itrVertices->distanceCalcHelper;
            // also find the shortest distance to the next major node...
            if (!itrVertices->isFeatureVertex && itrVertices->aExits.size() > 1) {
                // this is a major node
                if (nextMajorVertexDist == -1. || itrVertices->distanceCalcHelper.distance < nextMajorVertexDist) {
                    nextMajorVertexDist = itrVertices->distanceCalcHelper.distance;
                    nextMajorVertex = &*itrVertices;
                }
            }
        }
    }
    if (nextMajorVertexDist > 0.) {
        startExit->distanceToNextMajorVertex = nextMajorVertexDist;
        startExit->nextMajorVertex = nextMajorVertex;
    }
}


