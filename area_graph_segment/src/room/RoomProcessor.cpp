#include "room/RoomProcessor.h"
#include "geometry/GeometryUtils.h"
#include "polygon/PolygonProcessor.h"
#include "utils/ParamsLoader.h"
#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <iomanip>
#include <fstream>

namespace RMG {
namespace RoomProcessor {

// 去除originSet中形状相同的多边形
void removeDuplicatePolygons(AreaGraph* areaGraph) {
    if (areaGraph->originSet.empty()) {
        return;
    }
    
    // 使用哈希表存储多边形的哈希值和对应的roomVertex
    // 哈希值基于多边形的形状，而不是roomId
    std::map<size_t, std::vector<roomVertex*>> polygonHash;
    
    // 计算每个多边形的哈希值
    for (auto roomVtx : areaGraph->originSet) {
        // 如果多边形为空，跳过
        if (roomVtx->polygon.empty()) {
            continue;
        }
        
        // 计算多边形的哈希值
        size_t hash = PolygonProcessor::calculatePolygonHash(roomVtx->polygon);
        
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
                if (PolygonProcessor::arePolygonsEqual(vertices[i]->polygon, vertices[j]->polygon)) {
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
        areaGraph->originSet.erase(std::remove(areaGraph->originSet.begin(), areaGraph->originSet.end(), roomVtx), areaGraph->originSet.end());
        delete roomVtx; // 释放内存
    }
    
    std::cout << "已删除 " << toRemove.size() << " 个重复多边形" << std::endl;
}

// 将一个roomVertex的通道转移给另一个roomVertex
void transferPassages(roomVertex* source, roomVertex* target) {
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

// 合并小面积相邻房间
void mergeSmallAdjacentRooms(AreaGraph* areaGraph, double minArea, double maxMergeDistance) {
    if (areaGraph->originSet.empty()) {
        return;
    }
    
    std::cout << "开始合并小面积相邻房间..." << std::endl;
    
    // 计算每个房间的面积和中心点
    std::map<roomVertex*, double> roomAreas;
    std::map<roomVertex*, topo_geometry::point> roomCenters;
    std::vector<roomVertex*> smallRooms;
    
    for (auto room : areaGraph->originSet) {
        double area = calculateRoomArea(room);
        roomAreas[room] = area;
        roomCenters[room] = calculateRoomCenter(room);
        
        if (area < minArea) {
            smallRooms.push_back(room);
        }
    }
    
    std::cout << "检测到 " << smallRooms.size() << " 个小面积房间" << std::endl;
    
    // 如果没有小房间，直接返回
    if (smallRooms.empty()) {
        return;
    }
    
    // 记录已合并的房间
    std::set<roomVertex*> mergedRooms;
    // 记录需要删除的通道
    std::set<passageEdge*> passagesToRemove;
    // 记录合并操作
    std::vector<std::pair<roomVertex*, roomVertex*>> mergeOperations;
    
    // 逐个处理小房间，优先合并面积最小的
    std::sort(smallRooms.begin(), smallRooms.end(), 
              [&roomAreas](roomVertex* a, roomVertex* b) {
                  return roomAreas[a] < roomAreas[b];
              });
    
    for (auto smallRoom : smallRooms) {
        // 如果已经被合并，跳过
        if (mergedRooms.find(smallRoom) != mergedRooms.end()) {
            continue;
        }
        
        // 寻找最佳合并对象
        roomVertex* bestNeighbor = nullptr;
        double bestScore = -1.0;
        passageEdge* bestPassage = nullptr;
        
        // 遍历所有通道，找出与小房间相连的房间
        for (auto passage : areaGraph->passageEList) {
            if (passage->connectedAreas.size() != 2) continue;
            
            roomVertex* neighbor = nullptr;
            
            // 检查通道是否连接了当前小房间
            if (passage->connectedAreas[0] == smallRoom) {
                neighbor = passage->connectedAreas[1];
            } else if (passage->connectedAreas[1] == smallRoom) {
                neighbor = passage->connectedAreas[0];
            } else {
                continue; // 通道不连接当前小房间
            }
            
            // 如果邻居已经被合并，跳过
            if (mergedRooms.find(neighbor) != mergedRooms.end()) {
                continue;
            }
            
            // 计算两个房间中心点之间的距离
            double distance = boost::geometry::distance(
                roomCenters[smallRoom], roomCenters[neighbor]);
            
            // 计算合并分数，考虑多个因素
            double score = 0;
            
            // 1. 距离因素：距离越近越好
            if (distance < maxMergeDistance) {
                score += (maxMergeDistance - distance) / maxMergeDistance * 10.0;
                
                // 2. 面积因素：如果邻居也是小面积，更值得合并
                if (roomAreas[neighbor] < minArea * 1.5) {
                    score += 5.0;
                }
                
                // 3. 形状兼容性：如果合并后形状仍然简单，更好
                // 这里简化处理，只考虑距离和面积
                
                // 更新最佳邻居
                if (score > bestScore) {
                    bestScore = score;
                    bestNeighbor = neighbor;
                    bestPassage = passage;
                }
            }
        }
        
        // 如果找到了合适的邻居，进行合并
        if (bestNeighbor != nullptr && bestScore > 0) {
            // 记录合并操作
            mergeOperations.push_back(std::make_pair(smallRoom, bestNeighbor));
            
            // 标记小房间为已合并
            mergedRooms.insert(smallRoom);
            
            // 记录需要删除的通道
            if (bestPassage != nullptr) {
                passagesToRemove.insert(bestPassage);
            }
        }
    }
    
    std::cout << "计划执行 " << mergeOperations.size() << " 次合并操作" << std::endl;
    
    // 执行合并操作
    for (const auto& op : mergeOperations) {
        roomVertex* smallRoom = op.first;
        roomVertex* targetRoom = op.second;
        
        // 合并多边形
        targetRoom->polygon = PolygonProcessor::mergePolygons(smallRoom->polygon, targetRoom->polygon);
        
        // 转移小房间的通道到目标房间
        transferPassages(smallRoom, targetRoom);
        
        // 从 originSet 中移除小房间
        areaGraph->originSet.erase(std::remove(areaGraph->originSet.begin(), areaGraph->originSet.end(), smallRoom), areaGraph->originSet.end());
        
        // 释放内存
        delete smallRoom;
    }
    
    // 删除不需要的通道
    for (auto passage : passagesToRemove) {
        areaGraph->passageEList.erase(std::remove(areaGraph->passageEList.begin(), areaGraph->passageEList.end(), passage), areaGraph->passageEList.end());
        delete passage;
    }
    
    std::cout << "小面积房间合并完成，合并了 " << mergeOperations.size() << " 个房间，删除了 " 
              << passagesToRemove.size() << " 个通道" << std::endl;
}

// 打印房间面积排序列表
void printRoomAreasSorted(AreaGraph* areaGraph) {
    if (areaGraph->originSet.empty()) {
        std::cout << "没有房间数据可输出" << std::endl;
        return;
    }
    
    // 使用默认分辨率（米/像素）
    double resolution = 0.044;
    
    // 像素平方到平方米的转换系数
    double pixelToSqMeter = resolution * resolution;
    
    std::vector<std::pair<double, roomVertex*>> areas;
    for (auto room : areaGraph->originSet) {
        // 计算像素面积并转换为平方米
        double pixelArea = calculateRoomArea(room);
        double sqMeterArea = pixelArea * pixelToSqMeter;
        areas.emplace_back(sqMeterArea, room);
    }
    std::sort(areas.begin(), areas.end(), [](const std::pair<double, roomVertex*>& a, const std::pair<double, roomVertex*>& b) {
        return a.first > b.first;
    });
    
    // 导出 CSV 供 Python 绘图（已转换为平方米）
    std::ofstream csv("room_areas.csv");
    for (auto &p : areas) {
        csv << "room_" << p.second->roomId << "," << p.first << "\n";
    }
    csv.close();
    std::cout << "已导出房间面积CSV: room_areas.csv (单位: 平方米)" << std::endl;
    
    std::cout << "房间面积排序 (从大到小, 单位: 平方米):" << std::endl;
    int maxBarWidth = 50;
    double maxArea = areas.front().first;
    for (auto &p : areas) {
        int barLen = maxArea > 0 ? static_cast<int>(p.first / maxArea * maxBarWidth) : 0;
        std::string bar(barLen, '#');
        std::cout << std::setw(12) << ("room_" + std::to_string(p.second->roomId))
                  << " |" << bar << " " << std::fixed << std::setprecision(2) << p.first << std::endl;
    }
}

// 计算房间面积
double calculateRoomArea(roomVertex* room) {
    if (room->polygon.empty()) {
        return 0.0;
    }
    
    std::list<topo_geometry::point> polygon = room->polygon;
    return GeometryUtils::calcPolyArea(polygon);
}

// 计算房间中心点
topo_geometry::point calculateRoomCenter(roomVertex* room) {
    if (room->polygon.empty()) {
        // 返回原点作为默认值
        return topo_geometry::point(0, 0);
    }
    
    double centerX = 0, centerY = 0;
    int count = 0;
    
    for (const auto& point : room->polygon) {
        centerX += topo_geometry::getX(point);
        centerY += topo_geometry::getY(point);
        count++;
    }
    
    if (count > 0) {
        centerX /= count;
        centerY /= count;
    }
    
    return topo_geometry::point(centerX, centerY);
}

} // namespace RoomProcessor
} // namespace RMG
