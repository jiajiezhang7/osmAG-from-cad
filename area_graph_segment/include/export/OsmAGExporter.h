#ifndef OSM_AG_EXPORTER_H
#define OSM_AG_EXPORTER_H

#include "roomGraph.h"
#include <string>
#include <vector>

namespace RMG {
namespace OsmAGExporter {

// 将AreaGraph导出为osmAG.xml格式
void exportToOsmAG(AreaGraph* areaGraph, 
                 const std::string& filename,
                 bool simplify_enabled = true, 
                 double simplify_tolerance = 0.05,
                 bool spike_removal_enabled = true, 
                 double spike_angle_threshold = 60.0, 
                 double spike_distance_threshold = 0.30);

// 简化所有房间多边形
void simplifyPolygons(AreaGraph* areaGraph, 
                    double epsilon, 
                    const std::vector<topo_geometry::point>* preservePoints);

// 移除房间多边形中的"毛刺"和尖角
void removeSpikesFromPolygons(AreaGraph* areaGraph, 
                            double angleThreshold, 
                            double distanceThreshold, 
                            const std::vector<topo_geometry::point>* preservePoints);

} // namespace OsmAGExporter
} // namespace RMG

#endif // OSM_AG_EXPORTER_H
