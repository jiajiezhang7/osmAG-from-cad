#ifndef POLYGON_PROCESSOR_H
#define POLYGON_PROCESSOR_H

#include "TopoGeometry.h"
#include <list>
#include <vector>

namespace RMG {

class AreaGraph; // 前向声明

namespace PolygonProcessor {

// Douglas-Peucker算法递归简化多边形一部分
void douglasPeuckerRecursive(const std::vector<topo_geometry::point>& points, int start, int end, 
                            double epsilon, std::vector<bool>& keepPoint, 
                            AreaGraph* areaGraph);

// 简化单个多边形
std::list<topo_geometry::point> simplifyPolygon(const std::list<topo_geometry::point>& polygon, 
                                              double epsilon, 
                                              const std::vector<topo_geometry::point>* preservePoints,
                                              AreaGraph* areaGraph);

// 移除单个多边形中的"毛刺"
std::list<topo_geometry::point> removeSpikesFromPolygon(const std::list<topo_geometry::point>& polygon, 
                                                      double angleThreshold, 
                                                      double distanceThreshold,
                                                      const std::vector<topo_geometry::point>* preservePoints);

// 合并两个多边形
std::list<topo_geometry::point> mergePolygons(const std::list<topo_geometry::point>& poly1, 
                                            const std::list<topo_geometry::point>& poly2);

// 计算多边形的哈希值
size_t calculatePolygonHash(const std::list<topo_geometry::point>& polygon);

// 判断两个多边形是否相同
bool arePolygonsEqual(const std::list<topo_geometry::point>& poly1, 
                     const std::list<topo_geometry::point>& poly2);

} // namespace PolygonProcessor
} // namespace RMG

#endif // POLYGON_PROCESSOR_H
