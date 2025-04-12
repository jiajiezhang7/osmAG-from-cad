#include "passage/PassageProcessor.h"
#include "geometry/GeometryUtils.h"
#include <algorithm>
#include <limits>

namespace RMG {
namespace PassageProcessor {

// 优化房间多边形，使通道与房间边界重合
void optimizeRoomPolygonsForPassages(AreaGraph* areaGraph, 
                                   const std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, 
                                   std::pair<roomVertex*, roomVertex*>>>* precomputedPassagePoints) {
    // 保存所有通道的端点信息
    struct PassageEndpoints {
        topo_geometry::point pointA;
        topo_geometry::point pointB;
        roomVertex* roomA;
        roomVertex* roomB;
    };
    
    std::vector<PassageEndpoints> allPassages;
    
    // 如果提供了预计算的通道端点，则直接使用
    if (precomputedPassagePoints) {
        // 使用预计算的通道端点
        for (const auto& passagePoint : *precomputedPassagePoints) {
            const auto& points = passagePoint.first;
            const auto& rooms = passagePoint.second;
            
            PassageEndpoints endpoints;
            endpoints.pointA = points.first;
            endpoints.pointB = points.second;
            endpoints.roomA = rooms.first;
            endpoints.roomB = rooms.second;
            allPassages.push_back(endpoints);
        }
    } else {
        // 第一步：收集所有通道的端点信息
        for (auto passageEdge : areaGraph->passageEList) {
            if (passageEdge->connectedAreas.size() == 2) {
                roomVertex* roomA = passageEdge->connectedAreas[0];
                roomVertex* roomB = passageEdge->connectedAreas[1];
                
                // 定义判断两个点是否接近的阈值
                const double POINT_PROXIMITY_THRESHOLD = 0.5; // 根据实际坐标系调整
                
                // 计算通道附近的点
                const int MAX_POINTS_TO_CONSIDER = 10;
                std::vector<std::pair<topo_geometry::point, double>> roomAPoints, roomBPoints;
                
                // 收集房间A中距离通道最近的点
                for (const auto& point : roomA->polygon) {
                    double dist = boost::geometry::distance(point, passageEdge->position);
                    roomAPoints.push_back(std::make_pair(point, dist));
                }
                
                // 按距离排序
                std::sort(roomAPoints.begin(), roomAPoints.end(), 
                    [](const auto& a, const auto& b) { return a.second < b.second; });
                
                // 限制为前N个点
                if (roomAPoints.size() > MAX_POINTS_TO_CONSIDER) {
                    roomAPoints.resize(MAX_POINTS_TO_CONSIDER);
                }
                
                // 收集房间B中距离通道最近的点
                for (const auto& point : roomB->polygon) {
                    double dist = boost::geometry::distance(point, passageEdge->position);
                    roomBPoints.push_back(std::make_pair(point, dist));
                }
                
                // 按距离排序
                std::sort(roomBPoints.begin(), roomBPoints.end(), 
                    [](const auto& a, const auto& b) { return a.second < b.second; });
                
                // 限制为前N个点
                if (roomBPoints.size() > MAX_POINTS_TO_CONSIDER) {
                    roomBPoints.resize(MAX_POINTS_TO_CONSIDER);
                }
                
                // 从这些点中找出两个房间的共有边界点（或相距非常近的点）
                std::vector<std::pair<topo_geometry::point, topo_geometry::point>> sharedPoints;
                
                for (const auto& pointA_pair : roomAPoints) {
                    for (const auto& pointB_pair : roomBPoints) {
                        const auto& pointACandidate = pointA_pair.first;
                        const auto& pointBCandidate = pointB_pair.first;
                        
                        double pointDistance = boost::geometry::distance(pointACandidate, pointBCandidate);
                        if (pointDistance < POINT_PROXIMITY_THRESHOLD) {
                            sharedPoints.push_back(std::make_pair(pointACandidate, pointBCandidate));
                        }
                    }
                }
                
                // 找到两个点作为通道端点
                topo_geometry::point pointA, pointB;
                
                // 如果找到了至少两对共有边界点，选择相距最远的两对
                if (sharedPoints.size() >= 2) {
                    double maxDist = 0;
                    size_t maxI = 0, maxJ = 1;
                    
                    for (size_t i = 0; i < sharedPoints.size(); ++i) {
                        for (size_t j = i + 1; j < sharedPoints.size(); ++j) {
                            double dist = boost::geometry::distance(sharedPoints[i].first, sharedPoints[j].first);
                            if (dist > maxDist) {
                                maxDist = dist;
                                maxI = i;
                                maxJ = j;
                            }
                        }
                    }
                    
                    pointA = sharedPoints[maxI].first;
                    pointB = sharedPoints[maxJ].first;
                } 
                else if (sharedPoints.size() == 1) {
                    pointA = sharedPoints[0].first;
                    
                    double maxDist = 0;
                    for (const auto& pointB_pair : roomBPoints) {
                        double dist = boost::geometry::distance(pointA, pointB_pair.first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            pointB = pointB_pair.first;
                        }
                    }
                    
                    if (maxDist < 0.01) {
                        for (const auto& pointA_pair : roomAPoints) {
                            double dist = boost::geometry::distance(pointA, pointA_pair.first);
                            if (dist > maxDist) {
                                maxDist = dist;
                                pointB = pointA_pair.first;
                            }
                        }
                    }
                }
                else {
                    if (!roomAPoints.empty() && !roomBPoints.empty()) {
                        pointA = roomAPoints[0].first;
                        pointB = roomBPoints[0].first;
                    }
                    else if (!passageEdge->line.cwline.empty()) {
                        pointA = passageEdge->line.cwline.front();
                        pointB = passageEdge->line.cwline.back();
                    }
                    else {
                        pointA = passageEdge->position;
                        double newX = topo_geometry::getX(passageEdge->position) + 0.01;
                        double newY = topo_geometry::getY(passageEdge->position) + 0.01;
                        pointB = topo_geometry::point(newX, newY);
                    }
                }
                
                // 收集通道端点信息
                PassageEndpoints endpoints;
                endpoints.pointA = pointA;
                endpoints.pointB = pointB;
                endpoints.roomA = roomA;
                endpoints.roomB = roomB;
                allPassages.push_back(endpoints);
            }
        }
    }
    
    // 第二步：优化每个房间的多边形
    for (auto roomVtx : areaGraph->originSet) {
        // 收集与该房间相关的所有通道端点
        std::vector<topo_geometry::point> passagePoints;
        for (const auto& passage : allPassages) {
            if (passage.roomA == roomVtx) {
                passagePoints.push_back(passage.pointA);
                passagePoints.push_back(passage.pointB);
            }
            else if (passage.roomB == roomVtx) {
                passagePoints.push_back(passage.pointA);
                passagePoints.push_back(passage.pointB);
            }
        }
        
        // 如果没有通道端点，跳过优化
        if (passagePoints.empty()) {
            continue;
        }
        
        // 为每对通道端点创建映射，用于后续处理
        std::vector<std::pair<topo_geometry::point, topo_geometry::point>> passageEndpointPairs;
        
        // 找出属于同一通道的端点对
        for (const auto& passage : allPassages) {
            if (passage.roomA == roomVtx || passage.roomB == roomVtx) {
                passageEndpointPairs.push_back(std::make_pair(passage.pointA, passage.pointB));
            }
        }
        
        // 先确保通道端点在房间多边形中
        std::list<topo_geometry::point> tempPolygon = roomVtx->polygon;
        
        // 先插入所有通道端点（如果尚未存在）
        for (const auto& passagePoint : passagePoints) {
            bool found = false;
            for (const auto& polygonPoint : tempPolygon) {
                if (GeometryUtils::equalLineVertex(passagePoint, polygonPoint)) {
                    found = true;
                    break;
                }
            }
            
            if (!found) {
                // 找到最近的边并插入
                auto it = tempPolygon.begin();
                auto itNext = std::next(it);
                double minDist = std::numeric_limits<double>::max();
                auto bestPos = tempPolygon.end();
                
                while (itNext != tempPolygon.end()) {
                    double dist = boost::geometry::distance(*it, passagePoint) + 
                                 boost::geometry::distance(*itNext, passagePoint);
                    if (dist < minDist) {
                        minDist = dist;
                        bestPos = itNext;
                    }
                    ++it;
                    ++itNext;
                }
                
                double lastDist = boost::geometry::distance(tempPolygon.back(), passagePoint) + 
                               boost::geometry::distance(tempPolygon.front(), passagePoint);
                if (lastDist < minDist) {
                    bestPos = tempPolygon.begin();
                }
                
                if (bestPos != tempPolygon.end()) {
                    tempPolygon.insert(bestPos, passagePoint);
                }
            }
        }
        
        // 根据通道端点对重构多边形
        std::list<topo_geometry::point> optimizedPolygon;
        bool needsOptimization = !passageEndpointPairs.empty();
        
        if (needsOptimization) {
            // 将多边形转换为vector以便索引访问
            std::vector<topo_geometry::point> polygonPoints(tempPolygon.begin(), tempPolygon.end());
            int n = polygonPoints.size();
            
            // 找出所有通道端点在多边形中的索引位置
            std::map<topo_geometry::point, int, topo_geometry::Smaller> pointToIndex;
            for (int i = 0; i < n; ++i) {
                for (const auto& passagePoint : passagePoints) {
                    if (GeometryUtils::equalLineVertex(polygonPoints[i], passagePoint)) {
                        pointToIndex[passagePoint] = i;
                        break;
                    }
                }
            }
            
            // 创建保留点的mask
            std::vector<bool> keepPoint(n, true);
            
            // 对每对通道端点，删除它们之间的点（选择较短的路径）
            for (const auto& endpointPair : passageEndpointPairs) {
                // 找到点在多边形中的索引位置
                int idx1 = -1, idx2 = -1;
                
                // 手动查找索引，因为直接使用map的find可能会因为浮点比较精度问题失败
                for (int i = 0; i < n; ++i) {
                    if (GeometryUtils::equalLineVertex(polygonPoints[i], endpointPair.first)) {
                        idx1 = i;
                    }
                    if (GeometryUtils::equalLineVertex(polygonPoints[i], endpointPair.second)) {
                        idx2 = i;
                    }
                }
                
                // 确认两个端点都在多边形中
                if (idx1 != -1 && idx2 != -1) {
                    // 确保idx1 < idx2，如果需要则交换
                    if (idx1 > idx2) {
                        std::swap(idx1, idx2);
                    }
                    
                    // 计算两种路径的长度：idx1->idx2 和 idx2->idx1+n
                    int path1Length = idx2 - idx1 - 1;
                    int path2Length = (idx1 + n) - idx2 - 1;
                    
                    if (path1Length < path2Length) {
                        // 删除第一条路径上的点
                        for (int i = idx1 + 1; i < idx2; ++i) {
                            keepPoint[i] = false;
                        }
                    } else {
                        // 删除第二条路径上的点
                        for (int i = idx2 + 1; i < idx1 + n; ++i) {
                            keepPoint[i % n] = false;
                        }
                    }
                }
            }
            
            // 根据keepPoint构建新的多边形
            for (int i = 0; i < n; ++i) {
                if (keepPoint[i]) {
                    optimizedPolygon.push_back(polygonPoints[i]);
                }
            }
        } else {
            // 如果没有需要优化的通道端点对，使用tempPolygon
            optimizedPolygon = tempPolygon;
        }
        
        // 确保多边形仍然闭合
        if (!optimizedPolygon.empty() && !GeometryUtils::equalLineVertex(optimizedPolygon.front(), optimizedPolygon.back())) {
            optimizedPolygon.push_back(optimizedPolygon.front());
        }
        
        // 更新房间的多边形
        roomVtx->polygon = optimizedPolygon;
    }
}

// 收集通道端点信息
std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, 
                     std::pair<roomVertex*, roomVertex*>>> 
collectPassagePoints(AreaGraph* areaGraph) {
    std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, 
                         std::pair<roomVertex*, roomVertex*>>> passagePoints;
    
    // 遍历所有通道，找出并记录它们的端点
    for (auto passageEdge : areaGraph->passageEList) {
        // 只处理连接两个房间的通道
        if (passageEdge->connectedAreas.size() == 2) {
            roomVertex* roomA = passageEdge->connectedAreas[0];
            roomVertex* roomB = passageEdge->connectedAreas[1];
            
            // 找到两个房间共有边界点中相距最远的两个点作为通道两端
            topo_geometry::point pointA, pointB;
            
            // 定义判断两个点是否接近的阈值
            const double POINT_PROXIMITY_THRESHOLD = 0.5; // 根据实际坐标系调整
            
            // 计算通道附近的点（取两个房间中到通道距离最小的前N个点）
            const int MAX_POINTS_TO_CONSIDER = 10;
            std::vector<std::pair<topo_geometry::point, double>> roomAPoints, roomBPoints;
            
            // 收集房间A中距离通道最近的点
            for (const auto& point : roomA->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomAPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomAPoints.begin(), roomAPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomAPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomAPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 收集房间B中距离通道最近的点
            for (const auto& point : roomB->polygon) {
                double dist = boost::geometry::distance(point, passageEdge->position);
                roomBPoints.push_back(std::make_pair(point, dist));
            }
            
            // 按距离排序
            std::sort(roomBPoints.begin(), roomBPoints.end(), 
                [](const auto& a, const auto& b) { return a.second < b.second; });
            
            // 限制为前N个点
            if (roomBPoints.size() > MAX_POINTS_TO_CONSIDER) {
                roomBPoints.resize(MAX_POINTS_TO_CONSIDER);
            }
            
            // 从这些点中找出两个房间的共有边界点（或相距非常近的点）
            std::vector<std::pair<topo_geometry::point, topo_geometry::point>> sharedPoints;
            
            for (const auto& pointA_pair : roomAPoints) {
                for (const auto& pointB_pair : roomBPoints) {
                    const auto& pointACandidate = pointA_pair.first;
                    const auto& pointBCandidate = pointB_pair.first;
                    
                    double pointDistance = boost::geometry::distance(pointACandidate, pointBCandidate);
                    if (pointDistance < POINT_PROXIMITY_THRESHOLD) {
                        // 这两个点尽管不完全相同，但很接近，可以视为共有边界点
                        sharedPoints.push_back(std::make_pair(pointACandidate, pointBCandidate));
                    }
                }
            }
            
            // 如果找到了至少两对共有边界点，选择相距最远的两对
            if (sharedPoints.size() >= 2) {
                double maxDist = 0;
                size_t maxI = 0, maxJ = 1;
                
                for (size_t i = 0; i < sharedPoints.size(); ++i) {
                    for (size_t j = i + 1; j < sharedPoints.size(); ++j) {
                        double dist = boost::geometry::distance(sharedPoints[i].first, sharedPoints[j].first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            maxI = i;
                            maxJ = j;
                        }
                    }
                }
                
                // 使用相距最远的两对点
                pointA = sharedPoints[maxI].first;
                pointB = sharedPoints[maxJ].first;
            } 
            // 如果只有一对共有边界点，使用这对点和另一个房间的点
            else if (sharedPoints.size() == 1) {
                pointA = sharedPoints[0].first;
                
                // 根据距离选择另一个房间的点（与所选的共有点相距最远的点）
                double maxDist = 0;
                
                for (const auto& pointB_pair : roomBPoints) {
                    double dist = boost::geometry::distance(pointA, pointB_pair.first);
                    if (dist > maxDist) {
                        maxDist = dist;
                        pointB = pointB_pair.first;
                    }
                }
                
                if (maxDist < 0.01) { // 如果没找到合适的点
                    for (const auto& pointA_pair : roomAPoints) {
                        double dist = boost::geometry::distance(pointA, pointA_pair.first);
                        if (dist > maxDist) {
                            maxDist = dist;
                            pointB = pointA_pair.first;
                        }
                    }
                }
            }
            // 如果没有共有边界点，使用每个房间距离通道最近的点
            else {
                if (!roomAPoints.empty() && !roomBPoints.empty()) {
                    pointA = roomAPoints[0].first;
                    pointB = roomBPoints[0].first;
                }
                // 如果集合为空，使用通道的线段端点（如果有）
                else if (!passageEdge->line.cwline.empty()) {
                    pointA = passageEdge->line.cwline.front();
                    pointB = passageEdge->line.cwline.back();
                }
                // 最后的备用方案，使用通道位置和偏移点
                else {
                    pointA = passageEdge->position;
                    double newX = topo_geometry::getX(passageEdge->position) + 0.01;
                    double newY = topo_geometry::getY(passageEdge->position) + 0.01;
                    pointB = topo_geometry::point(newX, newY);
                }
            }
            
            // 添加到结果中
            passagePoints.push_back(std::make_pair(
                std::make_pair(pointA, pointB),
                std::make_pair(roomA, roomB)));
        }
    }
    
    return passagePoints;
}

} // namespace PassageProcessor
} // namespace RMG
