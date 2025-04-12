#ifndef GEOMETRY_UTILS_H
#define GEOMETRY_UTILS_H

#include "TopoGeometry.h"
#include <list>
#include <boost/geometry.hpp>

namespace RMG {
namespace GeometryUtils {

// 判断两个点是否相等（考虑浮点误差）
bool equalLineVertex(const topo_geometry::point &a, const topo_geometry::point &b);

// 计算多边形面积
double calcPolyArea(std::list<topo_geometry::point> &polygon);

// 将笛卡尔坐标转换为经纬度
std::pair<double, double> cartesianToLatLon(double x, double y, double root_lat, double root_lon);

// 计算点到线段的距离
double pointToLineDistance(const topo_geometry::point& p, const topo_geometry::point& lineStart, const topo_geometry::point& lineEnd);

// 计算局部曲率
double calculateLocalCurvature(const std::vector<topo_geometry::point>& points, int index, int windowSize = 5);

// 检测是否是平滑曲线的一部分
bool isPartOfSmoothCurve(const std::vector<topo_geometry::point>& points, int index, int windowSize = 5);

// 检测多边形是否近似圆形
bool isApproximatelyCircular(const std::vector<topo_geometry::point>& points);

// 计算点到质心的距离
double distanceToCenter(const topo_geometry::point& p, double centerX, double centerY);

} // namespace GeometryUtils
} // namespace RMG

#endif // GEOMETRY_UTILS_H
