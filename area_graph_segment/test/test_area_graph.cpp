//
// 测试文件：测试区域图分割算法的各个组件
//

#include <iostream>
#include <string>
#include <cassert>
#include <cmath>

#include "VoriGraph.h"
#include "TopoGraph.h"
#include "RoomDect.h"
#include "roomGraph.h"
#include "Denoise.h"
#include "geometry/GeometryUtils.h"

namespace {

bool nearlyEqual(double lhs, double rhs, double epsilon = 1e-9) {
    return std::abs(lhs - rhs) < epsilon;
}

} // namespace

// 测试VoriGraph基本功能
bool test_vori_graph() {
    std::cout << "测试VoriGraph基本功能..." << std::endl;
    
    // 创建一个简单的VoriGraph
    VoriGraph voriGraph;
    
    // TODO: 添加测试代码
    
    return true;
}

// 测试房间检测功能
bool test_room_detection() {
    std::cout << "测试房间检测功能..." << std::endl;
    
    // TODO: 添加测试代码
    
    return true;
}

// 测试区域合并功能
bool test_area_merging() {
    std::cout << "测试区域合并功能..." << std::endl;
    
    // TODO: 添加测试代码
    
    return true;
}

// 测试root_node像素位置和分辨率配置是否会实际影响WGS84转换
bool test_geometry_root_node_config() {
    std::cout << "测试root_node配置转换..." << std::endl;

    const double root_lat = 31.230416;
    const double root_lon = 121.473701;

    RMG::GeometryUtils::setRootNodePixelPosition(10.0, 20.0);
    RMG::GeometryUtils::setResolution(1.0);

    const auto root_position = RMG::GeometryUtils::cartesianToLatLon(10.0, 20.0, root_lat, root_lon);
    assert(nearlyEqual(root_position.first, root_lat));
    assert(nearlyEqual(root_position.second, root_lon));

    const auto one_meter_east = RMG::GeometryUtils::cartesianToLatLon(11.0, 20.0, root_lat, root_lon);
    const double one_meter_lon_delta = std::abs(one_meter_east.second - root_lon);

    RMG::GeometryUtils::setResolution(2.0);
    const auto two_meters_east = RMG::GeometryUtils::cartesianToLatLon(11.0, 20.0, root_lat, root_lon);
    const double two_meter_lon_delta = std::abs(two_meters_east.second - root_lon);

    assert(two_meter_lon_delta > one_meter_lon_delta * 1.5);

    RMG::GeometryUtils::setRootNodePixelPosition(3804.0, 2801.0);
    RMG::GeometryUtils::setResolution(0.044);

    return true;
}

int main() {
    std::cout << "开始测试区域图分割算法的各个组件..." << std::endl;
    
    bool all_tests_passed = true;
    
    // 运行各个测试
    all_tests_passed &= test_vori_graph();
    all_tests_passed &= test_room_detection();
    all_tests_passed &= test_area_merging();
    all_tests_passed &= test_geometry_root_node_config();
    
    if (all_tests_passed) {
        std::cout << "所有测试通过！" << std::endl;
        return 0;
    } else {
        std::cout << "测试失败！" << std::endl;
        return 1;
    }
}
