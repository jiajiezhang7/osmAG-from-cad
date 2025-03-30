#include "roomGraph.h"
#include "RoomDect.h"
#include "utils/ParamsLoader.h"
#include <algorithm>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <vector>
#include <limits>

// 判断两个点是否相等（考虑浮点误差）
static bool equalLineVertex(const topo_geometry::point &a, const topo_geometry::point &b) {
    const double EPSILON = 1e-6;
    return boost::geometry::distance(a, b) < EPSILON;
}


// 计算多边形面积
static double calc_poly_area(std::list<topo_geometry::point> &polygon) {
    double area = 0;
    std::list<topo_geometry::point>::iterator itj = polygon.end();
    itj--;
    for (std::list<topo_geometry::point>::iterator it = polygon.begin(); it != polygon.end(); it++) {
        area += ((topo_geometry::getX(*itj) * topo_geometry::getY(*it)) -
                 (topo_geometry::getY(*itj) * topo_geometry::getX(*it)));
        itj = it;
    }
    return std::abs(area / 2.0);
}

// 将笛卡尔坐标转换为经纬度
static std::pair<double, double> cartesianToLatLon(double x, double y, const topo_geometry::point& root_point)
{
    // 坐标缩放因子(根据实际地图大小调整)
    const double SCALE_FACTOR = 0.001;
    
    // 计算相对于根节点的偏移量，并转换为经纬度
    double lat = topo_geometry::getY(root_point) + y * SCALE_FACTOR;
    double lon = topo_geometry::getX(root_point) + x * SCALE_FACTOR;
    
    return std::make_pair(lat, lon);
}

// 优化房间多边形，使通道与房间边界重合
void RMG::AreaGraph::optimizeRoomPolygonsForPassages(const std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, std::pair<roomVertex*, roomVertex*>>>* precomputedPassagePoints)
{
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
        for (auto passageEdge : passageEList) {
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
    for (auto roomVtx : originSet) {
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
                if (equalLineVertex(passagePoint, polygonPoint)) {
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
                    if (equalLineVertex(polygonPoints[i], passagePoint)) {
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
                    if (equalLineVertex(polygonPoints[i], endpointPair.first)) {
                        idx1 = i;
                    }
                    if (equalLineVertex(polygonPoints[i], endpointPair.second)) {
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
        if (!optimizedPolygon.empty() && !equalLineVertex(optimizedPolygon.front(), optimizedPolygon.back())) {
            optimizedPolygon.push_back(optimizedPolygon.front());
        }
        
        // 更新房间的多边形
        roomVtx->polygon = optimizedPolygon;
    }
}

// 去除originSet中形状相同的多边形
void RMG::AreaGraph::removeDuplicatePolygons() {
    if (originSet.empty()) {
        return;
    }
    
    // 使用哈希表存储多边形的哈希值和对应的roomVertex
    // 哈希值基于多边形的形状，而不是roomId
    std::map<size_t, std::vector<roomVertex*>> polygonHash;
    
    // 计算每个多边形的哈希值
    for (auto roomVtx : originSet) {
        // 如果多边形为空，跳过
        if (roomVtx->polygon.empty()) {
            continue;
        }
        
        // 计算多边形的哈希值
        size_t hash = calculatePolygonHash(roomVtx->polygon);
        
        // 将roomVertex添加到对应哈希值的列表中
        polygonHash[hash].push_back(roomVtx);
    }
    
    // 标记要删除的roomVertex
    std::vector<roomVertex*> toRemove;
    
    // 处理每个哈希值对应的roomVertex列表
    for (auto& pair : polygonHash) {
        auto& vertices = pair.second;
        
        // 如果只有一个roomVertex，不需要处理
        if (vertices.size() <= 1) {
            continue;
        }
        
        // 验证多边形是否真的相同（哈希碰撞检查）
        for (size_t i = 0; i < vertices.size(); ++i) {
            for (size_t j = i + 1; j < vertices.size(); ++j) {
                if (arePolygonsEqual(vertices[i]->polygon, vertices[j]->polygon)) {
                    // 确认多边形相同，保留roomId较小的那个
                    if (vertices[i]->roomId > vertices[j]->roomId) {
                        // 将vertices[i]标记为要删除
                        toRemove.push_back(vertices[i]);
                        
                        // 将vertices[i]的通道转移给vertices[j]
                        transferPassages(vertices[i], vertices[j]);
                        break;
                    } else {
                        // 将vertices[j]标记为要删除
                        toRemove.push_back(vertices[j]);
                        
                        // 将vertices[j]的通道转移给vertices[i]
                        transferPassages(vertices[j], vertices[i]);
                    }
                }
            }
        }
    }
    
    // 从originSet中删除标记的roomVertex
    for (auto roomVtx : toRemove) {
        originSet.erase(std::remove(originSet.begin(), originSet.end(), roomVtx), originSet.end());
        delete roomVtx; // 释放内存
    }
    
    std::cout << "已删除 " << toRemove.size() << " 个重复多边形" << std::endl;
}

// 计算多边形的哈希值
size_t RMG::AreaGraph::calculatePolygonHash(const std::list<topo_geometry::point>& polygon) {
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
    double area = calc_poly_area(const_cast<std::list<topo_geometry::point>&>(polygon));
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
    if (!polygon.empty() && !equalLineVertex(polygon.front(), polygon.back())) {
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
bool RMG::AreaGraph::arePolygonsEqual(const std::list<topo_geometry::point>& poly1, const std::list<topo_geometry::point>& poly2) {
    // 如果顶点数量不同，多边形不同
    if (poly1.size() != poly2.size()) {
        return false;
    }
    
    // 如果多边形为空，认为相同
    if (poly1.empty() && poly2.empty()) {
        return true;
    }
    
    // 计算多边形的面积和周长
    double area1 = calc_poly_area(const_cast<std::list<topo_geometry::point>&>(poly1));
    double area2 = calc_poly_area(const_cast<std::list<topo_geometry::point>&>(poly2));
    
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

// 将一个roomVertex的通道转移给另一个roomVertex
void RMG::AreaGraph::transferPassages(roomVertex* source, roomVertex* target) {
    // 遍历source的所有通道
    for (auto passage : source->passages) {
        // 检查target是否已经有这个通道
        bool passageExists = false;
        for (auto targetPassage : target->passages) {
            if (targetPassage == passage) {
                passageExists = true;
                break;
            }
        }
        
        // 如果target没有这个通道，添加它
        if (!passageExists) {
            target->passages.push_back(passage);
        }
        
        // 在通道的connectedAreas中，将source替换为target
        for (size_t i = 0; i < passage->connectedAreas.size(); ++i) {
            if (passage->connectedAreas[i] == source) {
                // 检查target是否已经在connectedAreas中
                bool targetExists = false;
                for (auto area : passage->connectedAreas) {
                    if (area == target) {
                        targetExists = true;
                        break;
                    }
                }
                
                if (targetExists) {
                    // 如果target已经存在，删除source
                    passage->connectedAreas.erase(passage->connectedAreas.begin() + i);
                    i--; // 调整索引
                } else {
                    // 否则，将source替换为target
                    passage->connectedAreas[i] = target;
                }
            }
        }
    }
    
    // 清空source的通道列表，防止删除时出现问题
    source->passages.clear();
}

// 将AreaGraph导出为osmAG.xml格式
void RMG::AreaGraph::exportToOsmAG(const std::string& filename,
                               bool simplify_enabled, double simplify_tolerance,
                               bool spike_removal_enabled, double spike_angle_threshold, 
                               double spike_distance_threshold)
{
    // 添加调试信息
    std::cout << "开始导出AreaGraph到" << filename << std::endl;
    
    // 输出优化前的房间信息
    std::cout << "优化前房间数量: " << originSet.size() << std::endl;
    
    // 去除重复多边形
    removeDuplicatePolygons();
    std::cout << "去重后房间数量: " << originSet.size() << std::endl;

    // 用于收集通道端点信息，后续传给优化函数
    std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, std::pair<roomVertex*, roomVertex*>>> passagePointsForOptimization;
    
    // 创建XML文档
    std::ofstream osmFile(filename);
    osmFile << "<?xml version='1.0' encoding='UTF-8'?>\n";
    osmFile << "<osm version='0.6' generator='AreaGraph'>\n";
    
    // 创建一个负整数ID生成器(避免与OSM实际数据冲突)
    int nextId = -1;
    std::map<topo_geometry::point, int, topo_geometry::Smaller> pointToNodeId;
    
    // 1. 创建根节点作为坐标原点(0,0)
    // 直接使用构造函数创建点，不使用setX和setY
    topo_geometry::point root_point(0.01, 0.01);
    int rootId = nextId--;
    osmFile << "  <node id='" << rootId << "' action='modify' visible='true' lat='" 
            << topo_geometry::getY(root_point) << "' lon='" << topo_geometry::getX(root_point) << "'>\n";
    osmFile << "    <tag k='name' v='root' />\n";
    osmFile << "  </node>\n";
    
    // 2. 收集所有房间的点（仅使用优化后的多边形）
    std::map<roomVertex*, std::vector<int>> roomVertexToNodeIds;
    
    // 3. 创建房间way的ID映射
    int nextWayId = -1;
    std::map<roomVertex*, int> roomToWayId;
    
    for (auto roomVtx : originSet) {
        int wayId = nextWayId--;
        roomToWayId[roomVtx] = wayId;
    }
    
    // 4. 获取所有通道端点信息
    struct PassagePoint {
        topo_geometry::point point;
        roomVertex* roomA;
        roomVertex* roomB;
        int nodeId;
    };
    
    std::vector<std::pair<PassagePoint, PassagePoint>> passagePoints;
    
    // 遍历所有通道，找出并记录它们的正确端点
    for (auto passageEdge : passageEList) {
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
            
            // 检查端点是否已存在，否则创建新节点
            int nodeIdA = -1;
            int nodeIdB = -1;
            
            // 查找点A是否存在
            bool pointAExists = false;
            for (const auto& pair : pointToNodeId) {
                if (equalLineVertex(pair.first, pointA)) {
                    pointAExists = true;
                    nodeIdA = pair.second;
                    break;
                }
            }
            
            if (!pointAExists) {
                nodeIdA = nextId--;
                pointToNodeId[pointA] = nodeIdA;
                
                auto latLon = cartesianToLatLon(topo_geometry::getX(pointA), topo_geometry::getY(pointA), root_point);
                osmFile << "  <node id='" << nodeIdA << "' action='modify' visible='true' lat='" 
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }
            
            // 查找点B是否存在
            bool pointBExists = false;
            if (!equalLineVertex(pointA, pointB)) { // 只有当点A和点B不同时才查找点B
                for (const auto& pair : pointToNodeId) {
                    if (equalLineVertex(pair.first, pointB)) {
                        pointBExists = true;
                        nodeIdB = pair.second;
                        break;
                    }
                }
                
                if (!pointBExists) {
                    nodeIdB = nextId--;
                    pointToNodeId[pointB] = nodeIdB;
                    
                    auto latLon = cartesianToLatLon(topo_geometry::getX(pointB), topo_geometry::getY(pointB), root_point);
                    osmFile << "  <node id='" << nodeIdB << "' action='modify' visible='true' lat='" 
                            << latLon.first << "' lon='" << latLon.second << "' />\n";
                }
            } else {
                // 如果点A和点B相同，则使用相同的nodeId
                nodeIdB = nodeIdA;
            }
            
            // 在这里记录通道端点信息，但先不创建通道way
            PassagePoint ptA, ptB;
            
            ptA.point = pointA;
            ptA.roomA = roomA;
            ptA.roomB = roomB;
            ptA.nodeId = nodeIdA;
            
            ptB.point = pointB;
            ptB.roomA = roomA;
            ptB.roomB = roomB;
            ptB.nodeId = nodeIdB;
            
            passagePoints.push_back(std::make_pair(ptA, ptB));
            
            // 同时收集端点信息用于多边形优化
            passagePointsForOptimization.push_back(std::make_pair(
                std::make_pair(pointA, pointB),
                std::make_pair(roomA, roomB)));
            
        }
    }
    
    // 遍历所有通道，找出并记录它们的端点
    
    // 在这里调用优化函数，传入预计算的通道端点信息
    optimizeRoomPolygonsForPassages(&passagePointsForOptimization);
    
    // 输出优化后的房间信息
    std::cout << "优化后房间数量: " << originSet.size() << std::endl;
    
    // 收集需要保留的通道端点
    std::vector<topo_geometry::point> preservePoints;
    for (const auto& passage : passagePointsForOptimization) {
        preservePoints.push_back(passage.first.first);  // 第一个端点
        preservePoints.push_back(passage.first.second); // 第二个端点
    }

    // 根据参数决定是否进行多边形简化
    if (simplify_enabled) {
        // 在通道端点优化后进行多边形简化，保留通道端点
        simplifyPolygons(simplify_tolerance, &preservePoints);
        std::cout << "多边形简化完成，使用参数tolerance=" << simplify_tolerance 
                  << "，已保留" << preservePoints.size() << "个通道端点" << std::endl;
    } else {
        std::cout << "跳过多边形简化处理" << std::endl;
    }
    
    // 根据参数决定是否进行毛刺去除
    if (spike_removal_enabled) {
        // 移除房间多边形中的“毛刺”和尖角
        removeSpikesFromPolygons(spike_angle_threshold, spike_distance_threshold, &preservePoints);
        std::cout << "多边形平滑完成，使用参数angle_threshold=" << spike_angle_threshold 
                  << ", distance_threshold=" << spike_distance_threshold << std::endl;
    } else {
        std::cout << "跳过毛刺去除处理" << std::endl;
    }
    
    // 遍历所有房间，生成节点ID（使用优化后的多边形）
    for (auto roomVtx : originSet) {
        std::vector<int> nodeIds;
        
        // 从优化后的房间多边形中提取所有点
        for (auto it = roomVtx->polygon.begin(); it != roomVtx->polygon.end(); ++it) {
            topo_geometry::point point = *it;
            
            // 检查这个点是否已经创建过
            bool pointExists = false;
            int nodeId = nextId;
            
            for (const auto& pair : pointToNodeId) {
                if (equalLineVertex(pair.first, point)) {
                    pointExists = true;
                    nodeId = pair.second;
                    break;
                }
            }
            
            if (!pointExists) {
                nodeId = nextId--;
                pointToNodeId[point] = nodeId;
                
                // 转换为经纬度
                auto latLon = cartesianToLatLon(topo_geometry::getX(point), topo_geometry::getY(point), root_point);
                
                // 写入节点
                osmFile << "  <node id='" << nodeId << "' action='modify' visible='true' lat='" 
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }
            
            nodeIds.push_back(nodeId);
        }
        
        roomVertexToNodeIds[roomVtx] = nodeIds;
    }
    
    // 输出所有房间way，仅使用优化后的多边形
    // 创建一个集合来跟踪已经处理过的房间ID
    std::set<int> processedRoomIds;
    
    // 在这里 originSet中已经有了“重复“”的多边形
    for (auto roomVtx : originSet) {
        
        // 记录这个房间ID已经被处理
        processedRoomIds.insert(roomVtx->roomId);
        
        int wayId = roomToWayId[roomVtx];
        
        osmFile << "  <way id='" << wayId << "' action='modify' visible='true'>\n";
        
        // 添加所有节点引用
        auto& nodeIds = roomVertexToNodeIds[roomVtx];
        for (int nodeId : nodeIds) {
            osmFile << "    <nd ref='" << nodeId << "' />\n";
        }
        // 确保闭合（第一个点和最后一个点相同）
        if (!nodeIds.empty() && nodeIds.front() != nodeIds.back()) {
            osmFile << "    <nd ref='" << nodeIds.front() << "' />\n";
        }
        
        // 添加房间标签
        osmFile << "    <tag k='indoor' v='room' />\n";
        osmFile << "    <tag k='name' v='room_" << roomVtx->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:areaType' v='room' />\n";
        osmFile << "    <tag k='osmAG:type' v='area' />\n";
        osmFile << "  </way>\n";
    }
    
    // 6. 输出通道way
    int passageCount = 1;
    for (const auto& passage : passagePoints) {
        int wayId = nextWayId--;
        const PassagePoint& ptA = passage.first;
        const PassagePoint& ptB = passage.second;
        
        osmFile << "  <way id='" << wayId << "' action='modify' visible='true'>\n";
        osmFile << "    <nd ref='" << ptA.nodeId << "' />\n";
        
        // 只有当两个点不同时才添加第二个点
        if (ptA.nodeId != ptB.nodeId) {
            osmFile << "    <nd ref='" << ptB.nodeId << "' />\n";
        }
        
        // 添加通道标签
        osmFile << "    <tag k='name' v='p_" << passageCount++ << "' />\n";
        osmFile << "    <tag k='osmAG:from' v='room_" << ptA.roomA->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:to' v='room_" << ptA.roomB->roomId << "' />\n";
        osmFile << "    <tag k='osmAG:type' v='passage' />\n";
        osmFile << "  </way>\n";
    }
    
    // 结束文档
    osmFile << "</osm>\n";
    osmFile.close();
}

// 计算点到线段的距离
double RMG::AreaGraph::pointToLineDistance(const topo_geometry::point& p, const topo_geometry::point& lineStart, const topo_geometry::point& lineEnd) {
    // 如果线段实际上是一个点，直接返回点到这个点的距离
    if (equalLineVertex(lineStart, lineEnd)) {
        return boost::geometry::distance(p, lineStart);
    }
    
    // 计算向量
    double x1 = topo_geometry::getX(lineStart);
    double y1 = topo_geometry::getY(lineStart);
    double x2 = topo_geometry::getX(lineEnd);
    double y2 = topo_geometry::getY(lineEnd);
    double x0 = topo_geometry::getX(p);
    double y0 = topo_geometry::getY(p);
    
    // 计算线段长度的平方
    double lineLength2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    
    // 计算投影比例
    double t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / lineLength2;
    
    // 如果投影在线段外，返回点到线段端点的最小距离
    if (t < 0.0) {
        return boost::geometry::distance(p, lineStart);
    }
    if (t > 1.0) {
        return boost::geometry::distance(p, lineEnd);
    }
    
    // 计算投影点
    double projX = x1 + t * (x2 - x1);
    double projY = y1 + t * (y2 - y1);
    topo_geometry::point projPoint(projX, projY);
    
    // 返回点到投影点的距离
    return boost::geometry::distance(p, projPoint);
}

// Douglas-Peucker算法递归简化多边形一部分
static void douglasPeuckerRecursive(const std::vector<topo_geometry::point>& points, int start, int end, 
                                 double epsilon, std::vector<bool>& keepPoint, 
                                 RMG::AreaGraph* areaGraph) {
    if (end - start <= 1) {
        return;
    }
    
    // 找出最远的点
    double maxDistance = 0.0;
    int furthestIndex = start;
    
    for (int i = start + 1; i < end; ++i) {
        double distance = areaGraph->pointToLineDistance(points[i], points[start], points[end]);
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
// 计算点到质心的距离
double distanceToCenter(const topo_geometry::point& p, double centerX, double centerY) {
    double dx = topo_geometry::getX(p) - centerX;
    double dy = topo_geometry::getY(p) - centerY;
    return std::sqrt(dx*dx + dy*dy);
}

// 检测多边形是否近似圆形
bool isApproximatelyCircular(const std::vector<topo_geometry::point>& points) {
    if (points.size() < 8) return false; // 点太少无法判断是否为圆
    
    // 计算质心
    double centerX = 0, centerY = 0;
    for (const auto& p : points) {
        centerX += topo_geometry::getX(p);
        centerY += topo_geometry::getY(p);
    }
    centerX /= points.size();
    centerY /= points.size();
    
    // 计算到质心的平均距离
    double avgRadius = 0;
    for (const auto& p : points) {
        avgRadius += distanceToCenter(p, centerX, centerY);
    }
    avgRadius /= points.size();
    
    // 计算每个点到质心距离与平均距离的差异
    double variance = 0;
    for (const auto& p : points) {
        double radius = distanceToCenter(p, centerX, centerY);
        variance += (radius - avgRadius) * (radius - avgRadius);
    }
    variance /= points.size();
    
    // 如果方差小，说明点到质心的距离接近一致，可能是圆形
    double relativeVariance = variance / (avgRadius * avgRadius);
    return relativeVariance < 0.05; // 相对方差小于5%可能是圆
}

// 简化单个多边形
std::list<topo_geometry::point> RMG::AreaGraph::simplifyPolygon(const std::list<topo_geometry::point>& polygon, double epsilon, const std::vector<topo_geometry::point>* preservePoints) {
    if (polygon.size() <= 3) {
        return polygon; // 不能再简化
    }
    
    // 转换为向量便于索引访问
    std::vector<topo_geometry::point> points(polygon.begin(), polygon.end());
    int n = points.size();
    
    // 检测多边形是否近似圆形
    bool isCircular = isApproximatelyCircular(points);
    
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
                if (equalLineVertex(points[i], preservePoint) || 
                    boost::geometry::distance(points[i], preservePoint) < PRESERVE_THRESHOLD) {
                    keepPoint[i] = true;
                    break;
                }
            }
        }
    }
    
    // 应用Douglas-Peucker算法，使用调整后的epsilon值
    douglasPeuckerRecursive(points, 0, n-1, effectiveEpsilon, keepPoint, this);
    
    // 根据标记建立简化后的多边形
    std::list<topo_geometry::point> simplifiedPolygon;
    for (int i = 0; i < n; ++i) {
        if (keepPoint[i]) {
            simplifiedPolygon.push_back(points[i]);
        }
    }
    
    // 确保多边形闭合
    if (!simplifiedPolygon.empty() && !equalLineVertex(simplifiedPolygon.front(), simplifiedPolygon.back())) {
        simplifiedPolygon.push_back(simplifiedPolygon.front());
    }
    
    return simplifiedPolygon;
}

// 简化所有房间多边形
void RMG::AreaGraph::simplifyPolygons(double epsilon, const std::vector<topo_geometry::point>* preservePoints) {
    // 输出简化前的点数量统计
    int totalPointsBefore = 0;
    for (auto roomVtx : originSet) {
        totalPointsBefore += roomVtx->polygon.size();
    }
    
    // 对每个房间多边形进行简化
    for (auto roomVtx : originSet) {
        roomVtx->polygon = simplifyPolygon(roomVtx->polygon, epsilon, preservePoints);
    }
    
    // 输出简化后的点数量统计
    int totalPointsAfter = 0;
    for (auto roomVtx : originSet) {
        totalPointsAfter += roomVtx->polygon.size();
    }
    
    std::cout << "多边形简化: 原有" << totalPointsBefore << "个点，简化后" << totalPointsAfter 
              << "个点，减少" << (totalPointsBefore - totalPointsAfter) << "个点 (" 
              << (100.0 * (totalPointsBefore - totalPointsAfter) / totalPointsBefore) << "%)" << std::endl;
}

/**
 * 移除多边形中的"毛刺"
 * 
 * 参数调整指南:
 * 1. 角度阈值(angleThreshold)
 *    - 默认值: 15.0
 *    - 范围: 5.0-30.0
 *    - 越小越激进，会移除更多与90度偏差小的角
 *    - 极端值: 8.0 (非常激进)
 * 
 * 2. 距离阈值(distanceThreshold)
 *    - 默认值: 0.15
 *    - 范围: 0.05-0.3
 *    - 越大越激进，会移除更多距离直线较远的点
 *    - 极端值: 0.3 (非常激进)
 * 
 * 3. 针对特定毛刺类型的调整:
 *    - 针对尖角: 在代码中修改 "angle < 30.0" 为更大的值(如 40.0)
 *    - 针对钝角: 在代码中修改 "angle > 150.0" 为更小的值(如 140.0)
 *    - 针对长毛刺: 在代码中增大 "(distance / minVectorLen) < 0.1" 中的比例值
 * 
 * 4. 极端情况下的组合参数:
 *    - 最激进: angleThreshold=8.0, distanceThreshold=0.3
 *    - 中等: angleThreshold=15.0, distanceThreshold=0.15
 *    - 保守: angleThreshold=30.0, distanceThreshold=0.05
 * 
 * 5. 对于特别顶固的毛刺，可以考虑多次迭代应用算法
 * 
 * 注意: 参数过于激进可能会过度简化多边形，导致有意义的形状丢失
 */
void RMG::AreaGraph::removeSpikesFromPolygons(double angleThreshold, double distanceThreshold, 
                                          const std::vector<topo_geometry::point>* preservePoints) {
    // 输出处理前的点数量统计
    int totalPointsBefore = 0;
    for (auto roomVtx : originSet) {
        totalPointsBefore += roomVtx->polygon.size();
    }
    
    // 对每个房间多边形进行处理
    for (auto roomVtx : originSet) {
        roomVtx->polygon = removeSpikesFromPolygon(roomVtx->polygon, angleThreshold, distanceThreshold, preservePoints);
    }
    
    // 输出处理后的点数量统计
    int totalPointsAfter = 0;
    for (auto roomVtx : originSet) {
        totalPointsAfter += roomVtx->polygon.size();
    }
    
    std::cout << "多边形毛刺移除: 原有" << totalPointsBefore << "个点，处理后" << totalPointsAfter 
              << "个点，减少" << (totalPointsBefore - totalPointsAfter) << "个点 (" 
              << (100.0 * (totalPointsBefore - totalPointsAfter) / totalPointsBefore) << "%)" << std::endl;
}




// 计算局部曲率
double calculateLocalCurvature(const std::vector<topo_geometry::point>& points, int index, int windowSize = 5) {
    int n = points.size();
    double totalAngleChange = 0;
    
    for (int i = 1; i < windowSize; i++) {
        int prev = (index - i + n) % n;
        int curr = (index - i + 1 + n) % n;
        int next = (index - i + 2 + n) % n;
        
        // 计算相邻三点的角度
        double ax = topo_geometry::getX(points[prev]) - topo_geometry::getX(points[curr]);
        double ay = topo_geometry::getY(points[prev]) - topo_geometry::getY(points[curr]);
        double bx = topo_geometry::getX(points[next]) - topo_geometry::getX(points[curr]);
        double by = topo_geometry::getY(points[next]) - topo_geometry::getY(points[curr]);
        
        double lenA = std::sqrt(ax*ax + ay*ay);
        double lenB = std::sqrt(bx*bx + by*by);
        
        if (lenA < 1e-6 || lenB < 1e-6) continue;
        
        ax /= lenA; ay /= lenA;
        bx /= lenB; by /= lenB;
        
        double dotProduct = ax*bx + ay*by;
        dotProduct = std::max(-1.0, std::min(1.0, dotProduct));
        
        double angle = std::acos(dotProduct) * 180.0 / M_PI;
        totalAngleChange += std::abs(angle - 180.0); // 计算与直线的偏差
    }
    
    return totalAngleChange / windowSize;
}

// 检测是否是平滑曲线的一部分
bool isPartOfSmoothCurve(const std::vector<topo_geometry::point>& points, int index, int windowSize = 5) {
    double curvature = calculateLocalCurvature(points, index, windowSize);
    
    // 如果局部曲率在一个合理范围内，可能是平滑曲线的一部分
    // 曲率太小表示直线，曲率太大表示尖角
    return curvature > 5.0 && curvature < 30.0;
}

// 移除单个多边形中的“毛刺”
std::list<topo_geometry::point> RMG::AreaGraph::removeSpikesFromPolygon(
                            const std::list<topo_geometry::point>& polygon, 
                            double angleThreshold, double distanceThreshold,
                            const std::vector<topo_geometry::point>* preservePoints) {
    if (polygon.size() <= 3) {
        return polygon; // 不能再简化
    }
    
    // 将多边形转换为向量便于索引访问
    std::vector<topo_geometry::point> points(polygon.begin(), polygon.end());
    int n = points.size();
    
    // 检测多边形是否近似圆形
    bool isCircular = isApproximatelyCircular(points);
    
    // 根据多边形特征调整阈值
    double effectiveAngleThreshold = isCircular ? angleThreshold * 0.5 : angleThreshold;
    double effectiveDistanceThreshold = isCircular ? distanceThreshold * 2.0 : distanceThreshold;
    
    // if (isCircular) {
    //     std::cout << "检测到圆形多边形，使用保守参数" << std::endl;
    // }
    
    // 标记需要保留的点
    std::vector<bool> keepPoint(n, true);
    
    // 处理保留点列表
    std::vector<int> preserveIndices;
    if (preservePoints != nullptr && !preservePoints->empty()) {
        const double PRESERVE_THRESHOLD = 1e-6; // 保留点判断阈值
        
        for (int i = 0; i < n; ++i) {
            for (const auto& preservePoint : *preservePoints) {
                if (equalLineVertex(points[i], preservePoint) || 
                    boost::geometry::distance(points[i], preservePoint) < PRESERVE_THRESHOLD) {
                    preserveIndices.push_back(i);
                    break;
                }
            }
        }
    }
    
    // 使用cmath中的M_PI常量
    #include <cmath>
    
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
        double distance = pointToLineDistance(points[curr], points[prev], points[next]);
        
        // 检测是否是平滑曲线的一部分
        bool isCurve = isPartOfSmoothCurve(points, curr);
        
        // 判断是否是“毛刺”
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
    if (!smoothedPolygon.empty() && !equalLineVertex(smoothedPolygon.front(), smoothedPolygon.back())) {
        smoothedPolygon.push_back(smoothedPolygon.front());
    }
    
    return smoothedPolygon;
}
