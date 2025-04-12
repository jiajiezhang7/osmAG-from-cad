#ifndef PASSAGE_PROCESSOR_H
#define PASSAGE_PROCESSOR_H

#include "roomGraph.h"
#include <vector>
#include <utility>

namespace RMG {
namespace PassageProcessor {

// 优化房间多边形，使通道与房间边界重合
void optimizeRoomPolygonsForPassages(AreaGraph* areaGraph, 
                                   const std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, 
                                   std::pair<roomVertex*, roomVertex*>>>* precomputedPassagePoints = nullptr);

// 收集通道端点信息
std::vector<std::pair<std::pair<topo_geometry::point, topo_geometry::point>, 
                     std::pair<roomVertex*, roomVertex*>>> 
collectPassagePoints(AreaGraph* areaGraph);

} // namespace PassageProcessor
} // namespace RMG

#endif // PASSAGE_PROCESSOR_H
