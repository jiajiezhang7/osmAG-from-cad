#include "qt/QImageVoronoi.h"


#include <cstdlib>
#include <string>
using namespace std;


void calcCoordinates(const unsigned int &x, const unsigned int &y, double &outX, double &outY){
  outX = static_cast<double>(x);
  outY = static_cast<double>(y);
}



void analyseImage(QImage &pImg, bool &pIsTriple){
    pIsTriple = true;
    unsigned int height = pImg.height();
    if(pImg.format()==QImage::Format_RGB32 || pImg.format()==QImage::Format_ARGB32){
        qDebug()<<"32 bit analyse";
        for(unsigned int y=0; y < height; y++){
            //progress Bar:
//             emit analyzing(100.*double(y)/height);
            // do the stuff...
            QRgb* pointer = (QRgb*)pImg.scanLine(y);
            QRgb* endP = pointer + pImg.width();
            for( ; pointer<endP; pointer++){
                int red = qRed(*pointer);
                int green = qGreen(*pointer);
                int blue = qBlue(*pointer);
                if(!(red == FREE || red == UNKNOWN || red == OCCUPIED)) pIsTriple = false;
                if(!(green == FREE || green == UNKNOWN || green == OCCUPIED)) pIsTriple = false;
                if(!(blue == FREE || blue == UNKNOWN || blue == OCCUPIED)) pIsTriple = false;
                if(!pIsTriple){
//                     emit analyzing(100);
                            return;
                }
            }
        }
    }else if(pImg.format()==QImage::Format_RGB888){
        qDebug()<<"24 bit analyse";
        for(unsigned int y=0; y < height; y++){
            //progress Bar:
//             emit analyzing(100.*double(y)/height);
//             QCoreApplication::processEvents( QEventLoop::ExcludeUserInputEvents );
            // do the stuff...
            uchar* pointer = pImg.scanLine(y);
            uchar* endP = pointer + pImg.width()*3;
            for( ; pointer<endP; ){
                uchar red = *pointer++;
                uchar green = *pointer++;
                uchar blue = *pointer++;
                if(!(red == FREE || red == UNKNOWN || red == OCCUPIED)) pIsTriple = false;
                if(!(green == FREE || green == UNKNOWN || green == OCCUPIED)) pIsTriple = false;
                if(!(blue == FREE || blue == UNKNOWN || blue == OCCUPIED)) pIsTriple = false;
                if(!pIsTriple){
//                   emit analyzing(100);
                  return;
                }
            }
        }
    }else{
        qDebug()<<"unsupported image format while analyzing...";
    }
//     emit analyzing(100);
}



bool getSites(QImage &pImg, std::vector<topo_geometry::point> &sites){
    unsigned int counter = 0;
    double outX, outY;
    unsigned int height = pImg.height();

    if(pImg.format()==QImage::Format_RGB32 || pImg.format()==QImage::Format_ARGB32){
        cerr<<"32 bit analyse"<<endl;
        for(unsigned int y=0; y < height; y++){
            //progress Bar:
//             emit converting(100.*double(y)/height);
//             cout<<"Progress : "<<QString::number(((100.*double(y)/height))).toStdString()<<endl;
            // do the stuff...
            QRgb* pointer = (QRgb*)pImg.scanLine(y);
            QRgb* endP = pointer + pImg.width();

            for(unsigned int x = 0; pointer<endP; pointer++, x++){
              int red = qRed(*pointer);
              if(red == OCCUPIED){
                // this is a point
                calcCoordinates(x, y, outX, outY);
                sites.push_back(topo_geometry::point(outX, outY));
                counter++;
              }
            }
        }
    }else if(pImg.format()==QImage::Format_RGB888){
        qDebug()<<"24 bit analyse";
        for(unsigned int y=0; y < height; y++){
            //progress Bar:
//             emit converting(100.*double(y)/height);
//             cout<<"Progress : "<<QString::number(((100.*double(y)/height))).toStdString()<<endl;
//             QCoreApplication::processEvents( QEventLoop::ExcludeUserInputEvents );
            // do the stuff...
            uchar* pointer = pImg.scanLine(y);
            uchar* endP = pointer + pImg.width()*3;
            for(unsigned int x = 0; pointer<endP; pointer += 3, x++){
                uchar red = *pointer;
              if(red == OCCUPIED){
                // this is a point
                calcCoordinates(x, y, outX, outY);
                sites.push_back(topo_geometry::point(outX, outY));
                counter++;
              }
            }
        }
    }else{
        qDebug()<<"unsupported image format while analyzing...";
        return false;
    }
    return true;
}

// void paintVori(QImage &image, VoriGraph &voriGraph){
// 
//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
//     QPainter painter(&image);
// 
// 
//     unsigned int county = 0;
// 
//     std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;  ;
//     for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
//       county++;
//       if(voriHalfEdgeItr->isRay()){
//         painter.setPen(qRgb(0,255,0));
//         int x1 = (round(voriHalfEdgeItr->ray.source().x()));
//         int y1 = (round(voriHalfEdgeItr->ray.source().y()));
//         CgalVoronoi::Point_2 p = voriHalfEdgeItr->ray.point(200);
//         int x2 = round(p.x());
//         int y2 = round(p.y());
//         painter.drawLine(x1, y1, x2, y2);
//       }else{
//         if(voriHalfEdgeItr->deadEnd){
//           painter.setPen(qRgb(0,255,255));
//         }else{
//           painter.setPen(qRgb(0,0,255));
//         }
//         std::list<CgalVoronoi::Halfedge_handle>::iterator halfedgeItr =  voriHalfEdgeItr->halfEdges.begin ();
//         for( ; halfedgeItr != voriHalfEdgeItr->halfEdges.end(); halfedgeItr++, county++){
//     //         print_endpoint(*halfedgeItr, true);
//     //         print_endpoint(*halfedgeItr, false);
//     //         cout<<" ----- "<<endl;
//             CgalVoronoi::Halfedge_handle hh = *halfedgeItr;
//             if(hh->has_source() && hh->has_target()){
//               int x1 = (round(hh->source()->point().x()));
//               int y1 = (round(hh->source()->point().y()));
//               int x2 = (round(hh->target()->point().x()));
//               int y2 = (round(hh->target()->point().y()));
//               painter.drawLine(x1, y1, x2, y2);
//             }
//         }//for
//       }// is (not) ray
//       painter.setPen(qRgb(255,0,255));
//       if(!voriHalfEdgeItr->isRay()){
//         VoriGraphVertex * source = voriHalfEdgeItr->source;
//         if(source) painter.drawPoint(round(voriHalfEdgeItr->source->vertex->point().x()), round(voriHalfEdgeItr->source->vertex->point().y()));
//         if(voriHalfEdgeItr->target) painter.drawPoint(round(voriHalfEdgeItr->target->vertex->point().x()), round(voriHalfEdgeItr->target->vertex->point().y()));
// 
// 
//       }
//     }// for
// 
// 
//     for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
//       if(!voriHalfEdgeItr->isRay()){
//         VoriGraphVertex * source = voriHalfEdgeItr->source;
//         painter.setPen(qRgb(255,255,0));
// 
//         if(source){
//           CgalVoronoi::Point_2 p;
//           if(voriHalfEdgeItr->getPointForDistance(5, p)){
//             painter.drawPoint(round(p.x()), round(p.y()));
//           }
// /*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
//             painter.drawPoint(round(p.x()), round(p.y()));
//           }
//           if(voriHalfEdgeItr->getPointForDistance(9, p)){
//             painter.drawPoint(round(p.x()), round(p.y()));
//           }*/
//         }
//       }      
//     }
// }
//

void paintVori(QImage &image, VoriGraph &voriGraph){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);


    unsigned int county = 0;

    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;  ;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{
            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();

            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边

                //         print_endpoint(*halfedgeItr, true);
                //         print_endpoint(*halfedgeItr, false);
                //         cout<<" ----- "<<endl;
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}

//void paintVori(QImage &image, VoriGraph &voriGraph){
//
////     image = image.convertToFormat(QImage::Format_ARGB32);
////     image.fill(qRgba(0, 0, 0, 0));
//    QPainter painter(&image);
//
//
//    unsigned int county = 0;
//
//    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;  ;
//    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
//      county++;
//      if(voriHalfEdgeItr->isRay()){ //射线：绿色
//        painter.setPen(qRgb(0,255,0));
//	int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
//	int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
//	int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
//	int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
//	painter.drawLine(x1, y1, x2, y2);
//        painter.drawLine(x1, y1, x2, y2);
//      }else{
//        if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
//          painter.setPen(qRgb(0,255,255));
//        }else{
//          painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
//        }
//
//        std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
//
//        for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
//
//    //         print_endpoint(*halfedgeItr, true);
//    //         print_endpoint(*halfedgeItr, false);
//    //         cout<<" ----- "<<endl;
//            const topo_geometry::Halfedge &he = *pathEdgeItr;
//	    int x1 = (round(topo_geometry::getX(he.s())));
//	    int y1 = (round(topo_geometry::getY(he.s())));
//	    int x2 = (round(topo_geometry::getX(he.t())));
//	    int y2 = (round(topo_geometry::getY(he.t())));
//	    painter.drawLine(x1, y1, x2, y2);
//        }//for
//      }// is (not) ray
//      painter.setPen(qRgb(255,0,255));
//
//      if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色
//
//        if(voriHalfEdgeItr->source){
//	  painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
//	  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
//	}
//        if(voriHalfEdgeItr->target){
//	  painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
//	}
//
//
//      }
//    }// for voriGraph.halfEdges
//
//
//    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
//      if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
//        VoriGraphVertex * source = voriHalfEdgeItr->source;
//        painter.setPen(qRgb(255,255,0));
//
//        if(source){
//          topo_geometry::point p;
//          if(voriHalfEdgeItr->getPointForDistance(5, p)){
//            painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
//          }
///*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
//            painter.drawPoint(round(p.x()), round(p.y()));
//          }
//          if(voriHalfEdgeItr->getPointForDistance(9, p)){
//            painter.drawPoint(round(p.x()), round(p.y()));
//          }*/
//        }
//      }
//    }
//}

void paintVori_randomcolor(QImage &image, VoriGraph &voriGraph){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);


    unsigned int county = 0;

    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;  ;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{
            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();

            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边

                //         print_endpoint(*halfedgeItr, true);
                //         print_endpoint(*halfedgeItr, false);
                //         cout<<" ----- "<<endl;
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}
void paintVori_Area(QImage &image, VoriGraph &voriGraph){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);

    unsigned int county = 0;

    std::set<VoriGraphHalfEdge *> drawnHalfEdge;
    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{
            if(drawnHalfEdge.find(&*voriHalfEdgeItr)==drawnHalfEdge.end()){
                drawnHalfEdge.insert(&*voriHalfEdgeItr);
                QBrush brush;
                QColor color = QColor( rand() % 255, rand() % 255, rand() % 255 );
                brush.setColor( color );
                brush.setStyle( Qt::SolidPattern );
                painter.setBrush( brush );
                painter.setPen( color );  // random color!!!!

                if(voriHalfEdgeItr->pathEdges.size()==0) cout<<"voriHalfEdgeItr->pathEdges.size()==0"<<endl;

                VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
                if(polygonPtr != 0 /*&& polygonPtr->isRay*/) {
                    //                cout<<"polygonPtr != 0 && polygonPtr->isRay"<<endl;
                    QPolygon poly;
                    for (std::list<topo_geometry::point>::iterator pointitr = polygonPtr->polygonpoints.begin();
                         pointitr != polygonPtr->polygonpoints.end(); pointitr++) {
                        int x = round( topo_geometry::getX( *pointitr ));
                        int y = round( topo_geometry::getY( *pointitr ));

                        poly << QPoint( x, y );
                    }
                    painter.drawPolygon( poly );

                    VoriGraphHalfEdge * twinHalfedge=voriHalfEdgeItr->twin;
                    if(voriHalfEdgeItr->twin) {
                        if(twinHalfedge->pathEdges.size()==0) cout<<"twinHalfedge->pathEdges.size()==0"<<endl;

//                        cout<<" path: ("<<voriHalfEdgeItr->source->point.x() <<", "<<voriHalfEdgeItr->source->point.y()
//                            <<")-->("<<voriHalfEdgeItr->target->point.x() <<", "<<voriHalfEdgeItr->target->point.y()<<endl;
//                        cout<<" tpath: ("<<twinHalfedge->source->point.x() <<", "<<twinHalfedge->source->point.y()
//                            <<")-->("<<twinHalfedge->target->point.x() <<", "<<twinHalfedge->target->point.y()<<endl;
                        drawnHalfEdge.insert( twinHalfedge );
                        VoriGraphPolygon *twinpolygonPtr = twinHalfedge->pathFace;
                        if (twinHalfedge->pathFace&& !twinHalfedge->pathFace->polygonpoints.empty()) {
//                            cout<<twinHalfedge->pathFace<<endl;
//                            cout<<twinHalfedge->pathFace->polygonpoints.size()<<endl;
                            QPolygon twin_poly;
                            for (std::list<topo_geometry::point>::iterator pointitr = twinpolygonPtr->polygonpoints.begin();
                                 pointitr != twinpolygonPtr->polygonpoints.end(); pointitr++) {
                                int x = round( topo_geometry::getX( *pointitr ));
                                int y = round( topo_geometry::getY( *pointitr ));
                                twin_poly << QPoint( x, y );
                            }
//                            QColor color2 = QColor( rand() % 255, rand() % 255, rand() % 255 );
//                            brush.setColor( color2 );
//                            brush.setStyle( Qt::Dense7Pattern );
//                            painter.setBrush( brush );
//                            painter.setPen( color2 );  // random color!!!!
                            painter.drawPolygon( twin_poly );
                        }
                    }
                }
            }

            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}

void paintVori_vertex(QImage &image, VoriGraph &voriGraph){
    QPainter painter(&image);
    QPen pen ;
    pen.setWidth(11);
    pen.setColor(qRgb(255,255, 255));
    QPen pen1 ;
    pen1.setWidth(5);
    pen1.setColor(qRgb(0,255, 255));
    QPen pen2 ;
    pen2.setWidth(5);
    pen2.setColor(qRgb(255,0,0));

    unsigned int county = 0;
    VoriGraph::VertexMap::iterator voriHalfVertexItr;
    for(voriHalfVertexItr=voriGraph.vertices.begin();voriHalfVertexItr!=voriGraph.vertices.end();++voriHalfVertexItr){
        double x,y;
        x=voriHalfVertexItr->first.x();
        y=voriHalfVertexItr->first.y();
        if(voriHalfVertexItr->second.isBorderVertex()){
            painter.setPen(pen);
            painter.drawPoint((int)x,(int)y);

        }
//        if(voriHalfVertexItr->second.isRoomVertex()){
//            painter.setPen(pen1);
//            painter.drawPoint((int)x,(int)y);
//
//        }
//        if(voriHalfVertexItr->second.isPassageVertex()){
//            painter.setPen(pen2);
//            painter.drawPoint((int)x,(int)y);
//
//        }
    }



}


void paintVori_AreaRoom(QImage &image, VoriGraph &voriGraph){

    QPainter painter(&image);
//    cout<<"enter paintVori_AreaRoom() ..........."<<endl;

    unsigned int county = 0;

    std::set<VoriGraphHalfEdge *> drawnHalfEdge;
    std::map<int, QColor> roomColor;
    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{
            if(drawnHalfEdge.find(&*voriHalfEdgeItr)==drawnHalfEdge.end()){
                drawnHalfEdge.insert(&*voriHalfEdgeItr);
                QBrush brush;
                QColor color = QColor( rand() % 255, rand() % 255, rand() % 255 );
                brush.setColor( color );
                brush.setStyle( Qt::SolidPattern );
                painter.setBrush( brush );
                painter.setPen( color );  // random color!!!!

                VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
                if(polygonPtr != 0) {
                    QPolygon poly;
                    for (std::list<topo_geometry::point>::iterator pointitr = polygonPtr->polygonpoints.begin();
                         pointitr != polygonPtr->polygonpoints.end(); pointitr++) {
                        int x = round( topo_geometry::getX( *pointitr ));
                        int y = round( topo_geometry::getY( *pointitr ));
                        //                    cout<<" point: "<<x<<", "<<y;
                        poly << QPoint( x, y );
                    }
                    int halfEdgeRoomId=voriHalfEdgeItr->getRoomId();
//                    cout<<"halfEdgeRoomId= "<<halfEdgeRoomId<<endl;
                    if(halfEdgeRoomId!=-1){
//                        cout<<"enter if(voriHalfEdgeItr->roomId!=-1)..."<<endl;
                        std::map<int, QColor>::iterator iter = roomColor.find(halfEdgeRoomId);
                        if(iter!=roomColor.end())
                        {
                            QColor color1= iter->second;
//                            cout<<"roomId= "<<halfEdgeRoomId<<
//                                " QColor="<<color1.red()<<", "<<color1.blue()<<", "<<color1.green()<<endl;
                            brush.setColor( color1 );
                            brush.setStyle( Qt::SolidPattern );
                            painter.setBrush( brush );
                            painter.setPen( color1 );
                        } else{
                            roomColor[halfEdgeRoomId]=color;
                        }
                    }
                    painter.drawPolygon( poly );
                    VoriGraphHalfEdge * twinHalfedge=voriHalfEdgeItr->twin;
                    if(twinHalfedge) {
                        drawnHalfEdge.insert( twinHalfedge );
                        VoriGraphPolygon *twinpolygonPtr = twinHalfedge->pathFace;
                        if (twinpolygonPtr != 0) {
                            QPolygon twin_poly;
                            for (std::list<topo_geometry::point>::iterator pointitr = twinpolygonPtr->polygonpoints.begin();
                                 pointitr != twinpolygonPtr->polygonpoints.end(); pointitr++) {
                                int x = round( topo_geometry::getX( *pointitr ));
                                int y = round( topo_geometry::getY( *pointitr ));
                                twin_poly << QPoint( x, y );
                            }

                            painter.drawPolygon( twin_poly );
                        }
                    }
                }
            }

            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
            }
        }
    }
}


void qRGB2Gray_simple(QImage &image) {
    //problem: The background become black, and the whole pictrue is really dark
    QImage image2 = image.convertToFormat(QImage::Format_Indexed8);
    image2.setColorCount(256);
    for (int i = 0; i < 256; i++) {
        image2.setColor(i, qRgb(i, i, i));
    }
    image = image2;
}

void qRGB2Gray(QImage &image) {
//    QImage image2 = image.convertToFormat(QImage::Format_Indexed8);
    int w, h;
    w = image.width();
    h = image.height();
    QImage image2(w, h, QImage::Format_RGB32);
    for (int i = 0; i < image.width(); i++) {
        for (int j = 0; j < image.height(); j++) {
            QRgb pixel = image.pixel(i, j);
            int gray = qGray(pixel);
            QRgb grayPixel = qRgb(gray, gray, gray);
            image2.setPixel(i, j, grayPixel);
        }
    }

    image = image2;
}
void paintVori_onlyArea(QImage &image, VoriGraph &voriGraph){

    QPainter painter(&image);
//    cout<<"enter paintVori_AreaRoom() ..........."<<endl;

    unsigned int county = 0;

    int color_cnt=1,color_step=1;
    std::set<VoriGraphHalfEdge *> drawnHalfEdge;
    std::map<int, QColor> roomColor;
    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
//             painter.setPen(qRgb(0,255,0));
//             int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
//             int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
//             int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
//             int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            //painter.drawLine(x1, y1, x2, y2);
            //painter.drawLine(x1, y1, x2, y2);
        }else{
            if(drawnHalfEdge.find(&*voriHalfEdgeItr)==drawnHalfEdge.end()){
                drawnHalfEdge.insert(&*voriHalfEdgeItr);
                QBrush brush;
                QColor color = QColor( rand() % 255, rand() % 255, rand() % 255 );
//                QColor color = QColor( color_cnt % 254, color_cnt % 254, color_cnt % 254 );
                if(color_cnt==0)
                    color = QColor( ++color_cnt % 254, color_cnt % 254, color_cnt % 254 );
                color_cnt+=color_step;
                brush.setColor( color );
                brush.setStyle( Qt::SolidPattern );
                painter.setBrush( brush );
                painter.setPen( color );  // random color!!!!

                VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
                if(polygonPtr != 0) {
                    QPolygon poly;
                    for (std::list<topo_geometry::point>::iterator pointitr = polygonPtr->polygonpoints.begin();
                         pointitr != polygonPtr->polygonpoints.end(); pointitr++) {
                        int x = round( topo_geometry::getX( *pointitr ));
                        int y = round( topo_geometry::getY( *pointitr ));
                        //                    cout<<" point: "<<x<<", "<<y;
                        poly << QPoint( x, y );
                    }
                    int halfEdgeRoomId=voriHalfEdgeItr->getRoomId();
//                    cout<<"halfEdgeRoomId= "<<halfEdgeRoomId<<endl;
                    if(halfEdgeRoomId!=-1){
//                        cout<<"enter if(voriHalfEdgeItr->roomId!=-1)..."<<endl;
                        std::map<int, QColor>::iterator iter = roomColor.find(halfEdgeRoomId);
                        if(iter!=roomColor.end())
                        {
                            QColor color1= iter->second;
//                            cout<<"roomId= "<<halfEdgeRoomId<<
//                                " QColor="<<color1.red()<<", "<<color1.blue()<<", "<<color1.green()<<endl;
                            brush.setColor( color1 );
                            brush.setStyle( Qt::SolidPattern );
                            painter.setBrush( brush );
                            painter.setPen( color1 );
                            color_cnt-=color_step;
                        } else{
                            roomColor[halfEdgeRoomId]=color;
                        }
                    }
                    painter.drawPolygon( poly );
                    VoriGraphHalfEdge * twinHalfedge=voriHalfEdgeItr->twin;
                    if(twinHalfedge) {
                        drawnHalfEdge.insert( &*twinHalfedge );
                        if (twinHalfedge->pathFace != 0) {
                            VoriGraphPolygon *twinpolygonPtr = twinHalfedge->pathFace;
                            QPolygon twin_poly;
                            for (std::list<topo_geometry::point>::iterator pointitr = twinpolygonPtr->polygonpoints.begin();
                                 pointitr != twinpolygonPtr->polygonpoints.end(); pointitr++) {
                                int x = round( topo_geometry::getX( *pointitr ));
                                int y = round( topo_geometry::getY( *pointitr ));
                                twin_poly << QPoint( x, y );
                            }

                            painter.drawPolygon( twin_poly );
                        } else{
                            std::cout<<"qt  twin no pathface!!"<<endl;
                        }
                    } else{
                        std::cout<<"qt  no twin path!!"<<endl;
                    }
                } else{
                    std::cout<<"qt  no pathface!!"<<endl;
                }
            }

//            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
//                painter.setPen(qRgb(0,255,255));
//            }else{
//                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
//            }
//
//            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
//            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
////                 const topo_geometry::Halfedge &he = *pathEdgeItr;
////                 int x1 = (round(topo_geometry::getX(he.s())));
////                 int y1 = (round(topo_geometry::getY(he.s())));
////                 int x2 = (round(topo_geometry::getX(he.t())));
////                 int y2 = (round(topo_geometry::getY(he.t())));
////                 painter.drawLine(x1, y1, x2, y2);
//            }//for
        }// is (not) ray
//        painter.setPen(qRgb(255,0,255));
//
//        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色
//
//            if(voriHalfEdgeItr->source){
////                 painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
////                                   round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
//            }
//            if(voriHalfEdgeItr->target){
////                 painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
//            }
//
//
//        }
    }// for voriGraph.halfEdges


//    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
//        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
//            VoriGraphVertex * source = voriHalfEdgeItr->source;
//            painter.setPen(qRgb(255,255,0));
//
//            if(source){
//                topo_geometry::point p;
//                if(voriHalfEdgeItr->getPointForDistance(5, p)){
////                     painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
//                }
//            }
//        }
//    }

}


void paintVori_pathFace(QImage &image, VoriGraph &voriGraph){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);

    unsigned int county = 0;

    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{
//            cout<<endl<<"source:"<<voriHalfEdgeItr->source->point.x()<<", "<<voriHalfEdgeItr->source->point.y()
//                <<"target:"<<voriHalfEdgeItr->target->point.x()<<", "<<voriHalfEdgeItr->target->point.y()<<endl;

            VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
            if(polygonPtr != 0 /*&& polygonPtr->isRay*/){
//                cout<<"polygonPtr != 0 && polygonPtr->isRay"<<endl;
                QPolygon poly;
                for(std::list<topo_geometry::point>::iterator pointitr=polygonPtr->polygonpoints.begin();
                    pointitr!=polygonPtr->polygonpoints.end();pointitr++){
                    int x=round(topo_geometry::getX(*pointitr));
                    int y=round(topo_geometry::getY(*pointitr));
//                    cout<<" point: "<<x<<", "<<y;
                    poly<<QPoint(x,y);

                }
                //painter.setBrush(Qt::Dense7Pattern);    //填充

                QBrush brush;
                            brush.setColor( qRgb(rand()%255, rand()%255, rand()%255) );
                            brush.setStyle( Qt::SolidPattern );
                            painter.setBrush( brush );
                //painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));  // random color!!!!
                painter.drawPolygon(poly);

            }

            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}
void paintVori_pathFace_backup(QImage &image, VoriGraph &voriGraph){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);

    unsigned int county = 0;

    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{

            std::list<topo_geometry::point>::iterator pointitr;
            VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
            if(polygonPtr != 0){
                QPolygon poly;
                for(pointitr=polygonPtr->polygonpoints.begin();pointitr!=polygonPtr->polygonpoints.end();pointitr++){
                    int x=round((*pointitr).x());
                    int y=round((*pointitr).y());
                    poly<<QPoint(x,y);

                }
//                painter.setBrush(Qt::Dense7Pattern);    //填充
                painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));  // random color!!!!
                painter.drawPolygon(poly);

            }

            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}
void paintVori_pathFace_backup1(QImage &image, VoriGraph &voriGraph){//jiawei 6.26 16:36

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);
//    cout<<"enter paintVori_pathFace..."<<endl;

    unsigned int county = 0;

    std::list<VoriGraphHalfEdge>::iterator voriHalfEdgeItr;  ;
    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        county++;
        if(voriHalfEdgeItr->isRay()){ //射线：绿色
            painter.setPen(qRgb(0,255,0));
            int x1 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.s())));   //坐标都取整（四舍五入）再画
            int y1 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.s())));
            int x2 = (round(topo_geometry::getX(voriHalfEdgeItr->topo_ray.t())));
            int y2 = (round(topo_geometry::getY(voriHalfEdgeItr->topo_ray.t())));
            painter.drawLine(x1, y1, x2, y2);
            painter.drawLine(x1, y1, x2, y2);
        }else{

            std::list<topo_geometry::point>::iterator pointitr;
            VoriGraphPolygon * polygonPtr=voriHalfEdgeItr->pathFace;
            if(polygonPtr != 0){
                QPolygon poly;
                for(pointitr=polygonPtr->polygonpoints.begin();pointitr!=polygonPtr->polygonpoints.end();pointitr++){
                    int x=round((*pointitr).x());
                    int y=round((*pointitr).y());
                    poly<<QPoint(x,y);

                }
//                painter.setBrush(Qt::Dense7Pattern);    //填充
                painter.setPen(qRgb(rand()%255, rand()%255, rand()%255));  // random color!!!!
                painter.drawPolygon(poly);

            }

            if(voriHalfEdgeItr->deadEnd){   //deadend：蓝绿色
                painter.setPen(qRgb(0,255,255));
            }else{
                painter.setPen(qRgb(0,0,255));    //一般path: 蓝色
            }

            std::list<topo_geometry::Halfedge>::const_iterator pathEdgeItr =  voriHalfEdgeItr->pathEdges.begin();
            for( ; pathEdgeItr != voriHalfEdgeItr->pathEdges.end(); pathEdgeItr++, county++){   //遍历path中的短边
                const topo_geometry::Halfedge &he = *pathEdgeItr;
                int x1 = (round(topo_geometry::getX(he.s())));
                int y1 = (round(topo_geometry::getY(he.s())));
                int x2 = (round(topo_geometry::getX(he.t())));
                int y2 = (round(topo_geometry::getY(he.t())));
                painter.drawLine(x1, y1, x2, y2);
            }//for
        }// is (not) ray
        painter.setPen(qRgb(255,0,255));

        if(!voriHalfEdgeItr->isRay()){    //画出ray所连节点：紫色

            if(voriHalfEdgeItr->source){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->source->point)),
                                  round(topo_geometry::getY(voriHalfEdgeItr->source->point)));
            }
            if(voriHalfEdgeItr->target){
                painter.drawPoint(round(topo_geometry::getX(voriHalfEdgeItr->target->point)), round(topo_geometry::getY(voriHalfEdgeItr->target->point)));
            }


        }
    }// for voriGraph.halfEdges


    for(voriHalfEdgeItr = voriGraph.halfEdges.begin(); voriHalfEdgeItr != voriGraph.halfEdges.end(); ++voriHalfEdgeItr){
        if(!voriHalfEdgeItr->isRay()){    //在deadend和一般path上距离节点为5处画黄点
            VoriGraphVertex * source = voriHalfEdgeItr->source;
            painter.setPen(qRgb(255,255,0));

            if(source){
                topo_geometry::point p;
                if(voriHalfEdgeItr->getPointForDistance(5, p)){
                    painter.drawPoint(round(topo_geometry::getX(p)), round(topo_geometry::getY(p)));
                }
/*          if(voriHalfEdgeItr->getPointForDistance(6, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }
          if(voriHalfEdgeItr->getPointForDistance(9, p)){
            painter.drawPoint(round(p.x()), round(p.y()));
          }*/
            }
        }
    }
}







/*
 * 
 * 
 * TopoGraph
 * 
 * 
 */


void paintVoriEdge(/*TopoGraph &graph,*/ QPainter &painter, VoriGraphHalfEdge *edge, bool isFeature){
    if(edge->isRay()){
      painter.setPen(qRgb(0,255,0));
    }else if(isFeature){
      painter.setPen(qRgb(0,255,255));
    }else{
      painter.setPen(qRgb(0,0,255));
    }
    std::list<topo_geometry::Halfedge>::iterator pathEdgeItr =  edge->pathEdges.begin ();
    for( ; pathEdgeItr != edge->pathEdges.end(); pathEdgeItr++){
	const topo_geometry::Halfedge &he = *pathEdgeItr;
	int x1 = (round(topo_geometry::getX(he.s())));
	int y1 = (round(topo_geometry::getY(he.s())));
	int x2 = (round(topo_geometry::getX(he.t())));
	int y2 = (round(topo_geometry::getY(he.t())));
	painter.drawLine(x1, y1, x2, y2);
    }//for
  /*      painter.setPen(qRgb(255,0,255));
  if(!edge->isRay()){
    if(edge->source) painter.drawPoint(round(edge->source->vertex->point().x()), round(edge->source->vertex->point().y()));
    if(edge->target) painter.drawPoint(round(edge->target->vertex->point().x()), round(edge->target->vertex->point().y()));
  }*/
}


void paintTopoPaths(TopoGraph &graph, QImage &image){

//     image = image.convertToFormat(QImage::Format_ARGB32);
//     image.fill(qRgba(0, 0, 0, 0));
    QPainter painter(&image);

    std::list<TopoHalfEdge>::iterator topoHalfEdgeItr;
    for(topoHalfEdgeItr = graph.aHalfEdges.begin(); topoHalfEdgeItr != graph.aHalfEdges.end(); ++topoHalfEdgeItr){
      for(list<VoriGraphHalfEdge*>::iterator itrVoriHalfEdges = topoHalfEdgeItr->voriHalfEdges.begin(); itrVoriHalfEdges != topoHalfEdgeItr->voriHalfEdges.end(); ++itrVoriHalfEdges){
        paintVoriEdge(painter, *itrVoriHalfEdges, (topoHalfEdgeItr->edgeFlags & TopoHalfEdge::FEATURE_END) || (topoHalfEdgeItr->twin->edgeFlags & TopoHalfEdge::FEATURE_END));
      }
    }// for

    list<TopoVertex>::iterator itrVertices;
    for(itrVertices = graph.aVertices.begin(); itrVertices != graph.aVertices.end(); ++itrVertices){
      painter.setPen(qRgb(255,0,255));
      if(itrVertices->isFeatureVertex) painter.setPen(qRgb(0,255,255));
      painter.drawRect(round(itrVertices->point.x()-1.), round(itrVertices->point.y()-1.),2,2);
//       cout<<"  "<<itrVertices->point<<"  numberOfVert "<<itrVertices->aVoriVertices.size()<< "number of exits "<<itrVertices->aExits.size()<<endl;
    }
}




// void TopoGraph::paintNumbers(QImage &image){
//     assignVertexIds();
// 
//     const int minusX = 3;
//     const int minusY = 3;
//     
//     QPainter painty(&image);
//     for(list<TopoVertex>::iterator itrVertices = aVertices.begin(); itrVertices != aVertices.end(); ++itrVertices){
//         painty.setPen(Qt::white);
//         painty.drawText(itrVertices->point.x() - minusX+1, itrVertices->point.y() - minusY+1, QString::number(itrVertices->id));
//         painty.drawText(itrVertices->point.x() - minusX+1, itrVertices->point.y() - minusY-1, QString::number(itrVertices->id));
//         painty.drawText(itrVertices->point.x() - minusX-1, itrVertices->point.y() - minusY+1, QString::number(itrVertices->id));
//         painty.drawText(itrVertices->point.x() - minusX-1, itrVertices->point.y() - minusY-1, QString::number(itrVertices->id));
//         painty.setPen(Qt::black);
//         painty.drawText(itrVertices->point.x() - minusX, itrVertices->point.y() - minusY, QString::number(itrVertices->id));
//     }
// 
// }



