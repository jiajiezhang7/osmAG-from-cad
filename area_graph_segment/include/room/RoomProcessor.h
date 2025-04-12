#ifndef ROOM_PROCESSOR_H
#define ROOM_PROCESSOR_H

#include "roomGraph.h"
#include <vector>
#include <list>

namespace RMG {
namespace RoomProcessor {

// 去除originSet中形状相同的多边形
void removeDuplicatePolygons(AreaGraph* areaGraph);

// 将一个roomVertex的通道转移给另一个roomVertex
void transferPassages(roomVertex* source, roomVertex* target);

// 合并小面积相邻房间
void mergeSmallAdjacentRooms(AreaGraph* areaGraph, double minArea, double maxMergeDistance);

// 计算房间面积
double calculateRoomArea(roomVertex* room);

// 计算房间中心点
topo_geometry::point calculateRoomCenter(roomVertex* room);

} // namespace RoomProcessor
} // namespace RMG

#endif // ROOM_PROCESSOR_H
