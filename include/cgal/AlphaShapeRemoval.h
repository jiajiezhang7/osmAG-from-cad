#ifndef ALPHA_SHAPE_REMOVAL_H
#define ALPHA_SHAPE_REMOVAL_H

#define MAX_PLEN_REMOVAL 80 //380 for f101
class QImage;
// class AlphaShapeRemoval: public AlphaShapePolygon{
void performAlphaRemoval(QImage &pImg, double pAlphaShapeSquaredDist, double pMaxPolygonLength);
// };
#endif
