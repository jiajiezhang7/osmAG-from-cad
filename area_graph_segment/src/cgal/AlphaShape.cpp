#include "cgal/AlphaShape.h"
#include <QPainter>
#include <QPainterPath>
#include <QImage>
#include <QDebug>



using namespace std;


void AlphaShapePolygon::getPoints(QImage &pImg, std::vector<K::Point_2> &points) {

    unsigned int height = pImg.height();
    if (pImg.format() == QImage::Format_RGB32 || pImg.format() == QImage::Format_ARGB32) {
        qDebug() << "32 bit change color";
        // mark color here
        for (unsigned int y = 0; y < height; y++) {
            QRgb *pointer = (QRgb *) pImg.scanLine( y );
            QRgb *endP = pointer + pImg.width();
            for (unsigned int x = 0; pointer < endP; ++pointer, ++x) {
                if (qRed( *pointer ) < 2) {
                    points.push_back( K::Point_2( x + 0.25, y + 0.25 ));
                    points.push_back( K::Point_2( x + 0.25, y - 0.25 ));
                    points.push_back( K::Point_2( x - 0.25, y + 0.25 ));
                    points.push_back( K::Point_2( x - 0.25, y - 0.25 ));
                }
            }
        }
    } else if (pImg.format() == QImage::Format_RGB888) {
        qDebug() << "24 bit change color";
        for (unsigned int y = 0; y < height; y++) {
            // do the stuff...
            uchar *pointer = pImg.scanLine( y );
            uchar *endP = pointer + (pImg.width() * 3);
            for (unsigned int x = 0; pointer < endP; pointer += 3, x++) {
                if ((*pointer) < 2) {
                    points.push_back( K::Point_2( x + 0.25, y + 0.25 ));
                    points.push_back( K::Point_2( x + 0.25, y - 0.25 ));
                    points.push_back( K::Point_2( x - 0.25, y + 0.25 ));
                    points.push_back( K::Point_2( x - 0.25, y - 0.25 ));

                }
            }
        }
    }
}

AlphaShapePolygon::SegmentSearchy::SegmentSearchy(std::list<std::pair<AlphaShapePolygon::Segment, bool> > &pSegments)
        : aSegments( pSegments ) {
    fill();
}

void AlphaShapePolygon::SegmentSearchy::fill() {
    segmentSourceMap.clear();
    for (list<std::pair<AlphaShapePolygon::Segment, bool> >::iterator itr = aSegments.begin();
         itr != aSegments.end(); ++itr) {
        itr->second = true;
        segmentSourceMap[static_cast<int>(itr->first.source().x())][static_cast<int>(itr->first.source().y())].push_back(
                itr );
    }
}

AlphaShapePolygon::SegmentSearchy::CellEntries
AlphaShapePolygon::SegmentSearchy::findSegments(AlphaShapePolygon::K::Point_2 &p) {
    CellEntries rtn;
    map<int, map<int, CellEntries> >::iterator found1 = segmentSourceMap.find( static_cast<int>(p.x()));
    if (found1 == segmentSourceMap.end()) return rtn;
    map<int, CellEntries>::iterator found2 = found1->second.find( static_cast<int>(p.y()));
    if (found2 == found1->second.end()) return rtn;
    for (CellEntries::iterator itr = found2->second.begin(); itr != found2->second.end(); ++itr) {
        if ((*itr)->second && (*itr)->first.source() == p) rtn.push_back( *itr );
    }
    return rtn;
}


void AlphaShapePolygon::growPolygon(SegmentSearchy &searchy, Polygon_2 &polygon, K::Point_2 front, K::Point_2 back) {
    while (front != back) {
        SegmentSearchy::CellEntries found = searchy.findSegments( back );
        Segment currSegment;
        if (found.empty()) {
            cerr << "did not find contiuation for polygon!" << endl;
            return;
        }
        if (found.size() > 1) {
            cerr << "found " << found.size() << " continuations for polygon - randomly choosing..." << endl;
        }
        currSegment = (*found.begin())->first;
        // remove this segement...
        (*found.begin())->second = false;

        if (currSegment.source() == back) {
            back = currSegment.target();
            if (back != front) { ;
                polygon.push_back( currSegment.target());
            }
        } else {
            cerr << "not successfull :(" << endl;
        }
    }
}

// void AlphaShapePolygon::growPolygon(std::list<Segment> &segments, Polygon_2 &polygon, K::Point_2 front, K::Point_2 back){
//   list<Segment>::iterator itr = segments.begin();
//   while(front != back){
//     Segment &currSegment = *itr;
//     if(currSegment.target() == front){
//       front = currSegment.source();
//       if(back != front){
//         polygon.insert(polygon.vertices_begin(), currSegment.source());
//       }
//       list<Segment>::iterator del = itr;
//       ++itr;
//       segments.erase(del);
//     }else if(currSegment.source() == back){
//       back = currSegment.target();
//       if(back != front) {;
//         polygon.push_back(currSegment.target());
//       }
//       list<Segment>::iterator del = itr;
//       ++itr;
//       segments.erase(del);
//     }else{
//       ++itr;
//     }
//     // continue search
//     if(itr == segments.end()) itr = segments.begin();
//   }
// }

bool AlphaShapePolygon::isOutside(const K::Point_2 &p, Polygon_2 &poly, CGAL::Bbox_2 &box) {
    return p.x() >= box.xmin() && p.x() <= box.xmax() && p.y() >= box.ymin() && p.y() <= box.ymax() &&
           poly.is_simple() && !poly.has_on_unbounded_side( p );
}

void AlphaShapePolygon::generateBBoxesForPolygons(list<Polygon_2> &polygons, list<CGAL::Bbox_2> &bboxes) {
    for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
        bboxes.push_back( itr->bbox());
    }
}

double AlphaShapePolygon::calculatePolygonLength(Polygon_2 &polygon) {
    double length = 0.;
    for (Polygon_2::Edge_const_iterator edgeItr = polygon.edges_begin(); edgeItr != polygon.edges_end(); ++edgeItr) {
        length += sqrt( edgeItr->squared_length());
    }
    return length;
}

void AlphaShapePolygon::generatePolygons(std::vector<K::Point_2> &points, double squared_size_is_alpha,
                                         list<Polygon_2> &polygons) {

    Alpha_shape_2 alpha( points.begin(), points.end());
    alpha.set_alpha( squared_size_is_alpha );
    alpha.set_mode( Alpha_shape_2::REGULARIZED );
    cout << "calculated alpha - number " << alpha.number_of_solid_components() << endl;

    if (alpha.alpha_shape_edges_begin() == alpha.alpha_shape_edges_end()) return;

    std::list<std::pair<Segment, bool> > segments;

    for (Edge_iterator itr = alpha.alpha_shape_edges_begin(); itr != alpha.alpha_shape_edges_end(); ++itr) {
        segments.push_back( pair<Segment, bool>( alpha.segment( *itr ), true ));
//     cout<<"segment added"<<segments.rbegin()->first<<endl;
    }
    cout << "number of segments: " << segments.size() << " Generating polygons: " << endl;

    SegmentSearchy segmentSearchy( segments );
//   segmentSearchy.fill(segments);

    // find the polygon(s)
    for (std::list<std::pair<Segment, bool> >::iterator itr = segments.begin(); itr != segments.end(); ++itr) {
        if (itr->second) {
            itr->second = false;
            // search for all connected parts
            polygons.push_back( Polygon_2());
            Polygon_2 &currPoly = *polygons.rbegin();
            currPoly.push_back( itr->first.source());
            currPoly.push_back( itr->first.target());
            growPolygon( segmentSearchy, currPoly, itr->first.source(), itr->first.target());
        }
    }
}

// AlphaShapePolygon::Polygon_2 *
// AlphaShapePolygon::performAlpha(QImage &pImg, double squared_size_is_alpha, bool deleteSmallPolygon) {
//
//     std::vector<K::Point_2> points;
//     getPoints( pImg, points );
//
//     generatePolygons( points, squared_size_is_alpha, polygons );
//
//     pImg = pImg.convertToFormat( QImage::Format_ARGB32 );
// //   pImg.fill(qRgba(255, 255, 255, 0));
//
//     QPainter painty( &pImg );
//     painty.setPen( Qt::red );
//
//     cout << "number of polygons: " << polygons.size() << endl;
//     for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
//         for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr) {
//             Segment s = *edgeItr;
//             painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
//                              round( s.target().y()));
//         }
//     }
//
//     list<CGAL::Bbox_2> bboxes;
//     generateBBoxesForPolygons( polygons, bboxes );
//
//     if (deleteSmallPolygon) {
//         for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
//             // delete polygons inside this one:
//             list<CGAL::Bbox_2>::iterator itrBBox = bboxes.begin();
//             for (list<Polygon_2>::iterator itr2 = polygons.begin(); itr2 != polygons.end();) {
//
//                 if (itr != itr2 && isOutside( itr2->edges_begin()->source(), *itr, *itrBBox )) {
//                     // this is an inside polygon
//                     itr2 = polygons.erase( itr2 );
//                     itrBBox = bboxes.erase( itrBBox );
//                 } else {
//                     ++itr2;
//                     ++itrBBox;
//                 }
//             }
//         }
//
//         cout << "After inside removal: number of polygons: " << polygons.size() << endl;
//
//         for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
//             for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr) {
//                 Segment s = *edgeItr;
//                 painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
//                                  round( s.target().y()));
//             }
//         }
//     }
//
// //   Polygon_2 &biggest = *polygons.begin();
// //   double maxLength = -1.;
// //   for(list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr){
// //     double length = calculatePolygonLength(*itr);
// //     if(length > maxLength){
// //       maxLength = length;
// //       biggest = *itr;
// //     }
// //   }
//
//
//     int biggest = 0;
//     int counter = 0;
//     double maxLength = -1.;
//     for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr, ++counter) {
//         double length = calculatePolygonLength( *itr );
//         cout << " test  " << counter << "  length " << length << endl;
//         if (length > maxLength) {
//             maxLength = length;
//             biggest = counter;
//             cout << " biggest " << biggest << "  length " << length << endl;
//         }
//     }
//
//     painty.setPen( qRgb(255,200,0) );
//     cout << "Length of biggest polygon: " << maxLength << endl;
//     for (Polygon_2::Edge_const_iterator edgeItr = getPolygon( biggest ).edges_begin();
//          edgeItr != getPolygon( biggest ).edges_end(); ++edgeItr) {
//         Segment s = *edgeItr;
//         painty.drawLine( round( s.source().x()), round( s.source().y()),
//                          round( s.target().x()), round( s.target().y()));
//     }
//
//     return &getPolygon( biggest );
//
// }

AlphaShapePolygon::Polygon_2 *
AlphaShapePolygon::performAlpha(QImage &pImg, double squared_size_is_alpha, bool deleteSmallPolygon) {
//biggest alpha shape: longest length
    std::vector<K::Point_2> points;
    getPoints( pImg, points );

    generatePolygons( points, squared_size_is_alpha, polygons );

    pImg = pImg.convertToFormat( QImage::Format_ARGB32 );
//   pImg.fill(qRgba(255, 255, 255, 0));

    QPainter painty( &pImg );
    painty.setPen( Qt::red );


   QBrush brush;
   QColor color = QColor( qRgba(250,0,0,80) );
   brush.setColor( color );
   brush.setStyle( Qt::Dense7Pattern );
   QPainter painter(&pImg);
   painty.setBrush( brush );
   painty.setPen( color );
    cout << "number of polygons: " << polygons.size() << endl;
    int cnt=0;
    for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
        QPolygon poly;
        for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr) {
            Segment s = *edgeItr;
            painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
                             round( s.target().y()));
           poly << QPoint( round( s.target().x()), round( s.target().y()));
        }
       if (cnt!=0)
       painty.drawPolygon( poly );
       cnt++;
    }

    list<CGAL::Bbox_2> bboxes;
    generateBBoxesForPolygons( polygons, bboxes );

    if (deleteSmallPolygon) {
        for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
            // delete polygons inside this one:
            list<CGAL::Bbox_2>::iterator itrBBox = bboxes.begin();
            for (list<Polygon_2>::iterator itr2 = polygons.begin(); itr2 != polygons.end();) {

                if (itr != itr2 && isOutside( itr2->edges_begin()->source(), *itr, *itrBBox )) {
                    // this is an inside polygon
                    itr2 = polygons.erase( itr2 );
                    itrBBox = bboxes.erase( itrBBox );
                } else {
                    ++itr2;
                    ++itrBBox;
                }
            }
        }

//        cout << "After inside removal: number of polygons: " << polygons.size() << endl;

        for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
            for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr) {
                Segment s = *edgeItr;
                painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
                                 round( s.target().y()));
            }
        }
    }

//   Polygon_2 &biggest = *polygons.begin();
//   double maxLength = -1.;
//   for(list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr){
//     double length = calculatePolygonLength(*itr);
//     if(length > maxLength){
//       maxLength = length;
//       biggest = *itr;
//     }
//   }


    int biggest = 0;
    int counter = 0;
    double maxLength = -1.;
    for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr, ++counter) {
        double length = calculatePolygonLength( *itr );
//        cout << " test  " << counter << "  length " << length << endl;
        if (length > maxLength) {
            maxLength = length;
            biggest = counter;
//            cout << " biggest " << biggest << "  length " << length << endl;
        }
    }

    painty.setPen( qRgb(0,250,0) );
    cout << "Length of biggest polygon: " << maxLength << endl;
    for (Polygon_2::Edge_const_iterator edgeItr = getPolygon( biggest ).edges_begin();
         edgeItr != getPolygon( biggest ).edges_end(); ++edgeItr) {
        Segment s = *edgeItr;
        painty.drawLine( round( s.source().x()), round( s.source().y()),
                         round( s.target().x()), round( s.target().y()));
    }

    return &getPolygon( biggest );

}
AlphaShapePolygon::Polygon_2 *
AlphaShapePolygon::performAlpha_biggestArea(QImage &pImg, double squared_size_is_alpha, bool deleteSmallPolygon) {
    // function: returen biggest alpha polygon, and save all generated alpha polygons in this->polygons (protected member)

    std::vector<K::Point_2> points;
    getPoints( pImg, points );

    // polygons: a list of alpha shape polygons
    generatePolygons( points, squared_size_is_alpha, polygons );

    pImg = pImg.convertToFormat( QImage::Format_ARGB32 );

    QPainter painty( &pImg );
    painty.setPen( Qt::red );


   QBrush brush;
   QColor color = QColor( qRgba(250,0,0,80) );
   brush.setColor( color );
   brush.setStyle( Qt::Dense7Pattern );
//   QPainter painter(&pImg);
   painty.setBrush( brush );
   painty.setPen( color );
    cout << "number of polygons: " << polygons.size() << endl;
    if(!deleteSmallPolygon) {
        int cnt = 0;
        for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
            QPolygon poly;
            for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin(); edgeItr != itr->edges_end(); ++edgeItr) {
                Segment s = *edgeItr;
                painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
                                 round( s.target().y()));
                poly << QPoint( round( s.target().x()), round( s.target().y()));
            }
            if (cnt != 0)
                painty.drawPolygon( poly );
            cnt++;
        }
    }

    list<CGAL::Bbox_2> bboxes;
    generateBBoxesForPolygons( polygons, bboxes );

    if (deleteSmallPolygon) {
        for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
            // delete polygons inside this one:
            list<CGAL::Bbox_2>::iterator itrBBox = bboxes.begin();
            for (list<Polygon_2>::iterator itr2 = polygons.begin(); itr2 != polygons.end();) {

                if (itr != itr2 && isOutside( itr2->edges_begin()->source(), *itr, *itrBBox )) {
                    // this is an inside polygon
                    itr2 = polygons.erase( itr2 );
                    itrBBox = bboxes.erase( itrBBox );
                } else {
                    ++itr2;
                    ++itrBBox;
                }
            }
        }

        if(!deleteSmallPolygon) {
            for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr) {
                for (Polygon_2::Edge_const_iterator edgeItr = itr->edges_begin();
                     edgeItr != itr->edges_end(); ++edgeItr) {
                    Segment s = *edgeItr;
                    painty.drawLine( round( s.source().x()), round( s.source().y()), round( s.target().x()),
                                     round( s.target().y()));
                }
            }
        }
    }
    int biggest = 0;
    int counter = 0;
    double maxArea = -1.;
    for (list<Polygon_2>::iterator itr = polygons.begin(); itr != polygons.end(); ++itr, ++counter) {
	double tem_area= fabs(itr->area());
//        cout << " test  " << counter << "  area " << tem_area << endl;
        if (tem_area > maxArea) {
            maxArea = tem_area;
            biggest = counter;
        }
    }

    painty.setPen( qRgb(0,0,0) );
    if(!deleteSmallPolygon)
        painty.setPen( qRgb(0,0,250) );
    cout << "Area of biggest polygon: " << maxArea << endl;
    for (Polygon_2::Edge_const_iterator edgeItr = getPolygon( biggest ).edges_begin();
         edgeItr != getPolygon( biggest ).edges_end(); ++edgeItr) {
        Segment s = *edgeItr;
        painty.drawLine( round( s.source().x()), round( s.source().y()),
                         round( s.target().x()), round( s.target().y()));
    }

    return &getPolygon( biggest );

}

//add
AlphaShapePolygon::Polygon_2 &AlphaShapePolygon::getPolygon(unsigned int i) {
    std::list<Polygon_2>::iterator itr = polygons.begin();
    unsigned int index;
    for (index = 0; index < i && itr != polygons.end(); index++, itr++);
    if (index == i) {
        return *itr;
    } else {
        return polygons.back();
    }
}

unsigned int AlphaShapePolygon::sizeOfPolygons() {
    return polygons.size();
}

void AlphaShapePolygon::drawPolygonByIndex(QImage &pImg, unsigned int index) {
    QPainter painty( &pImg );
    unsigned int i = 0;
    QPainterPath polygonPath;

    for (Polygon_2::Edge_const_iterator edgeItr = getPolygon( index ).edges_begin();
         edgeItr != getPolygon( index ).edges_end(); ++edgeItr) {
        Segment s = *edgeItr;
        if (i == 0) {
            polygonPath.moveTo( round( s.source().x()), round( s.source().y()));
        } else {
            polygonPath.lineTo( round( s.source().x()), round( s.source().y()));
        }
        i++;
        //painty.drawLine(round(s.source().x()), round(s.source().y()), round( s.target().x()), round(s.target().y()));
    }
    polygonPath.closeSubpath();

    painty.setPen( Qt::red );
    painty.fillPath( polygonPath, QBrush( QColor( 255, 255, (255 / (sizeOfPolygons())) * index ), Qt::SolidPattern ));
    painty.drawPath( polygonPath );

    /*painty.setPen(Qt::red);
    if(index < sizeOfPolygons())
    {
      for(Polygon_2::Edge_const_iterator edgeItr = getPolygon(index).edges_begin(); edgeItr != getPolygon(index).edges_end(); ++edgeItr){
            Segment s = *edgeItr;
            painty.drawLine(round(s.source().x()), round(s.source().y()), round( s.target().x()), round(s.target().y()));
      }
    }*/
}

void AlphaShapePolygon::drawPolygon(QImage &pImg, Polygon_2 *poly) {
    QPainter painty( &pImg );
    for (int index = 0; index < sizeOfPolygons(); index++) {
        unsigned int i = 0;
        QPainterPath polygonPath;

        for (Polygon_2::Edge_const_iterator edgeItr = getPolygon( index ).edges_begin();
             edgeItr != getPolygon( index ).edges_end(); ++edgeItr) {
            Segment s = *edgeItr;
            if (i == 0) {
                polygonPath.moveTo( round( s.source().x()), round( s.source().y()));
            } else {
                polygonPath.lineTo( round( s.source().x()), round( s.source().y()));
            }
            i++;
        }
        polygonPath.closeSubpath();

        if (getPolygon( index ) != *poly) {
            painty.setPen( Qt::red );
            painty.fillPath( polygonPath,
                             QBrush( QColor( 255, 255, (255 / (sizeOfPolygons())) * index ), Qt::SolidPattern ));
        } else {
            painty.setPen( Qt::blue );
        }

        painty.drawPath( polygonPath );
    }
}