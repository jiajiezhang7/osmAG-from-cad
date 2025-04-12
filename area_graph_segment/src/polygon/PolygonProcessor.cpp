#include "polygon/PolygonProcessor.h"
#include "geometry/GeometryUtils.h"
#include "roomGraph.h"
#include <algorithm>
#include <cmath>

namespace RMG {
namespace PolygonProcessor {

// Douglas-Peucker算法递归简化多边形一部分
void douglasPeuckerRecursive(const std::vector<topo_geometry::point>& points, int start, int end, 
                           double epsilon, std::vector<bool>& keepPoint, 
                           AreaGraph* areaGraph) {
    if (end - start <= 1) {
        return;
    }
    
    // 找出最远的点
    double maxDistance = 0.0;
    int furthestIndex = start;
    
    for (int i = start + 1; i < end; ++i) {
        double distance = GeometryUtils::pointToLineDistance(points[i], points[start], points[end]);
        if (distance > maxDistance) {
            maxDistance = distance;
            furthestIndex = i;
        }
    }
    
    // 如果最远的点距离超过阈值，保留它并递归简化两侧
    if (maxDistance > epsilon) {
        keepPoint[furthestIndex] = true;
        douglasPeuckerRecursive(points, start, furthestIndex, epsilon, keepPoint, areaGraph);
        douglasPeuckerRecursive(points, furthestIndex, end, epsilon, keepPoint, areaGraph);
    }
}

// 简化单个多边形
std::list<topo_geometry::point> simplifyPolygon(const std::list<topo_geometry::point>& polygon, 
                                              double epsilon, 
                                              const std::vector<topo_geometry::point>* preservePoints,
                                              AreaGraph* areaGraph) {
    if (polygon.size() <= 3) {
        return polygon; // 不能再简化
    }
    
    // 转换为向量便于索引访问
    std::vector<topo_geometry::point> points(polygon.begin(), polygon.end());
    int n = points.size();
    
    // 检测多边形是否近似圆形
    bool isCircular = GeometryUtils::isApproximatelyCircular(points);
    
    // 根据多边形类型调整epsilon
    double effectiveEpsilon = isCircular ? epsilon * 0.5 : epsilon * 1.5;
    
    // 初始化保留标记，默认只保留第一个和最后一个点
    std::vector<bool> keepPoint(n, false);
    keepPoint[0] = true;
    keepPoint[n-1] = true;
    
    // 标记需要保留的特殊点（如通道端点）
    if (preservePoints != nullptr && !preservePoints->empty()) {
        const double PRESERVE_THRESHOLD = 1e-6; // 保留点判断阈值
        
        for (int i = 0; i < n; ++i) {
            for (const auto& preservePoint : *preservePoints) {
                if (GeometryUtils::equalLineVertex(points[i], preservePoint) || 
                    boost::geometry::distance(points[i], preservePoint) < PRESERVE_THRESHOLD) {
                    keepPoint[i] = true;
                    break;
                }
            }
        }
    }
    
    // 应用Douglas-Peucker算法，使用调整后的epsilon值
    douglasPeuckerRecursive(points, 0, n-1, effectiveEpsilon, keepPoint, areaGraph);
    
    // 根据标记建立简化后的多边形
    std::list<topo_geometry::point> simplifiedPolygon;
    for (int i = 0; i < n; ++i) {
        if (keepPoint[i]) {
            simplifiedPolygon.push_back(points[i]);
        }
    }
    
    // 确保多边形闭合
    if (!simplifiedPolygon.empty() && !GeometryUtils::equalLineVertex(simplifiedPolygon.front(), simplifiedPolygon.back())) {
        simplifiedPolygon.push_back(simplifiedPolygon.front());
    }
    
    return simplifiedPolygon;
}

// 移除单个多边形中的"毛刺"
std::list<topo_geometry::point> removeSpikesFromPolygon(const std::list<topo_geometry::point>& polygon, 
                                                      double angleThreshold, 
                                                      double distanceThreshold,
                                                      const std::vector<topo_geometry::point>* preservePoints) {
    if (polygon.size() <= 3) {
        return polygon; // 不能再简化
    }
    
    // 将多边形转换为向量便于索引访问
    std::vector<topo_geometry::point> points(polygon.begin(), polygon.end());
    int n = points.size();
    
    // 检测多边形是否近似圆形
    bool isCircular = GeometryUtils::isApproximatelyCircular(points);
    
    // 根据多边形特征调整阈值
    double effectiveAngleThreshold = isCircular ? angleThreshold * 0.5 : angleThreshold;
    double effectiveDistanceThreshold = isCircular ? distanceThreshold * 2.0 : distanceThreshold;
    
    // 标记需要保留的点
    std::vector<bool> keepPoint(n, true);
    
    // 处理保留点列表
    std::vector<int> preserveIndices;
    if (preservePoints != nullptr && !preservePoints->empty()) {
        const double PRESERVE_THRESHOLD = 1e-6; // 保留点判断阈值
        
        for (int i = 0; i < n; ++i) {
            for (const auto& preservePoint : *preservePoints) {
                if (GeometryUtils::equalLineVertex(points[i], preservePoint) || 
                    boost::geometry::distance(points[i], preservePoint) < PRESERVE_THRESHOLD) {
                    preserveIndices.push_back(i);
                    break;
                }
            }
        }
    }
    
    // 遍历所有连续的三个点
    for (int i = 0; i < n; ++i) {
        // 确保索引在范围内并形成循环
        int prev = (i + n - 1) % n;
        int curr = i;
        int next = (i + 1) % n;
        
        // 跳过保留点
        bool isPreservePoint = false;
        for (int idx : preserveIndices) {
            if (curr == idx) {
                isPreservePoint = true;
                break;
            }
        }
        if (isPreservePoint) continue;
        
        // 计算向量
        double ax = topo_geometry::getX(points[prev]) - topo_geometry::getX(points[curr]);
        double ay = topo_geometry::getY(points[prev]) - topo_geometry::getY(points[curr]);
        double bx = topo_geometry::getX(points[next]) - topo_geometry::getX(points[curr]);
        double by = topo_geometry::getY(points[next]) - topo_geometry::getY(points[curr]);
        
        // 计算向量长度（即点之间的距离）
        double lenA = std::sqrt(ax*ax + ay*ay);
        double lenB = std::sqrt(bx*bx + by*by);
        
        // 如果任一距离为0，跳过
        if (lenA < 1e-6 || lenB < 1e-6) continue;
        
        // 计算归一化向量
        ax /= lenA; ay /= lenA;
        bx /= lenB; by /= lenB;
        
        // 计算点积 (cos theta)
        double dotProduct = ax*bx + ay*by;
        
        // 限制在[-1, 1]范围内，避免浮点误差
        dotProduct = std::max(-1.0, std::min(1.0, dotProduct));
        
        // 计算角度（弧度），然后转换为度
        double angle = std::acos(dotProduct) * 180.0 / M_PI;
        
        // 计算点到直线的距离
        double distance = GeometryUtils::pointToLineDistance(points[curr], points[prev], points[next]);
        
        // 检测是否是平滑曲线的一部分
        bool isCurve = GeometryUtils::isPartOfSmoothCurve(points, curr);
        
        // 判断是否是"毛刺"
        bool isSpike = false;
        
        // 如果是平滑曲线的一部分，不视为毛刺
        if (isCurve && isCircular) {
            isSpike = false;
        } else {
            // 条件1：角度与90度相差过大，且距离小
            if (std::abs(angle - 90.0) > effectiveAngleThreshold && distance < effectiveDistanceThreshold) {
                isSpike = true;
            }
            
            // 条件2：特别尖锐的角度或非常钝的角度
            // 对于圆形，使用更严格的条件
            if (isCircular) {
                if (angle < 15.0 || angle > 165.0) { // 更严格的条件
                    isSpike = true;
                }
            } else {
                if (angle < 30.0 || angle > 150.0) {
                    isSpike = true;
                }
            }
            
            // 条件3：长毛刺 - 点到直线的距离与向量长度的比例很小
            double minVectorLen = std::min(lenA, lenB);
            double ratio = distance / minVectorLen;
            
            // 对于圆形，使用更宽松的比例阈值
            if (isCircular) {
                if (minVectorLen > 0.1 && ratio < 0.05) { // 更宽松的条件
                    isSpike = true;
                }
            } else {
                if (minVectorLen > 0.1 && ratio < 0.1) {
                    isSpike = true;
                }
            }
        }
        
        if (isSpike) {
            keepPoint[curr] = false;
        }
    }
    
    // 根据标记重建多边形
    std::list<topo_geometry::point> smoothedPolygon;
    for (int i = 0; i < n; ++i) {
        if (keepPoint[i]) {
            smoothedPolygon.push_back(points[i]);
        }
    }
    
    // 确保多边形闭合
    if (!smoothedPolygon.empty() && !GeometryUtils::equalLineVertex(smoothedPolygon.front(), smoothedPolygon.back())) {
        smoothedPolygon.push_back(smoothedPolygon.front());
    }
    
    return smoothedPolygon;
}

// 合并两个多边形
std::list<topo_geometry::point> mergePolygons(const std::list<topo_geometry::point>& poly1, 
                                            const std::list<topo_geometry::point>& poly2) {
    // 使用CGAL库合并多边形
    // 这里使用简化版本：将两个多边形的点合并，然后计算凸包
    std::vector<topo_geometry::point> allPoints;
    
    // 收集所有点
    for (const auto& p : poly1) allPoints.push_back(p);
    for (const auto& p : poly2) allPoints.push_back(p);
    
    // 去除重复点
    std::sort(allPoints.begin(), allPoints.end(), 
              [](const topo_geometry::point& a, const topo_geometry::point& b) {
                  if (topo_geometry::getX(a) != topo_geometry::getX(b))
                      return topo_geometry::getX(a) < topo_geometry::getX(b);
                  return topo_geometry::getY(a) < topo_geometry::getY(b);
              });
    
    allPoints.erase(std::unique(allPoints.begin(), allPoints.end(), 
                              [](const topo_geometry::point& a, const topo_geometry::point& b) {
                                  return GeometryUtils::equalLineVertex(a, b);
                              }), allPoints.end());
    
    // 计算凸包或使用更复杂的多边形合并算法
    // 这里简化处理，直接返回所有点
    return std::list<topo_geometry::point>(allPoints.begin(), allPoints.end());
}

// 计算多边形的哈希值
size_t calculatePolygonHash(const std::list<topo_geometry::point>& polygon) {
    // 计算多边形的质心
    double centroidX = 0, centroidY = 0;
    int count = 0;
    
    for (const auto& point : polygon) {
        centroidX += topo_geometry::getX(point);
        centroidY += topo_geometry::getY(point);
        count++;
    }
    
    if (count > 0) {
        centroidX /= count;
        centroidY /= count;
    }
    
    // 计算多边形的面积和周长
    double area = GeometryUtils::calcPolyArea(const_cast<std::list<topo_geometry::point>&>(polygon));
    double perimeter = 0;
    
    auto it = polygon.begin();
    auto prevIt = it;
    ++it;
    
    while (it != polygon.end()) {
        perimeter += boost::geometry::distance(*prevIt, *it);
        prevIt = it;
        ++it;
    }
    
    // 如果多边形不闭合，添加最后一条边的长度
    if (!polygon.empty() && !GeometryUtils::equalLineVertex(polygon.front(), polygon.back())) {
        perimeter += boost::geometry::distance(polygon.back(), polygon.front());
    }
    
    // 计算顶点数量
    size_t vertexCount = polygon.size();
    
    // 组合这些特征计算哈希值
    std::hash<double> doubleHasher;
    std::hash<size_t> sizeHasher;
    
    size_t hash = 17;
    hash = hash * 31 + doubleHasher(area);
    hash = hash * 31 + doubleHasher(perimeter);
    hash = hash * 31 + doubleHasher(centroidX);
    hash = hash * 31 + doubleHasher(centroidY);
    hash = hash * 31 + sizeHasher(vertexCount);
    
    return hash;
}

// 判断两个多边形是否相同
bool arePolygonsEqual(const std::list<topo_geometry::point>& poly1, 
                     const std::list<topo_geometry::point>& poly2) {
    // 如果顶点数量不同，多边形不同
    if (poly1.size() != poly2.size()) {
        return false;
    }
    
    // 如果多边形为空，认为相同
    if (poly1.empty() && poly2.empty()) {
        return true;
    }
    
    // 计算多边形的面积和周长
    double area1 = GeometryUtils::calcPolyArea(const_cast<std::list<topo_geometry::point>&>(poly1));
    double area2 = GeometryUtils::calcPolyArea(const_cast<std::list<topo_geometry::point>&>(poly2));
    
    // 如果面积差异过大，多边形不同
    const double AREA_THRESHOLD = 0.01;
    if (std::abs(area1 - area2) > AREA_THRESHOLD) {
        return false;
    }
    
    // 计算每个顶点到质心的距离，并按距离排序
    std::vector<double> distances1, distances2;
    
    // 计算poly1的质心
    double centroidX1 = 0, centroidY1 = 0;
    for (const auto& point : poly1) {
        centroidX1 += topo_geometry::getX(point);
        centroidY1 += topo_geometry::getY(point);
    }
    centroidX1 /= poly1.size();
    centroidY1 /= poly1.size();
    topo_geometry::point centroid1(centroidX1, centroidY1);
    
    // 计算poly2的质心
    double centroidX2 = 0, centroidY2 = 0;
    for (const auto& point : poly2) {
        centroidX2 += topo_geometry::getX(point);
        centroidY2 += topo_geometry::getY(point);
    }
    centroidX2 /= poly2.size();
    centroidY2 /= poly2.size();
    topo_geometry::point centroid2(centroidX2, centroidY2);
    
    // 计算每个顶点到质心的距离
    for (const auto& point : poly1) {
        distances1.push_back(boost::geometry::distance(point, centroid1));
    }
    
    for (const auto& point : poly2) {
        distances2.push_back(boost::geometry::distance(point, centroid2));
    }
    
    // 排序距离
    std::sort(distances1.begin(), distances1.end());
    std::sort(distances2.begin(), distances2.end());
    
    // 比较排序后的距离
    const double DISTANCE_THRESHOLD = 0.01;
    for (size_t i = 0; i < distances1.size(); ++i) {
        if (std::abs(distances1[i] - distances2[i]) > DISTANCE_THRESHOLD) {
            return false;
        }
    }
    
    // 如果所有检查都通过，认为多边形相同
    return true;
}

} // namespace PolygonProcessor
} // namespace RMG
