#include "export/OsmAGExporter.h"
#include "geometry/GeometryUtils.h"
#include "polygon/PolygonProcessor.h"
#include "room/RoomProcessor.h"
#include "passage/PassageProcessor.h"
#include "utils/ParamsLoader.h"
#include <fstream>
#include <iostream>
#include <map>
#include <set>

namespace RMG {
namespace OsmAGExporter {

// 简化所有房间多边形
void simplifyPolygons(AreaGraph* areaGraph, double epsilon, const std::vector<topo_geometry::point>* preservePoints) {
    // 输出简化前的点数量统计
    int totalPointsBefore = 0;
    for (auto roomVtx : areaGraph->originSet) {
        totalPointsBefore += roomVtx->polygon.size();
    }

    // 对每个房间多边形进行简化
    for (auto roomVtx : areaGraph->originSet) {
        roomVtx->polygon = PolygonProcessor::simplifyPolygon(roomVtx->polygon, epsilon, preservePoints, areaGraph);
    }

    // 输出简化后的点数量统计
    int totalPointsAfter = 0;
    for (auto roomVtx : areaGraph->originSet) {
        totalPointsAfter += roomVtx->polygon.size();
    }

    std::cout << "多边形简化: 原有" << totalPointsBefore << "个点，简化后" << totalPointsAfter
              << "个点，减少" << (totalPointsBefore - totalPointsAfter) << "个点 ("
              << (100.0 * (totalPointsBefore - totalPointsAfter) / totalPointsBefore) << "%)" << std::endl;
}

// 移除房间多边形中的"毛刺"和尖角
void removeSpikesFromPolygons(AreaGraph* areaGraph, double angleThreshold, double distanceThreshold,
                            const std::vector<topo_geometry::point>* preservePoints) {
    // 输出处理前的点数量统计
    int totalPointsBefore = 0;
    for (auto roomVtx : areaGraph->originSet) {
        totalPointsBefore += roomVtx->polygon.size();
    }

    // 对每个房间多边形进行处理
    for (auto roomVtx : areaGraph->originSet) {
        roomVtx->polygon = PolygonProcessor::removeSpikesFromPolygon(roomVtx->polygon, angleThreshold, distanceThreshold, preservePoints);
    }

    // 输出处理后的点数量统计
    int totalPointsAfter = 0;
    for (auto roomVtx : areaGraph->originSet) {
        totalPointsAfter += roomVtx->polygon.size();
    }

    std::cout << "多边形毛刺移除: 原有" << totalPointsBefore << "个点，处理后" << totalPointsAfter
              << "个点，减少" << (totalPointsBefore - totalPointsAfter) << "个点 ("
              << (100.0 * (totalPointsBefore - totalPointsAfter) / totalPointsBefore) << "%)" << std::endl;
}

// 将AreaGraph导出为osmAG.xml格式
void exportToOsmAG(AreaGraph* areaGraph,
                 const std::string& filename,
                 bool simplify_enabled,
                 double simplify_tolerance,
                 bool spike_removal_enabled,
                 double spike_angle_threshold,
                 double spike_distance_threshold) {
    // 添加调试信息
    std::cout << "开始导出AreaGraph到" << filename << std::endl;

    // 输出优化前的房间信息
    std::cout << "优化前房间数量: " << areaGraph->originSet.size() << std::endl;

    // 去除重复多边形
    RoomProcessor::removeDuplicatePolygons(areaGraph);
    std::cout << "去重后房间数量: " << areaGraph->originSet.size() << std::endl;

    // 合并小面积相邻房间
    // 从 params.yaml 读取参数
    double minRoomArea = 4.0; // 默认值
    double maxMergeDistance = 1.5; // 默认值
    bool mergeEnabled = true; // 默认启用

    // 尝试从 ParamsLoader 获取参数
    try {
        auto& params = ParamsLoader::getInstance();
        if (params.params["polygon_processing"]["small_room_merge"]) {
            mergeEnabled = params.params["polygon_processing"]["small_room_merge"]["enabled"].as<bool>();
            if (mergeEnabled) {
                minRoomArea = params.params["polygon_processing"]["small_room_merge"]["min_area"].as<double>();
                maxMergeDistance = params.params["polygon_processing"]["small_room_merge"]["max_merge_distance"].as<double>();
                // 执行小房间合并
                RoomProcessor::mergeSmallAdjacentRooms(areaGraph, minRoomArea, maxMergeDistance);
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "警告: 读取小房间合并参数失败，使用默认值: " << e.what() << std::endl;
        if (mergeEnabled) {
            RoomProcessor::mergeSmallAdjacentRooms(areaGraph, minRoomArea, maxMergeDistance);
        }
    }

    std::cout << "优化后房间数量: " << areaGraph->originSet.size() << std::endl;

    // 用于收集通道端点信息，后续传给优化函数
    std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, std::pair<roomVertex*, roomVertex*>>> passagePointsForOptimization;

    // 创建XML文档
    std::ofstream osmFile(filename);
    osmFile << "<?xml version='1.0' encoding='UTF-8'?>\n";
    osmFile << "<osm version='0.6' generator='AreaGraph'>\n";

    // 创建一个负整数ID生成器(避免与OSM实际数据冲突)
    int nextId = -1;
    std::map<topo_geometry::point, int, topo_geometry::Smaller> pointToNodeId;

    // 1. 从params.yaml读取root_node坐标并创建根节点
    double root_lat = 31.17947960435;  // 默认值
    double root_lon = 121.59139728509; // 默认值
    // root_node 在 PNG 图像中的像素位置
    double root_pixel_x = 3804.0;  // 根据测量的 root_node 像素 x 坐标
    double root_pixel_y = 2801.0;  // 根据测量的 root_node 像素 y 坐标
    double png_width = 4000.0;     // PNG 图像宽度
    double png_height = 3360.0;    // PNG 图像高度
    double resolution = 0.044;     // PNG 图像的分辨率（米/像素）

    try {
        auto& params = ParamsLoader::getInstance();
        if (params.params["root_node"]) {
            root_lat = params.params["root_node"]["latitude"].as<double>();
            root_lon = params.params["root_node"]["longitude"].as<double>();

            // 如果配置文件中有 root_node 的像素位置，则使用配置文件中的值
            if (params.params["root_node"]["pixel_x"]) {
                root_pixel_x = params.params["root_node"]["pixel_x"].as<double>();
            }
            if (params.params["root_node"]["pixel_y"]) {
                root_pixel_y = params.params["root_node"]["pixel_y"].as<double>();
            }
            if (params.params["png_dimensions"]) {
                if (params.params["png_dimensions"]["width"]) {
                    png_width = params.params["png_dimensions"]["width"].as<double>();
                }
                if (params.params["png_dimensions"]["height"]) {
                    png_height = params.params["png_dimensions"]["height"].as<double>();
                }
                if (params.params["png_dimensions"]["resolution"]) {
                    resolution = params.params["png_dimensions"]["resolution"].as<double>();
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "警告: 读取root_node坐标失败，使用默认值: " << e.what() << std::endl;
    }

    // 设置 root_node 在 PNG 中的像素位置，使得所有坐标转换都相对于这个位置
    GeometryUtils::setRootNodePixelPosition(root_pixel_x, root_pixel_y);

    // 设置 PNG 图像的分辨率，用于将像素坐标转换为实际的米单位
    GeometryUtils::setResolution(resolution);

    // 创建根节点，使用配置的经纬度
    // 注意：我们现在使用 root_node 在 PNG 中的实际像素位置作为笛卡尔坐标
    topo_geometry::point root_point(root_pixel_x, root_pixel_y);
    int rootId = nextId--;

    // 设置输出精度为11位小数
    osmFile.precision(11);
    osmFile << std::fixed;

    osmFile << "  <node id='" << rootId << "' action='modify' visible='true' lat='"
            << root_lat << "' lon='" << root_lon << "'>\n";
    osmFile << "    <tag k='name' v='root' />\n";
    osmFile << "  </node>\n";

    // 2. 收集所有房间的点（仅使用优化后的多边形）
    std::map<roomVertex*, std::vector<int>> roomVertexToNodeIds;

    // 3. 创建房间way的ID映射
    int nextWayId = -1;
    std::map<roomVertex*, int> roomToWayId;

    for (auto roomVtx : areaGraph->originSet) {
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

    // 收集通道端点信息
    passagePointsForOptimization = PassageProcessor::collectPassagePoints(areaGraph);

    // 在这里调用优化函数，传入预计算的通道端点信息
    PassageProcessor::optimizeRoomPolygonsForPassages(areaGraph, &passagePointsForOptimization);

    // 输出优化后的房间信息
    std::cout << "优化后房间数量: " << areaGraph->originSet.size() << std::endl;

    // 收集需要保留的通道端点
    std::vector<topo_geometry::point> preservePoints;
    for (const auto& passage : passagePointsForOptimization) {
        preservePoints.push_back(passage.first.first);  // 第一个端点
        preservePoints.push_back(passage.first.second); // 第二个端点
    }

    // 根据参数决定是否进行多边形简化
    if (simplify_enabled) {
        // 在通道端点优化后进行多边形简化，保留通道端点
        simplifyPolygons(areaGraph, simplify_tolerance, &preservePoints);
        std::cout << "多边形简化完成，使用参数tolerance=" << simplify_tolerance
                  << "，已保留" << preservePoints.size() << "个通道端点" << std::endl;
    } else {
        std::cout << "跳过多边形简化处理" << std::endl;
    }

    // 根据参数决定是否进行毛刺去除
    if (spike_removal_enabled) {
        // 移除房间多边形中的"毛刺"和尖角
        removeSpikesFromPolygons(areaGraph, spike_angle_threshold, spike_distance_threshold, &preservePoints);
        std::cout << "多边形平滑完成，使用参数angle_threshold=" << spike_angle_threshold
                  << ", distance_threshold=" << spike_distance_threshold << std::endl;
    } else {
        std::cout << "跳过毛刺去除处理" << std::endl;
    }

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

            // 检查端点是否已存在，否则创建新节点
            int nodeIdA = -1;
            int nodeIdB = -1;

            // 查找点A是否存在
            bool pointAExists = false;
            for (const auto& pair : pointToNodeId) {
                if (GeometryUtils::equalLineVertex(pair.first, pointA)) {
                    pointAExists = true;
                    nodeIdA = pair.second;
                    break;
                }
            }

            if (!pointAExists) {
                nodeIdA = nextId--;
                pointToNodeId[pointA] = nodeIdA;

                auto latLon = GeometryUtils::cartesianToLatLon(topo_geometry::getX(pointA), topo_geometry::getY(pointA), root_lat, root_lon);
                osmFile << "  <node id='" << nodeIdA << "' action='modify' visible='true' lat='"
                        << latLon.first << "' lon='" << latLon.second << "' />\n";
            }

            // 查找点B是否存在
            bool pointBExists = false;
            if (!GeometryUtils::equalLineVertex(pointA, pointB)) { // 只有当点A和点B不同时才查找点B
                for (const auto& pair : pointToNodeId) {
                    if (GeometryUtils::equalLineVertex(pair.first, pointB)) {
                        pointBExists = true;
                        nodeIdB = pair.second;
                        break;
                    }
                }

                if (!pointBExists) {
                    nodeIdB = nextId--;
                    pointToNodeId[pointB] = nodeIdB;

                    auto latLon = GeometryUtils::cartesianToLatLon(topo_geometry::getX(pointB), topo_geometry::getY(pointB), root_lat, root_lon);
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
        }
    }

    // 遍历所有房间，生成节点ID（使用优化后的多边形）
    for (auto roomVtx : areaGraph->originSet) {
        std::vector<int> nodeIds;

        // 从优化后的房间多边形中提取所有点
        for (auto it = roomVtx->polygon.begin(); it != roomVtx->polygon.end(); ++it) {
            topo_geometry::point point = *it;

            // 检查这个点是否已经创建过
            bool pointExists = false;
            int nodeId = nextId;

            for (const auto& pair : pointToNodeId) {
                if (GeometryUtils::equalLineVertex(pair.first, point)) {
                    pointExists = true;
                    nodeId = pair.second;
                    break;
                }
            }

            if (!pointExists) {
                nodeId = nextId--;
                pointToNodeId[point] = nodeId;

                // 转换为经纬度
                auto latLon = GeometryUtils::cartesianToLatLon(topo_geometry::getX(point), topo_geometry::getY(point), root_lat, root_lon);

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

    // 在这里 originSet中已经有了"重复""的多边形
    for (auto roomVtx : areaGraph->originSet) {

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

} // namespace OsmAGExporter
} // namespace RMG
