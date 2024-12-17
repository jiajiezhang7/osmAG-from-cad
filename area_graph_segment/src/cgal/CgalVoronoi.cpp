#include "cgal/CgalVoronoi.h"

#include <QPainter>
#include <QImage>
#include <QDebug>
#include <QPolygon>
#include <iostream>

using namespace std;


//extern VoriConfig *sConfig;

CgalVoronoi::VD vdStatic; //< hack for the transition only!

set<CgalVoronoi::VD::Face_handle> delface_set;

void paintVoronoi(CgalVoronoi::VD &pVd, QImage &image, map<CgalVoronoi::Halfedge_handle, double> &list);


void generateVoriGraph(CgalVoronoi::VD &pVd, std::map<CgalVoronoi::Halfedge_handle, double> &halves, VoriGraph &voriGraph);

void filterForDist(CgalVoronoi::VD &pVd, std::map<CgalVoronoi::Halfedge_handle, double> &pResult, double pMinDistance);


void paintVoronoi(QImage &image, CgalVoronoi::VD & vd);
//#include "qt/QImageVoronoi.h"
void paintVori_face(QImage &image, map<CgalVoronoi::Halfedge_handle, double> &halves,
                    std::vector<topo_geometry::point> sites);
void paintdelface(QImage &image);
//set<CgalVoronoi::VD::Face_handle> VGface_set;
map<CgalVoronoi::VD::Face_handle, VoriGraphPolygon *> face_polygon; //记录被joined过的每个face属于那个polygon

bool createVoriGraph(const std::vector<topo_geometry::point> &sites, VoriGraph &voriGraph, VoriConfig *sConfig) {
    // 使用 std::vector 来存储插入点
    std::vector<CgalVoronoi::Site_2> insertSites;

    for (const auto& site : sites) {
        insertSites.push_back(CgalVoronoi::Site_2(topo_geometry::getX(site), topo_geometry::getY(site)));
    }

    // 使用智能指针来管理 CGAL::VD 对象的生命周期
    auto vd = std::make_unique<CgalVoronoi::VD>();
    vd->insert(insertSites.begin(), insertSites.end());

    // 创建一个地图来存储过滤后的边和距离
    std::map<CgalVoronoi::Halfedge_handle, double> filteredEdgeListWithDist;
    QImage save1(1500, 1500, QImage::Format_ARGB32);

    // 调用过滤函数
    filterForDist(*vd, filteredEdgeListWithDist, sConfig->voronoiMinimumDistanceToObstacle());

    // 生成 VoriGraph
    generateVoriGraph(*vd, filteredEdgeListWithDist, voriGraph);

    // 返回成功标志
    return true;
}


void createVoriGraphHalfEdgesForRay(CgalVoronoi::VD &pVd, map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &/*vertexSourceMap*/, VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle ray){

  CGAL::Ray_2<CgalVoronoi::K> rayValues;
  bool isRay = ( CGAL::assign( rayValues, pVd.dual().dual(ray->dual() ) ) );
  if(!isRay){
    cerr<<"Really starnge error - cannot cast to ray!"<<endl;
  }

  topo_geometry::point pointCoord(rayValues.source().x(), rayValues.source().y());
  VoriGraphVertex * vertex = &voriGraph.vertices[pointCoord];


  CgalVoronoi::Point_2 p = rayValues.point(20); //returns a point on r. point(0) is the source, point(i), with i>0, is different from the source.
  topo_geometry::point sourceP(rayValues.source().x(), rayValues.source().y());
  topo_geometry::point rayP(p.x(), p.y());
  topo_geometry::point obstacleP(ray->face()->dual()->point().x(), ray->face()->dual()->point().y());
  double distance = sqrt(squared_distance(rayValues, ray->face()->dual()->point()));

  VoriGraphHalfEdge edge1;
  edge1.source = vertex;
  edge1.target = 0;
  edge1.distance = -1;
//   edge1.ray = rayValues;
  voriGraph.halfEdges.push_back(edge1);
  VoriGraphHalfEdge * edge1Ptr = &*voriGraph.halfEdges.rbegin();
  assert(edge1Ptr != 0);
  vertex->edgesConnected.push_back(edge1Ptr);

  edge1.topo_ray = topo_geometry::Halfedge(sourceP, rayP, obstacleP, distance, true);

  // now the other direction!
  VoriGraphHalfEdge edge2;
  edge2.source = 0;
  edge2.target = vertex;
  edge2.distance = -1;
//   edge2.ray = rayValues;
  edge2.topo_ray = edge1.topo_ray;
  voriGraph.halfEdges.push_back(edge2);
  VoriGraphHalfEdge * edge2Ptr = &*voriGraph.halfEdges.rbegin();
  assert(edge2Ptr != 0);
  vertex->edgesConnected.push_back(edge2Ptr);
  vertex->markTwins();
}

double dist(topo_geometry::point a, topo_geometry::point b)
{
    double dx=a.x()-b.x();
    double dy=a.y()-b.y();
    return sqrt(dx*dx+dy*dy);
}
double computeAngle(topo_geometry::point o,topo_geometry::point p){
    double dx=p.x()-o.x();
    double dy=p.y()-o.y();
    double cosa=fabs(dx)/dist(o,p);
    double angle, result = acos (cosa) * 180.0 / M_PI;
    if(dx>=0 && dy>=0) {//第一象限
        angle=result;
    } else if(dx<0&&dy>=0) {//第二象限
        angle=180-result;
    } else if(dx<0&&dy<0){//第三象限
        angle=180+result;
    } else{// 第四象限
        angle=360-result;
    }
    return angle;
}
std::list<topo_geometry::point> findOutlinepoints(
                                            topo_geometry::point* sourceP,
                                            topo_geometry::point* targetP,
                                            std::map<topo_geometry::point*, topo_geometry::point* > nextpoint_map){
    std::list<topo_geometry::point> result_list;
    topo_geometry::point* curr=targetP;
    topo_geometry::point* next;
    int i=0;
    while(true){   //在此循环中不断寻找下一个轮廓点加入result_list
        i++;
        if(i>5000){cout<<"more than 5000 loops!!!"<<endl;break;}
        next=nextpoint_map[curr];
//        cout<<" ("<<curr->x()<<", "<<curr->y()<<")-->("<<next->x()<<", "<<next->y()<<") ";

        curr=next;
        if(next==sourceP)break;
        result_list.push_back(*next);

    }
//    cout<<endl;
    return result_list;
}
void createVoriGraphHalfEdgeandVoriGraphPolygon(//create polygon by connecting path and sites, add deleted faces to nearest polygon
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo){
    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    list<topo_geometry::point> pathpoints;

    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标

    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

//    map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > nextvertex_map;
    map<topo_geometry::point*, topo_geometry::point* > nextpoint_map;
    std::set<CgalVoronoi::VD::Face_handle> face_set;
    CgalVoronoi::Halfedge_handle curr = start;
    topo_geometry::point* lastobstacle;
    topo_geometry::point* firstobstacle=0;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        polygon.sites.push_back(obstacleP);
        topo_geometry::point* obsPtr = &*polygon.sites.rbegin();

        if(pathpoints.empty()){
            pathpoints.push_back(sourceP);
        }
        pathpoints.push_back(targetP);
        edge.distance += halfedge.length();

        if(face_set.find(curr->face())==face_set.end()){//never add this face
            if(!curr->face()->is_unbounded()){
                face_set.insert(curr->face());

                if(firstobstacle==0){
                    firstobstacle=obsPtr;
                }else{
                    nextpoint_map[obsPtr]=lastobstacle;
                }
                lastobstacle=obsPtr;
            }
        }   //end if (face not in face_set)

        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)




    // now also add the vertex for the target of curr

    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
    edge.target = target;
    edge.obstacleAverage /= edge.pathEdges.size();

    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);


    if(face_set.empty())return;
    //build the polygon by finding the outline points

    //add the deleted face (belong to the edge too close to sites) to the polygon
//#define DIST_SITES 1.5  //the longest distance between two closest sites
//    while(!delface_set.empty()){
//        set<CgalVoronoi::VD::Face_handle>::iterator fitr=delface_set.begin();
//        double min_dist=100;
//        CgalVoronoi::VD::Face_handle nearest_face;
//        topo_geometry::point *obs_ins=0,*obs_ains=0, *last_obs=0;
//        for(;fitr!=delface_set.end();fitr++){
//            topo_geometry::point site((*fitr)->dual()->point().x(),(*fitr)->dual()->point().y());
//            for(topo_geometry::point* obs=lastobstacle;obs!=firstobstacle;last_obs=obs, obs=nextpoint_map[obs]){
//
//                double curr_dist= dist(site,*obs);
//                if(min_dist>curr_dist){
//                    min_dist=curr_dist;
//                    nearest_face=*fitr;
//                    obs_ins=obs;
//                    if(obs==lastobstacle){
//                        double last_x=obs->x()+obs->x()-nextpoint_map[obs]->x();
//                        double last_y=obs->y()+obs->y()-nextpoint_map[obs]->y();
//                        topo_geometry::point tempsite(last_x,last_y);
//                        obs_ains=dist(site,tempsite)<=dist(site, *nextpoint_map[obs])?lastobstacle:nextpoint_map[obs];
//                    }else if(obs==firstobstacle){
//                        double next_x=obs->x()+obs->x()-last_obs->x();
//                        double next_y=obs->y()+obs->y()-last_obs->y();
//                        topo_geometry::point tempsite(next_x,next_y);
//                        obs_ains=dist(site,tempsite)<=dist(site, *last_obs)?firstobstacle:last_obs;
//                    }else{
//                        obs_ains=dist(site,*last_obs)<=dist(site, *nextpoint_map[obs])?last_obs:nextpoint_map[obs];
//                    }
//                }
//            }
//        }
//        if(min_dist>DIST_SITES){
//            break;
//        } else{
//            if(obs_ins==0||obs_ains==0||last_obs==0){
//                cout<<"strange!!!obs_ins==0||obs_ains==0||last_obs==0"<<endl;
//            }
//            topo_geometry::point site(nearest_face->dual()->point().x(),nearest_face->dual()->point().y());
//            polygon.sites.push_front(site);
//            topo_geometry::point* tempobs=&*polygon.sites.begin();
//            if(obs_ins==firstobstacle&&obs_ains==obs_ins){
//                firstobstacle=&*polygon.sites.begin();
//                nextpoint_map[obs_ins]=firstobstacle;
//            }else if(obs_ains==obs_ins && obs_ins==lastobstacle){
//                nextpoint_map[tempobs]=lastobstacle;
//                lastobstacle=tempobs;
//            }else{
//                if(obs_ins==nextpoint_map[obs_ains]){
//                    nextpoint_map[obs_ains]=tempobs;
//                    nextpoint_map[tempobs]=obs_ins;
//                }else if(obs_ains==nextpoint_map[obs_ins]){
//                    nextpoint_map[obs_ins]=tempobs;
//                    nextpoint_map[tempobs]=obs_ains;
//                }
//            }
//            delface_set.erase(nearest_face);
//        }
//    }

    list<topo_geometry::point> polygonP_list;
    polygonP_list.splice(polygonP_list.end(), pathpoints);
//    cout<<"path: ";
//    for(list<topo_geometry::point>::iterator Vitr=polygonP_list.begin();
//        Vitr!=polygonP_list.end();Vitr++){
//        cout<<"("<<(*Vitr).x()<<", "<<(*Vitr).y()<<")";
//    }
//    cout<<endl;

    nextpoint_map[firstobstacle]= &*polygonP_list.begin();
    nextpoint_map[&*polygonP_list.rbegin()]=lastobstacle;
//    cout<<"polygonP_list 's size is "<<polygonP_list.size()<<endl;

        topo_geometry::point *sourceP=&*polygonP_list.begin(), *targetP=&*polygonP_list.rbegin();
    list<topo_geometry::point> findlist=findOutlinepoints(sourceP,targetP, nextpoint_map);
    polygonP_list.splice(polygonP_list.end(),findlist);
    polygon.polygonpoints=polygonP_list;
//    cout<<"big face: ";
//    for(list<topo_geometry::point>::iterator Vitr=polygon.polygonpoints.begin();
//        Vitr!=polygon.polygonpoints.end();Vitr++){
//        cout<<"("<<(*Vitr).x()<<", "<<(*Vitr).y()<<")";
//    }
//    cout<<endl;

    voriGraph.pathFaces.push_back(polygon);
    VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
    assert(polygonPtr != 0);
    edgePtr->pathFace=polygonPtr;
    polygonPtr->belongpaths.push_back(edgePtr);

    source->markTwins();

//
}
void createVoriGraphHalfEdgeandVoriGraphPolygon_v5(//create polygon by connecting path and sites
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo){
    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    list<topo_geometry::point> pathpoints;

    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标

    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

//    map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > nextvertex_map;
    map<topo_geometry::point*, topo_geometry::point* > nextpoint_map;
    std::set<CgalVoronoi::VD::Face_handle> face_set;
    CgalVoronoi::Halfedge_handle curr = start;
    topo_geometry::point* lastobstacle;
    topo_geometry::point* firstobstacle=0;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        polygon.sites.push_back(obstacleP);
        topo_geometry::point* obsPtr = &*polygon.sites.rbegin();

        if(pathpoints.empty()){
            pathpoints.push_back(sourceP);
        }
        pathpoints.push_back(targetP);
        edge.distance += halfedge.length();

        ///* Jiawei: save face for each half edge!!! */

        if(face_set.find(curr->face())==face_set.end()){//never add this face
            bool has_ray=false;

            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
            f_ccb_start=curr->face()->ccb();

            for( f_ccb=f_ccb_start; f_ccb->next() != f_ccb_start; f_ccb++){
                if(f_ccb->is_ray()){
                    has_ray=true;
                    break;
                }
            }

            if(!has_ray){
                face_set.insert(curr->face());

                if(firstobstacle==0){
//                    cout<<"first obstacle: ("<<obsPtr->x()<<", "<<obsPtr->y()<<") "<<endl;
                    firstobstacle=obsPtr;
                }else{
                    nextpoint_map[obsPtr]=lastobstacle;
                }
                lastobstacle=obsPtr;
            } else{
                polygon.isRay=true;
            }

        }   //end if (face not in face_set)



        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)
    // now also add the vertex for the target of curr

    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
    edge.target = target;
    edge.obstacleAverage /= edge.pathEdges.size();

    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);


    if(face_set.empty())return;
    //build the polygon by finding the outline points

    list<topo_geometry::point> polygonP_list;
    polygonP_list.splice(polygonP_list.end(), pathpoints);
//    cout<<"path: ";
//    for(list<topo_geometry::point>::iterator Vitr=polygonP_list.begin();
//        Vitr!=polygonP_list.end();Vitr++){
//        cout<<"("<<(*Vitr).x()<<", "<<(*Vitr).y()<<")";
//    }
//    cout<<endl;

    nextpoint_map[firstobstacle]= &*polygonP_list.begin();
    nextpoint_map[&*polygonP_list.rbegin()]=lastobstacle;
//    cout<<"polygonP_list 's size is "<<polygonP_list.size()<<endl;

    topo_geometry::point *sourceP=&*polygonP_list.begin(), *targetP=&*polygonP_list.rbegin();
    list<topo_geometry::point> findlist=findOutlinepoints(sourceP,targetP, nextpoint_map);
    polygonP_list.splice(polygonP_list.end(),findlist);
    polygon.polygonpoints=polygonP_list;
//    cout<<"big face: ";
//    for(list<topo_geometry::point>::iterator Vitr=polygon.polygonpoints.begin();
//        Vitr!=polygon.polygonpoints.end();Vitr++){
//        cout<<"("<<(*Vitr).x()<<", "<<(*Vitr).y()<<")";
//    }
//    cout<<endl;

    voriGraph.pathFaces.push_back(polygon);
    VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
    assert(polygonPtr != 0);
    edgePtr->pathFace=polygonPtr;
    polygonPtr->belongpaths.push_back(edgePtr);

    source->markTwins();
}
std::list<CgalVoronoi::Vertex_handle> findOutline(//list<CgalVoronoi::Vertex_handle> &pathVertex,
        CgalVoronoi::Vertex_handle sourceV,
        CgalVoronoi::Vertex_handle last2ndV,
        CgalVoronoi::Vertex_handle targetV,
        std::map<CgalVoronoi::Vertex_handle, std::list<CgalVoronoi::Vertex_handle> > nextpoint_map){
    std::list<CgalVoronoi::Vertex_handle> result_list;
//    CgalVoronoi::Vertex_handle sourceV=*pathVertex.begin();
//
//    CgalVoronoi::Vertex_handle curr=pathVertex.back();
////    list<CgalVoronoi::Vertex_handle>::iterator Vptr=pathVertex.end();
////    Vptr--;Vptr--;
////    CgalVoronoi::Vertex_handle last=(*Vptr);
//    pathVertex.pop_back();
//    CgalVoronoi::Vertex_handle last=pathVertex.back();
//    pathVertex.push_back(curr);
    CgalVoronoi::Vertex_handle last=last2ndV;
    CgalVoronoi::Vertex_handle curr=targetV;
    CgalVoronoi::Vertex_handle next=curr;
    int i=0;
    while(true){   //在此循环中不断寻找下一个轮廓点加入result_list
        i++;
        if(i>5000){cout<<"more than 5000 loops!!!"<<endl;break;}
        double minangle=361.0;
        std::list<CgalVoronoi::Vertex_handle> nextpoint_list=nextpoint_map[curr];
        for(std::list<CgalVoronoi::Vertex_handle>::iterator nextitr=nextpoint_list.begin();
            nextitr!=nextpoint_list.end();nextitr++){//计算连接的边与上一条边的角度，找出右转角度最小
            CgalVoronoi::Vertex_handle maybe_next=*nextitr;
            topo_geometry::point currP(curr->point().x(),curr->point().y());
            topo_geometry::point maybe_nextP(maybe_next->point().x(),maybe_next->point().y());
            topo_geometry::point lastP(last->point().x(),last->point().y());
            double next_angle= computeAngle(currP,maybe_nextP);
            double last_angle= computeAngle(currP,lastP);
            double angle=next_angle<last_angle? (next_angle+360)-last_angle : next_angle-last_angle;
            if(angle<minangle)
            {
                minangle=angle;
                next=maybe_next;
            }
        }
        last=curr;
        curr=next;
        if(next==sourceV)break;
        result_list.push_back(next);

    }
    return result_list;
}
void createVoriGraphHalfEdgeandVoriGraphPolygon_v4(//connect the polygons along path
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo){
    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    list<CgalVoronoi::Vertex_handle> pathVertex;
    pathVertex.push_back(start->source());
    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标

    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

    map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > nextvertex_map;
    std::set<CgalVoronoi::VD::Face_handle> face_set;
    CgalVoronoi::Halfedge_handle curr = start;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        pathVertex.push_back(curr->target());
        edge.distance += halfedge.length();

        ///* Jiawei: save face for each half edge!!! */
        polygon.sites.push_back(obstacleP);
        if(face_set.find(curr->face())==face_set.end()){//never add this face
            bool has_ray=false;

            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
            f_ccb_start=curr->face()->ccb();

            map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > tempvertexmap;
            CgalVoronoi::Vertex_handle lastV;
            CgalVoronoi::Vertex_handle sourceV;
            if(f_ccb_start->has_source()) {
                sourceV=f_ccb_start->source();
                lastV=sourceV;
            }
            for( f_ccb=f_ccb_start; f_ccb->next() != f_ccb_start; f_ccb++){
                if(f_ccb->is_ray()){
                    has_ray=true;
                    break;
                }
                CgalVoronoi::Vertex_handle targetV=f_ccb->target();
                tempvertexmap[lastV].push_back(targetV);
                lastV=targetV;
            }

            if(!has_ray){
                face_set.insert(curr->face());
                tempvertexmap[lastV].push_back(sourceV);
                for(map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> >::iterator mapitr=tempvertexmap.begin();
                    mapitr!=tempvertexmap.end();mapitr++){
                    nextvertex_map[mapitr->first].splice(nextvertex_map[mapitr->first].end(), mapitr->second);
//                    cout<<endl<<"For ("<<mapitr->first->point().x()<<", "<<mapitr->first->point().y()<<"): ";
//                    for(list<CgalVoronoi::Vertex_handle>::iterator litr=nextvertex_map[mapitr->first].begin();
//                            litr!=nextvertex_map[mapitr->first].end();litr++){
//                        cout<<"("<<(*litr)->point().x()<<", "<<(*litr)->point().y()<<") ";
//                    }
                }
//                cout<<"a face not has ray..."<<endl;
            } else{
                polygon.isRay=true;
            }

        }   //end if (face not in face_set)



        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)
    // now also add the vertex for the target of curr

    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
    edge.target = target;
    CgalVoronoi::Vertex_handle sourceV = start->source();
    CgalVoronoi::Vertex_handle targetV = curr->target();
    CgalVoronoi::Vertex_handle last2nd = curr->source();
    edge.obstacleAverage /= edge.pathEdges.size();

    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);
//
//    bool allfacejoined=true;
//    int polycnt=0;
//    VoriGraphPolygon* faceVGpolygon=0;
//    for(std::set<CgalVoronoi::VD::Face_handle>::iterator faceitr=face_set.begin();
//        faceitr!=face_set.end();faceitr++){
//        if(face_polygon.find(*faceitr)==face_polygon.end()){ //该path上有未处理的face
//            allfacejoined=false;
//            faceVGpolygon=0;
//            break;
//        }else{
//            if(faceVGpolygon==0) {
//                polycnt++;
//                faceVGpolygon = face_polygon[*faceitr];
//            }else if(faceVGpolygon == face_polygon[*faceitr]){
//                polycnt++;
//            }else if(allfacejoined){
//                cout<<"Strange!! the polygon has two faces belong to defferdent polygon!"<<endl;
//            }
//        }
//    }

    if(face_set.empty())return;
//    if(!allfacejoined && !face_set.empty()){
        //build the polygon by finding the outline points
        list<CgalVoronoi::Vertex_handle> polygonV_list;
        polygonV_list.splice(polygonV_list.end(),pathVertex);
        cout<<"path: ";
        for(list<CgalVoronoi::Vertex_handle>::iterator Vitr=polygonV_list.begin();
            Vitr!=polygonV_list.end();Vitr++){
            cout<<"("<<(*Vitr)->point().x()<<", "<<(*Vitr)->point().y()<<")";
        }
        cout<<endl;
        list<CgalVoronoi::Vertex_handle> findlist=findOutline(sourceV, last2nd, targetV, nextvertex_map);
        polygonV_list.splice(polygonV_list.end(),findlist);
        cout<<"big face: ";
        for(list<CgalVoronoi::Vertex_handle>::iterator Vitr=polygonV_list.begin();
            Vitr!=polygonV_list.end();Vitr++){
            topo_geometry::point currP((*Vitr)->point().x(),(*Vitr)->point().y());
            polygon.polygonpoints.push_back(currP);
            cout<<"("<<(*Vitr)->point().x()<<", "<<(*Vitr)->point().y()<<")";
        }
        cout<<endl;

        voriGraph.pathFaces.push_back(polygon);
        VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
        assert(polygonPtr != 0);
        edgePtr->pathFace=polygonPtr;
        polygonPtr->belongpaths.push_back(edgePtr);

//        for(std::set<CgalVoronoi::VD::Face_handle>::iterator faceitr=face_set.begin();
//            faceitr!=face_set.end();faceitr++){
//            if(face_polygon.find(*faceitr)!=face_polygon.end()){    //该face曾属于其他polygon
//                VoriGraphPolygon* ori_polygon=face_polygon[(*faceitr)];
//                for(list<VoriGraphHalfEdge*>::iterator pathitr=ori_polygon->belongpaths.begin();
//                    pathitr!=ori_polygon->belongpaths.end();pathitr++){
//                    VoriGraphHalfEdge* tempVGpathPtr=(*pathitr);
//                    tempVGpathPtr->pathFace=polygonPtr;
//                    polygonPtr->belongpaths.push_back(tempVGpathPtr);
//                }
//            }
//            face_polygon[(*faceitr)]=polygonPtr;
//        }
//    } else if(allfacejoined&& !face_set.empty()){
//        //设置该path的pathface为更大的polygon
//        edgePtr->pathFace=faceVGpolygon;
//        faceVGpolygon->belongpaths.push_back(edgePtr);
//    }
    source->markTwins();
}
void createVoriGraphHalfEdgeandVoriGraphPolygon_backup_v3(//jiawei 2016.7.11, v3: all path use biger polygon, smaller polygon are given up
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo){
    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    list<CgalVoronoi::Vertex_handle> pathVertex;
    pathVertex.push_back(start->source());
    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标

    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

    map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > nextvertex_map;
    std::set<CgalVoronoi::VD::Face_handle> face_set;
    CgalVoronoi::Halfedge_handle curr = start;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        pathVertex.push_back(curr->target());
        edge.distance += halfedge.length();

        ///* Jiawei: save face for each half edge!!! */
        polygon.sites.push_back(obstacleP);
        if(face_set.find(curr->face())==face_set.end()){//never add this face
            bool has_ray=false;

            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
            f_ccb_start=curr->face()->ccb();

            map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> > tempvertexmap;
            CgalVoronoi::Vertex_handle lastV;
            CgalVoronoi::Vertex_handle sourceV;
            if(f_ccb_start->has_source()) {
                sourceV=f_ccb_start->source();
                lastV=sourceV;
            }
            for( f_ccb=f_ccb_start; f_ccb->next() != f_ccb_start; f_ccb++){
                if(f_ccb->is_ray()){
                    has_ray=true;
                    break;
                }
                CgalVoronoi::Vertex_handle targetV=f_ccb->target();
                tempvertexmap[lastV].push_back(targetV);
                lastV=targetV;
            }

            if(!has_ray){
                face_set.insert(curr->face());
                tempvertexmap[lastV].push_back(sourceV);
                for(map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Vertex_handle> >::iterator mapitr=tempvertexmap.begin();
                        mapitr!=tempvertexmap.end();mapitr++){
                    nextvertex_map[mapitr->first].splice(nextvertex_map[mapitr->first].end(), mapitr->second);
//                    cout<<endl<<"For ("<<mapitr->first->point().x()<<", "<<mapitr->first->point().y()<<"): ";
//                    for(list<CgalVoronoi::Vertex_handle>::iterator litr=nextvertex_map[mapitr->first].begin();
//                            litr!=nextvertex_map[mapitr->first].end();litr++){
//                        cout<<"("<<(*litr)->point().x()<<", "<<(*litr)->point().y()<<") ";
//                    }
                }
//                cout<<"a face not has ray..."<<endl;
            } else{
                polygon.isRay=true;
            }

        }   //end if (face not in face_set)



        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)
    // now also add the vertex for the target of curr

    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
    edge.target = target;
    CgalVoronoi::Vertex_handle sourceV = start->source();
    CgalVoronoi::Vertex_handle targetV = curr->target();
    CgalVoronoi::Vertex_handle last2nd = curr->source();
    edge.obstacleAverage /= edge.pathEdges.size();

    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);

    bool allfacejoined=true;
    int polycnt=0;
    VoriGraphPolygon* faceVGpolygon=0;
    for(std::set<CgalVoronoi::VD::Face_handle>::iterator faceitr=face_set.begin();
            faceitr!=face_set.end();faceitr++){
        if(face_polygon.find(*faceitr)==face_polygon.end()){ //该path上有未处理的face
            allfacejoined=false;
            faceVGpolygon=0;
            break;
        }else{
            if(faceVGpolygon==0) {
                polycnt++;
                faceVGpolygon = face_polygon[*faceitr];
            }else if(faceVGpolygon == face_polygon[*faceitr]){
                polycnt++;
            }else if(allfacejoined){
                cout<<"Strange!! the polygon has two faces belong to defferdent polygon!"<<endl;
            }
        }
    }
    if(!allfacejoined && !face_set.empty()){
        //build the polygon by finding the outline points
        list<CgalVoronoi::Vertex_handle> polygonV_list;
        polygonV_list.splice(polygonV_list.end(),pathVertex);
//        cout<<"path: ";
//        for(list<CgalVoronoi::Vertex_handle>::iterator Vitr=polygonV_list.begin();
//            Vitr!=polygonV_list.end();Vitr++){
//            cout<<"("<<(*Vitr)->point().x()<<", "<<(*Vitr)->point().y()<<")";
//        }
//        cout<<endl;
        list<CgalVoronoi::Vertex_handle> findlist=findOutline(sourceV, last2nd, targetV, nextvertex_map);
        polygonV_list.splice(polygonV_list.end(),findlist);
        cout<<"big face: ";
        for(list<CgalVoronoi::Vertex_handle>::iterator Vitr=polygonV_list.begin();
            Vitr!=polygonV_list.end();Vitr++){
            topo_geometry::point currP((*Vitr)->point().x(),(*Vitr)->point().y());
            polygon.polygonpoints.push_back(currP);
            cout<<"("<<(*Vitr)->point().x()<<", "<<(*Vitr)->point().y()<<")";
        }
        cout<<endl;

        voriGraph.pathFaces.push_back(polygon);
        VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
        assert(polygonPtr != 0);
        edgePtr->pathFace=polygonPtr;
        polygonPtr->belongpaths.push_back(edgePtr);

        for(std::set<CgalVoronoi::VD::Face_handle>::iterator faceitr=face_set.begin();
            faceitr!=face_set.end();faceitr++){
            if(face_polygon.find(*faceitr)!=face_polygon.end()){    //该face曾属于其他polygon
                VoriGraphPolygon* ori_polygon=face_polygon[(*faceitr)];
                for(list<VoriGraphHalfEdge*>::iterator pathitr=ori_polygon->belongpaths.begin();
                        pathitr!=ori_polygon->belongpaths.end();pathitr++){
                    VoriGraphHalfEdge* tempVGpathPtr=(*pathitr);
                    tempVGpathPtr->pathFace=polygonPtr;
                    polygonPtr->belongpaths.push_back(tempVGpathPtr);
                }
            }
            face_polygon[(*faceitr)]=polygonPtr;
        }
    } else if(allfacejoined&& !face_set.empty()){
        //设置该path的pathface为更大的polygon
        edgePtr->pathFace=faceVGpolygon;
        faceVGpolygon->belongpaths.push_back(edgePtr);
    }
    source->markTwins();
}


void createVoriGraphHalfEdgeandVoriGraphPolygon_backup_v2(//version2.0: no same face to join, not join face with ray
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo /*,
        QImage &image*/){

    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标
//    cout<<"start: "<<start->source()->point().x()<<", "<<start->source()->point().y()<<", "
//        <<start->target()->point().x()<<", "<<start->target()->point().y()<<endl;


    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

    std::list<topo_geometry::point> big_point_list;
    std::set<CgalVoronoi::VD::Face_handle> face_set;
    CgalVoronoi::Halfedge_handle curr = start;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        edge.distance += halfedge.length();

        /* Jiawei: save face for each half edge!!! */
        polygon.sites.push_back(obstacleP);
        CgalVoronoi::VD::Face_handle face=curr->face();
        if(face_set.find(curr->face())==face_set.end()){//never add this face
            bool has_ray=false;

            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
            CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
            f_ccb_start=curr->face()->ccb();

            std::list<topo_geometry::point> temppoints; //暂时存face的点，若发现face中有ray则丢弃
            if(f_ccb_start->has_source()) {
                topo_geometry::point sourceP(f_ccb_start->source()->point().x(), f_ccb_start->source()->point().y());
                temppoints.push_back(sourceP);
            }
            for( f_ccb=f_ccb_start; f_ccb->next() != f_ccb_start; f_ccb++){
                if(f_ccb->is_ray()){
                    has_ray=true;
                    break;
                }
                topo_geometry::point targetP(f_ccb->target()->point().x(), f_ccb->target()->point().y());
                temppoints.push_back(targetP);
            }

            if(!has_ray){
                face_set.insert(curr->face());
                big_point_list.splice(big_point_list.end(), temppoints);
            }

        }



        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)
    // now also add the vertex for the target of curr

    polygon.sites.reverse();
    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
// VoriGraphVertex * target = &voriGraph.vertices[curr->target()];
//   target->vertex = curr->target();
    edge.target = target;
    edge.obstacleAverage /= edge.pathEdges.size();

//    //draw the polygon
//    int cnt=0;
//    QPolygon poly;
//    for(std::list<topo_geometry::point>::iterator itr=uppoints.begin();itr!=uppoints.end();itr++){
//        poly<<QPoint(round((*itr).x()),round((*itr).y()));
//        cnt++;
//    }
//    QPainter painter(&image);
//    painter.setBrush(Qt::Dense7Pattern);    //填充
//    painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));  // random color!!!!
//    painter.drawPolygon(poly);

    polygon.polygonpoints=big_point_list;
    voriGraph.pathFaces.push_back(polygon);
    VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
    assert(polygonPtr != 0);
    edge.pathFace=polygonPtr;
    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);
//    polygon.path=edgePtr;


    source->markTwins();
}

void createVoriGraphHalfEdgeandVoriGraphPolygon_backup(     //add polygon point in order
        map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
        VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
        map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo /*,
        QImage &image*/){

    VoriGraphHalfEdge edge;
    VoriGraphPolygon polygon;
    topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
    VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
    // set the distance (don't need for rays ... those will be done for the these edges)
    source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
    source->point = pointCoord;   //该始节点的坐标
//    cout<<"start: "<<start->source()->point().x()<<", "<<start->source()->point().y()<<", "
//        <<start->target()->point().x()<<", "<<start->target()->point().y()<<endl;


    edge.source = source;
    edge.obstacleAverage = 0.;
    edge.obstacleMinimum = numeric_limits<double>::max();

    std::list<topo_geometry::point> uppoints;
    std::list<topo_geometry::point> downpoints;
    CgalVoronoi::Halfedge_handle curr = start;
    while(true){
        //
        topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
        topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
        topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
        topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
        edge.pathEdges.push_back(halfedge);
        edge.distance += halfedge.length();

        /* Jiawei: save face for each half edge!!! */
        polygon.sites.push_back(obstacleP);
        CgalVoronoi::VD::Face_handle face=curr->face();
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
        std::list<topo_geometry::point> tempdown;
        int fcnt=0;
        f_ccb=face->ccb();
        CgalVoronoi::VD::Halfedge_handle e;
        e=f_ccb;
        while((f_ccb->is_ray() || f_ccb->source()!=curr->source()||f_ccb->target()!=curr->target())&&fcnt<100) {
            f_ccb++;
            fcnt++;

        }
        if(fcnt>99)cout<<"strang!! can not find the edge in the face!!"<<endl;  //never happened
//        cout<<"fcnt: "<<fcnt<<endl;
        f_ccb_start=f_ccb;

        bool up=true;
        int f_ccb_cnt=0;
        topo_geometry::point lasttarget(0.0,0.0);
        for(;f_ccb->next()!=f_ccb_start; f_ccb++)
        {
            f_ccb_cnt++;
//            cout<<"enter face edges for..."<<f_ccb_cnt<<endl;
            if(f_ccb->is_ray()){
//                cout<<"a ray!!!!"<<endl;
                continue;
            }
            if(up){
//                if(true ||f_ccb->source()==curr->target()){
                up=false;
                topo_geometry::point sourceP(f_ccb->source()->point().x(), f_ccb->source()->point().y());
                if(sourceP.x()!=uppoints.rbegin()->x()) uppoints.push_back(sourceP);
                topo_geometry::point targetP(f_ccb->target()->point().x(), f_ccb->target()->point().y());
                uppoints.push_back(targetP);
                lasttarget=targetP;
//                }
//                else {
//                    topo_geometry::point sourceP( f_ccb->source()->point().x(), f_ccb->source()->point().y());
//                    uppoints.push_back( sourceP );
//                }
            } else{
                topo_geometry::point sourceP(f_ccb->source()->point().x(), f_ccb->source()->point().y());
                if(sourceP.x()!= lasttarget.x() &&sourceP.x()!=downpoints.begin()->x()) {
                    tempdown.push_front(sourceP);
                }
                topo_geometry::point targetP(f_ccb->target()->point().x(), f_ccb->target()->point().y());
                tempdown.push_front(targetP);
                lasttarget=targetP;
            }

        }
        downpoints.splice(downpoints.end (), tempdown);

        double distToObstacle = halfedge.dist();
        edge.obstacleAverage += distToObstacle;
        if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
        // find all the edges which have the target vertex as source
        //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
        list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
        // only continue if the target vertex as one other (2 because of both dircetions) full edge
        if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
        // make sure we don't go back with the twin (==opposite direction)
        CgalVoronoi::Halfedge_handle next;
        if( (*sourcesForVertex.begin()) != curr->twin()) {
            next = *sourcesForVertex.begin();
        }else{
            next = *sourcesForVertex.rbegin();
        }
        // check if the next is a ray
        if(next->is_ray()){
            break;
        }
        curr = next;

    }// while(true)
    // now also add the vertex for the target of curr

    polygon.sites.reverse();
    topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
    VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
// VoriGraphVertex * target = &voriGraph.vertices[curr->target()];
//   target->vertex = curr->target();
    edge.target = target;
    edge.obstacleAverage /= edge.pathEdges.size();
//    polygon.beforesite=*downpoints.rbegin();
//    polygon.aftersite=*downpoints.begin();
    downpoints.reverse();

    uppoints.splice(uppoints.end(),downpoints);

    //draw the polygon
    int cnt=0;
    QPolygon poly;
    for(std::list<topo_geometry::point>::iterator itr=uppoints.begin();itr!=uppoints.end();itr++){
        poly<<QPoint(round((*itr).x()),round((*itr).y()));
        cnt++;
    }
//    QPainter painter(&image);
//    painter.setBrush(Qt::Dense7Pattern);    //填充
//    painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));  // random color!!!!
//    painter.drawPolygon(poly);

    polygon.polygonpoints=uppoints;
//    polygon.path=edgePtr;
    voriGraph.pathFaces.push_back(polygon);
    VoriGraphPolygon * polygonPtr=&*voriGraph.pathFaces.rbegin();
    assert(polygonPtr != 0);
    edge.pathFace=polygonPtr;
    voriGraph.halfEdges.push_back(edge);
    VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
    assert(edgePtr != 0);
    target->edgesConnected.push_back(edgePtr);
    source->edgesConnected.push_back(edgePtr);


    source->markTwins();
}

void createVoriGraphHalfEdge(map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > &vertexSourceMap,
                             VoriGraph &voriGraph, CgalVoronoi::Halfedge_handle start,
                             map<CgalVoronoi::Halfedge_handle, double> &halvesDistanceInfo){
  VoriGraphHalfEdge edge;
  topo_geometry::point pointCoord(start->source()->point().x(), start->source()->point().y());
  VoriGraphVertex * source = &voriGraph.vertices[pointCoord];   //Halfedge的始节点指针，即该节点本身的指针
//   voriGraph.verticesList.push_back(VoriGraphVertex());
//   VoriGraphVertex * source = &*voriGraph.rbegin();
  //   source->vertex = start->source();
  // set the distance (don't need for rays ... those will be done for the these edges)
  source->obstacleDist = halvesDistanceInfo[start]; //获取该始节点的Halfedge与障碍点距离
  source->point = pointCoord;   //该始节点的坐标
//   cout<<" p "<<topo_geometry::print(pointCoord)<<endl;
  
  edge.source = source;
  edge.obstacleAverage = 0.;
  edge.obstacleMinimum = numeric_limits<double>::max();
  CgalVoronoi::Halfedge_handle curr = start;
  while(true){
    //
    topo_geometry::point sourceP(curr->source()->point().x(), curr->source()->point().y());
    topo_geometry::point targetP(curr->target()->point().x(), curr->target()->point().y());
    topo_geometry::point obstacleP(curr->face()->dual()->point().x(), curr->face()->dual()->point().y());
    topo_geometry::Halfedge halfedge(sourceP, targetP, obstacleP, halvesDistanceInfo[curr]);
      /* Jiawei: save face for each half edge!!! */
    edge.pathEdges.push_back(halfedge);
    edge.distance += halfedge.length();


    //
//     edge.halfEdges.push_back(curr);
    double distToObstacle = halfedge.dist();
    edge.obstacleAverage += distToObstacle;
    if(distToObstacle < edge.obstacleMinimum) edge.obstacleMinimum = distToObstacle;
    // find all the edges which have the target vertex as source
      //sourcesForVertex：以这条Halfedge的终结点为始节点的所有Halfedge
    list<CgalVoronoi::Halfedge_handle> &sourcesForVertex = vertexSourceMap[curr->target()];
    // only continue if the target vertex as one other (2 because of both dircetions) full edge
    if(sourcesForVertex.size() != 2) break; //该节点须连接两条短边（本边curr和下一条边next）
    // make sure we don't go back with the twin (==opposite direction)
    CgalVoronoi::Halfedge_handle next;
    if( (*sourcesForVertex.begin()) != curr->twin()) {
      next = *sourcesForVertex.begin();
    }else{
      next = *sourcesForVertex.rbegin();
    }
    // check if the next is a ray
    if(next->is_ray()){
      break;
    }
    curr = next;

  }// while(true)
  // now also add the vertex for the target of curr
  

  topo_geometry::point pointCoordTarget(curr->target()->point().x(), curr->target()->point().y());
  VoriGraphVertex * target = &voriGraph.vertices[pointCoordTarget];
// VoriGraphVertex * target = &voriGraph.vertices[curr->target()];
//   target->vertex = curr->target();
  edge.target = target;
  edge.obstacleAverage /= edge.pathEdges.size();
  voriGraph.halfEdges.push_back(edge);
  VoriGraphHalfEdge * edgePtr = &*voriGraph.halfEdges.rbegin();
  assert(edgePtr != 0);
//  createVoriGraphPolygon(edgePtr,voriGraph);
  target->edgesConnected.push_back(edgePtr);
  source->edgesConnected.push_back(edgePtr);

  source->markTwins();
}


void generateVoriGraph(CgalVoronoi::VD &pVd, map<CgalVoronoi::Halfedge_handle, double> &halves, VoriGraph &voriGraph){
  // count the number of filtered cgal half edges connected to the vertices
  map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > vertexTargetMap; //存作为终节点的vertex及以该节点为终结点的所有Halfedge
  map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> > vertexSourceMap; //存作为始节点的vertex及以该节点为始节点的所有Halfedge
  map<CgalVoronoi::Halfedge_handle, double>::iterator itr;
  for(itr = halves.begin(); itr != halves.end(); ++itr){
    if( itr->first->has_target()) vertexTargetMap[itr->first->target()].push_back(itr->first);
    if( itr->first->has_source()) vertexSourceMap[itr->first->source()].push_back(itr->first);
  }

  // now go trough all vertices found
  // vertices with source# (==target#) of 2 are within of a new VoriGraphHalfEdge and ignored here
  // vertices with source# 1 (dead end) or 3 or 4 ... (junction) create a new VoriGraphHalfEdge
  map<CgalVoronoi::Vertex_handle, list<CgalVoronoi::Halfedge_handle> >::iterator mapItr;
  for(mapItr = vertexSourceMap.begin(); mapItr != vertexSourceMap.end(); ++mapItr){
    if(mapItr->second.size() == 2){ //以此节点为始节点的有两条边而且这两条边都不是射线，则跳过处理
      // we skip through all which are not a junction, dead end or invlove a ray because they will be joined together during half edge creation
      if( (! (*mapItr->second.begin())->is_ray()) && (! (*mapItr->second.rbegin())->is_ray()) ) continue;
    }
    list<CgalVoronoi::Halfedge_handle>::iterator sourceItr;
    for(sourceItr = mapItr->second.begin(); sourceItr != mapItr->second.end(); ++sourceItr){
      if( (*sourceItr)->is_ray()){
        createVoriGraphHalfEdgesForRay(pVd, vertexSourceMap, voriGraph, *sourceItr);
      }else{
//        createVoriGraphHalfEdge(vertexSourceMap, voriGraph, *sourceItr, halves);
          createVoriGraphHalfEdgeandVoriGraphPolygon(vertexSourceMap, voriGraph, *sourceItr, halves);
      }
    }
  }
  // calculate the distances for the vertices:
  VoriGraph::VertexMap::iterator itrVertices;
  for(itrVertices = voriGraph.vertices.begin(); itrVertices != voriGraph.vertices.end(); ++itrVertices){    //遍历VoriGraph中每个节点
    double minDist = numeric_limits<double>::max();
    for(list<VoriGraphHalfEdge *>::iterator itrEdges = itrVertices->second.edgesConnected.begin(); itrEdges != itrVertices->second.edgesConnected.end(); ++itrEdges)
    {
//       if( (*itrEdges)->isRay() )
      if( (*itrEdges)->source == &itrVertices->second ){
//         double dist = halves[*(*itrEdges)->halfEdges.begin()];
        double dist = (*itrEdges)->pathEdges.begin()->dist();
        if(dist < minDist) minDist = dist;
      }else if( (*itrEdges)->target == &itrVertices->second ){
//         double dist = halves[*(*itrEdges)->halfEdges.rbegin()];
        double dist = (*itrEdges)->pathEdges.begin()->dist();
        if(dist < minDist) minDist = dist;
      }
    }
    itrVertices->second.obstacleDist = minDist;
  }
  voriGraph.markDeadEnds();
  cout<<" Done creating VoriGraph. Vertices: "<<voriGraph.vertices.size()<<" halfEdges: "<< voriGraph.halfEdges.size()<<endl;
}
#define EDGE_MINLEN 3.0
void filterForDist(CgalVoronoi::VD &pVd, std::map<CgalVoronoi::Halfedge_handle, double> &pResult, double pMinDistance) {
    //把与点距离的平方>pMinDistance的Halfedge及其与点距离存进pResult里
    double squaredMinDist = pMinDistance * pMinDistance;
    CgalVoronoi::VD::Halfedge_iterator halfedgeItr = pVd.halfedges_begin();
    for (; halfedgeItr != pVd.halfedges_end(); halfedgeItr++) {
        CgalVoronoi::Halfedge_handle hh = *halfedgeItr;
        if (hh->has_source() && hh->has_target()) {
            // we might be interested in this - check the dist to the vertex of the face
            CgalVoronoi::VD::Face::Delaunay_vertex_handle delaunayVertexHandle = hh->face()->dual();  //Halfedge->face())->dual(): 该半边的面中对应的delaunay三角形里的点
            CGAL::Segment_2<CgalVoronoi::K> segment( hh->source()->point(), hh->target()->point());
            CgalVoronoi::K::FT distsq = squared_distance( segment, delaunayVertexHandle->point());
            if (distsq > squaredMinDist) {
                pResult[hh] = sqrt( distsq );
            }
        } else if (hh->is_ray()) {
            // also take infinity edges - this is a ray...

            CGAL::Ray_2<CgalVoronoi::K> ray;
            bool isRay = (CGAL::assign( ray, pVd.dual().dual( hh->dual())));
            if (isRay) {
                // we might be interested in this - check the dist to the vertex of the face
                CgalVoronoi::VD::Face::Delaunay_vertex_handle delaunayVertexHandle = hh->face()->dual();
                CgalVoronoi::K::FT dist = squared_distance( ray, delaunayVertexHandle->point());
                if (dist > squaredMinDist) {
                    pResult[hh] = sqrt( dist );
                }
            }
        }
    }
}
void paintdelface(QImage &image){
//    cout<<"enter panintdelface ...";
    QPainter painter(&image);
    image.fill(qRgba(255, 255, 255, 255));
    int cnt=0;
    set<CgalVoronoi::VD::Face_handle>::iterator fitr=delface_set.begin();
    for(;fitr!=delface_set.end();fitr++){
//        topo_geometry::point site((*fitr)->dual()->point().x(),(*fitr)->dual()->point().y());
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
        f_ccb_start = (*fitr)->ccb();
        QPolygon poly;
        poly  << QPoint(round( f_ccb_start->source()->point().x()), round( f_ccb_start->source()->point().y()));
        for (f_ccb = f_ccb_start; f_ccb->next() != f_ccb_start; f_ccb++) {
            CgalVoronoi::VD::Halfedge_handle e;
            e = f_ccb;
            int x1=round( e->target()->point().x());
            int y1=round( e->target()->point().y());
            poly  << QPoint(x1, y1);
        }
        QBrush brush;
        QColor color = QColor( rand() % 255, rand() % 255, rand() % 255 );
        brush.setColor( color );
        brush.setStyle( Qt::SolidPattern );
        painter.setBrush( brush );
        painter.setPen( color );  // random color!!!!
        if(poly.size()>2){
//            cout<<"draw "<<cnt++<<"th polygon"<<endl;
            painter.drawPolygon(poly);
        }
    }
}

void paintVori_face(QImage &image, map<CgalVoronoi::Halfedge_handle, double> &halves,
                    std::vector<topo_geometry::point> sites){

//     image = image.convertToFormat(QImage::Format_ARGB32);
     image.fill(qRgba(255, 255, 255, 255));
    QPainter painter(&image);
    set<CgalVoronoi::Face_handle> faceset;

    unsigned int county = 0;
    map<CgalVoronoi::Halfedge_handle, double>::iterator itr;
//    cout<<"halves size: "<< halves.size()<<endl;
    for(itr = halves.begin(); itr != halves.end(); ++itr){
        if(faceset.find(itr->first->face())==faceset.end() || itr==halves.begin()){
            faceset.insert(itr->first->face());
        } else{
            continue;
        }

        county++;
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb_start;
        CgalVoronoi::VD::Ccb_halfedge_circulator f_ccb;
        f_ccb=itr->first->face()->ccb();
        int h_cnt=0;
        QPolygon poly;
//
//        cout<<"face No."<<county<<" for halfedge "
//            <<"("<<itr->first->source()->point().x()<<", "<<itr->first->source()->point().y()<<") - "
//            <<"("<<itr->first->target()->point().x()<<", "<<itr->first->target()->point().y()<<")"
//            <<": ";
        if(f_ccb->has_source()){
            poly  << QPoint(( f_ccb->source()->point().x()), ( f_ccb->source()->point().y()));
        }

        for( f_ccb_start=f_ccb; f_ccb->next() != f_ccb_start; f_ccb++) {   //遍历face的边
            CgalVoronoi::VD::Halfedge_handle e;
            e = f_ccb;

            if (!e->is_ray()) {
                int x1=( e->target()->point().x());
                int y1=( e->target()->point().y());
                poly  << QPoint(x1, y1);
//                    cout<<e->target()->point().x()<<", "<< e->target()->point().y()<<"; ";
                h_cnt++;
            } else{
                //不画射线的边
//                 cout<<"a ray!!!!"<<endl;
//                 int x1, y1;
//                 if (e->has_source()) {
//                     x1 = round( e->source()->point().x());
//                     y1 = round( e->source()->point().y());
//                 } else {
//                     x1 = round( e->target()->point().x());
//                     y1 = round( e->target()->point().y());
//                 }
//                 poly << QPoint( x1, y1 );
//                 h_cnt++;
//                 CGAL::Ray_2<CgalVoronoi::K> ray;
//                 bool isRay = (CGAL::assign( ray, pVd.dual().dual( e->dual())));
//                 if (isRay) {
//                     CgalVoronoi::Point_2 p = ray.point( 10 );
//                     int x2 = round( p.x());
//                     int y2 = round( p.y());
//                     poly << QPoint( x2, y2 );
//                     h_cnt++;
//                    }
            }
        }//for
//        cout<<endl;
//            cout<<"face "<<county<<": "<<h_cnt<<endl;
        QBrush brush;
        QColor color = QColor( rand() % 255, rand() % 255, rand() % 255 );
        brush.setColor( color );
        brush.setStyle( Qt::SolidPattern );
        painter.setBrush( brush );
        painter.setPen( color );  // random color!!!!
        if(poly.size()>2){
            painter.drawPolygon(poly);
        }

//        image.save("face.png");
//        }// is (not) ray


    }// for voriGraph.halfEdges
    painter.setPen(qRgb(0,0,0));
    for(vector<topo_geometry::point>::const_iterator itr = sites.begin(); itr != sites.end(); ++itr){
        QPointF pt(topo_geometry::getX(*itr), topo_geometry::getY(*itr));
        painter.drawPoint(pt);
    }
}
void paintVoronoi(QImage &image, CgalVoronoi::VD & vd){

    QPainter painter(&image);

    unsigned int county = 0;
    CgalVoronoi::VD::Halfedge_iterator halfedgeItr =  vd.halfedges_begin ();
    for( ; halfedgeItr != vd.halfedges_end(); halfedgeItr++, county++){
//        cout<<"try Painter!!!"<<endl;
//         print_endpoint(*halfedgeItr, true);
//         print_endpoint(*halfedgeItr, false);
//         cout<<" ----- "<<endl;
        CgalVoronoi::Halfedge_handle hh = *halfedgeItr;
        if(hh->has_source() && hh->has_target()){
          int x1 = (round(hh->source()->point().x()));
          int y1 = (round(hh->source()->point().y()));
          int x2 = (round(hh->target()->point().x()));
          int y2 = (round(hh->target()->point().y()));
          painter.setPen(Qt::red);
          painter.drawLine(x1, y1, x2, y2);
        }
         if(hh->is_ray()){
//           cout<<"painty raiy"<<endl;
           int x, y;
           if(hh->has_source()){
             x = round(hh->source()->point().x());
             y = round(hh->source()->point().y());
           }else{
             x = round(hh->target()->point().x());
             y = round(hh->target()->point().y());
           }
           CGAL::Ray_2<CgalVoronoi::K> ray;
           bool isRay = ( CGAL::assign( ray, vd.dual().dual(hh->dual() ) ) );
           if(isRay){
             CgalVoronoi::Point_2 p = ray.point(20);
             int x2 = round(p.x());
             int y2 = round(p.y());
             painter.setPen(Qt::green);
             painter.drawLine(x, y, x2, y2);
//             cout<<" ray "<<x<<" "<<(round(ray.source().x()))<<"   "<<y<<" "<<(round(ray.source().y()))<<"    "<<x2<<" "<<y2<<endl;
           }
         }

    }
//     CgalVoronoi::VD::Unbounded_halfedges_iterator unBItr =  vd.unbounded_halfedges_begin ();
//     for( ; unBItr != vd.unbounded_halfedges_end(); unBItr++){
//         CgalVoronoi::Halfedge_handle hh = *unBItr;
//         if(hh->is_ray()){
//           cout<<"painty raiy"<<endl;
//           int x, y;
//           if(hh->has_source()){
//             x = round(hh->source()->point().x());
//             y = round(hh->source()->point().y());
//           }else{
//             x = round(hh->target()->point().x());
//             y = round(hh->target()->point().y());
//           }
//           CGAL::Ray_2<CgalVoronoi::K> ray;
//           bool isRay = ( CGAL::assign( ray, vd.dual().dual(hh->dual() ) ) );
//           if(isRay){
//             CgalVoronoi::Point_2 p = ray.point(200);
//             int x2 = round(p.x());
//             int y2 = round(p.y());
//             painter.setPen(Qt::red);
//             painter.drawLine(x, y, x2, y2);
//             cout<<" ray "<<x<<" "<<(round(ray.source().x()))<<"   "<<y<<" "<<(round(ray.source().y()))<<"    "<<x2<<" "<<y2<<endl;
//           }
//         }
//     }

    cout<<"count Halfedge_iterator: "<<county<<endl;
    CgalVoronoi::VD::Edge_iterator edgeItr =  vd.edges_begin ();
    for(county = 0; edgeItr != vd.edges_end(); edgeItr++, county++){
    }
    cout<<"count Edge_iterator: "<<county<<endl;
    CgalVoronoi::VD::Face_iterator faceItr =  vd.faces_begin ();
    for(county = 0; faceItr != vd.faces_end(); faceItr++, county++){
    }
    cout<<"count Face_iterator: "<<county<<endl;
}

void paintVoronoi(CgalVoronoi::VD &pVd, QImage &image, map<CgalVoronoi::Halfedge_handle, double> &list){

    image = image.convertToFormat(QImage::Format_ARGB32);
    image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);

    unsigned int county = 0;
    map<CgalVoronoi::Halfedge_handle, double>::iterator halfedgeItr =  list.begin ();
    for( ; halfedgeItr != list.end(); halfedgeItr++, county++){
//         print_endpoint(*halfedgeItr, true);
//         print_endpoint(*halfedgeItr, false);
//         cout<<" ----- "<<endl;
        CgalVoronoi::Halfedge_handle hh = halfedgeItr->first;
        if(hh->has_source() && hh->has_target()){
          int x1 = (round(hh->source()->point().x()));
          int y1 = (round(hh->source()->point().y()));
          int x2 = (round(hh->target()->point().x()));
          int y2 = (round(hh->target()->point().y()));
          painter.setPen(Qt::red);
          painter.drawLine(x1, y1, x2, y2);
        }else if(hh->is_ray()){
          painter.setPen(Qt::green);
          CGAL::Ray_2<CgalVoronoi::K> ray;
          bool isRay = ( CGAL::assign( ray, pVd.dual().dual(hh->dual() ) ) );
          if(!isRay){
            cerr<<"Really starnge error - cannot cast to ray!"<<endl;
          }
          int x1 = (round(ray.source().x()));
          int y1 = (round(ray.source().y()));
          CgalVoronoi::Point_2 p = ray.point(200);
          int x2 = round(p.x());
          int y2 = round(p.y());
          painter.drawLine(x1, y1, x2, y2);

        }
    }
}




void removeOutsidePolygon(VoriGraph &voriGraph, CGAL::Polygon_2<CgalVoronoi::K> &polygon){
  for(std::list<VoriGraphHalfEdge>::iterator itr = voriGraph.halfEdges.begin(); itr != voriGraph.halfEdges.end();){
    bool targetOutside = false;
    bool sourceOutside = false;
    if( itr->target){
      CgalVoronoi::Point_2 p(topo_geometry::getX(itr->target->point), topo_geometry::getY(itr->target->point));
      //       CgalVoronoi::Point_2 p = itr->target->vertex->point();
      if(polygon.bounded_side(p) == CGAL::ON_UNBOUNDED_SIDE){
        targetOutside = true;
      }
    }
    if( itr->source){
      CgalVoronoi::Point_2 p(topo_geometry::getX(itr->source->point), topo_geometry::getY(itr->source->point));
//       CgalVoronoi::Point_2 p = itr->source->vertex->point();
      if(polygon.bounded_side(p) == CGAL::ON_UNBOUNDED_SIDE){
        // remove it
        sourceOutside = true;
      }
    }
    // delete if both are outside or if it is a ray and (the only) point is outside
    if( (targetOutside && sourceOutside) || (itr->isRay() && (targetOutside || sourceOutside)) ){
        itr = voriGraph.removeHalfEdge_jiawei(itr);
        continue;
    }else{

      if(targetOutside){
        //convert to a ray!
//         itr->ray = CGAL::Ray_2<CgalVoronoi::K>(ps, pt);
	itr->topo_ray = topo_geometry::Halfedge(itr->source->point, itr->target->point, itr->source->point, itr->obstacleMinimum, true);
        itr->target->removeHalfEdge(&*itr);
        if(itr->target->edgesConnected.empty()){
          voriGraph.vertices.erase(itr->target->point);
        }
        itr->target = 0;
      }
      if(sourceOutside){
        //convert to a ray!
//         itr->ray = CGAL::Ray_2<CgalVoronoi::K>(pt, ps);

	itr->topo_ray = topo_geometry::Halfedge(itr->target->point, itr->source->point, itr->target->point, itr->obstacleMinimum, true);
        itr->source->removeHalfEdge(&*itr);
        if(itr->source->edgesConnected.empty()){
          voriGraph.vertices.erase(itr->source->point);
        }
        itr->source = 0;
      }
    }
    ++itr;
  }// for
}



