#include "roomGraph.h"
#include "geometry/GeometryUtils.h"
#include "polygon/PolygonProcessor.h"
#include "room/RoomProcessor.h"
#include "passage/PassageProcessor.h"
#include "export/OsmAGExporter.h"

// 将AreaGraph导出为osmAG.xml格式
void RMG::AreaGraph::exportToOsmAG(const std::string& filename,
                               bool simplify_enabled, double simplify_tolerance,
                               bool spike_removal_enabled, double spike_angle_threshold, 
                               double spike_distance_threshold)
{
    // 调用OsmAGExporter模块中的导出函数
    OsmAGExporter::exportToOsmAG(this, filename, 
                               simplify_enabled, simplify_tolerance,
                               spike_removal_enabled, spike_angle_threshold, 
                               spike_distance_threshold);
}

// 优化房间多边形，使通道与房间边界重合
void RMG::AreaGraph::optimizeRoomPolygonsForPassages(const std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, std::pair<roomVertex*, roomVertex*>>>* precomputedPassagePoints)
{
    // 调用PassageProcessor模块中的优化函数
    PassageProcessor::optimizeRoomPolygonsForPassages(this, precomputedPassagePoints);
}

// 去除originSet中形状相同的多边形
void RMG::AreaGraph::removeDuplicatePolygons() {
    // 调用RoomProcessor模块中的去重函数
    RoomProcessor::removeDuplicatePolygons(this);
}

// 计算多边形的哈希值
size_t RMG::AreaGraph::calculatePolygonHash(const std::list<topo_geometry::point>& polygon) {
    // 调用PolygonProcessor模块中的哈希计算函数
    return PolygonProcessor::calculatePolygonHash(polygon);
}

// 判断两个多边形是否相同
bool RMG::AreaGraph::arePolygonsEqual(const std::list<topo_geometry::point>& poly1, const std::list<topo_geometry::point>& poly2) {
    // 调用PolygonProcessor模块中的多边形比较函数
    return PolygonProcessor::arePolygonsEqual(poly1, poly2);
}

// 将一个roomVertex的通道转移给另一个roomVertex
void RMG::AreaGraph::transferPassages(roomVertex* source, roomVertex* target) {
    // 调用RoomProcessor模块中的通道转移函数
    RoomProcessor::transferPassages(source, target);
}

// 计算点到线段的距离
double RMG::AreaGraph::pointToLineDistance(const topo_geometry::point& p, const topo_geometry::point& lineStart, const topo_geometry::point& lineEnd) {
    // 调用GeometryUtils模块中的距离计算函数
    return GeometryUtils::pointToLineDistance(p, lineStart, lineEnd);
}

// 计算房间面积
double RMG::AreaGraph::calculateRoomArea(roomVertex* room) {
    // 调用RoomProcessor模块中的面积计算函数
    return RoomProcessor::calculateRoomArea(room);
}

// 计算房间中心点
topo_geometry::point RMG::AreaGraph::calculateRoomCenter(roomVertex* room) {
    // 调用RoomProcessor模块中的中心点计算函数
    return RoomProcessor::calculateRoomCenter(room);
}

// 合并两个房间的多边形
std::list<topo_geometry::point> RMG::AreaGraph::mergePolygons(const std::list<topo_geometry::point>& poly1, 
                                                           const std::list<topo_geometry::point>& poly2) {
    // 调用PolygonProcessor模块中的多边形合并函数
    return PolygonProcessor::mergePolygons(poly1, poly2);
}

// 合并小面积相邻房间
void RMG::AreaGraph::mergeSmallAdjacentRooms(double minArea, double maxMergeDistance) {
    // 调用RoomProcessor模块中的小房间合并函数
    RoomProcessor::mergeSmallAdjacentRooms(this, minArea, maxMergeDistance);
}

// 简化所有房间多边形
void RMG::AreaGraph::simplifyPolygons(double epsilon, const std::vector<topo_geometry::point>* preservePoints) {
    // 调用OsmAGExporter模块中的多边形简化函数
    OsmAGExporter::simplifyPolygons(this, epsilon, preservePoints);
}

// 移除房间多边形中的"毛刺"和尖角
void RMG::AreaGraph::removeSpikesFromPolygons(double angleThreshold, double distanceThreshold, 
                                          const std::vector<topo_geometry::point>* preservePoints) {
    // 调用OsmAGExporter模块中的毛刺去除函数
    OsmAGExporter::removeSpikesFromPolygons(this, angleThreshold, distanceThreshold, preservePoints);
}

// 简化单个多边形
std::list<topo_geometry::point> RMG::AreaGraph::simplifyPolygon(const std::list<topo_geometry::point>& polygon, 
                                                             double epsilon, 
                                                             const std::vector<topo_geometry::point>* preservePoints) {
    // 调用PolygonProcessor模块中的多边形简化函数
    return PolygonProcessor::simplifyPolygon(polygon, epsilon, preservePoints, this);
}

// 移除单个多边形中的"毛刺"
std::list<topo_geometry::point> RMG::AreaGraph::removeSpikesFromPolygon(
                            const std::list<topo_geometry::point>& polygon, 
                            double angleThreshold, double distanceThreshold,
                            const std::vector<topo_geometry::point>* preservePoints) {
    // 调用PolygonProcessor模块中的毛刺去除函数
    return PolygonProcessor::removeSpikesFromPolygon(polygon, angleThreshold, distanceThreshold, preservePoints);
}
