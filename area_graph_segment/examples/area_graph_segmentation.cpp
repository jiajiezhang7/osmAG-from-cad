//
// Created by aass on 30/01/19.
//

// Last Modified by Jiajie on 24/7/02 

/*
Steps:
    1.Preprocess (noise, furniture removal)
    2.Voironoi generation
    3.Topology Graph generation
    4.Initial Area Graph generation
    5.Region 合并 -> final Area Graph
*/

#include <string>
#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <stdlib.h>
#include <sstream>
#include <sys/stat.h>
#include <sys/types.h>

#include <boost/geometry.hpp>
#include <boost/geometry/geometries/point_xy.hpp>
#include <boost/filesystem.hpp>
#include <boost/iterator/filter_iterator.hpp>
#include <boost/filesystem/path.hpp>

#include <QApplication>
#include <QMessageBox>
#include <QImage>

#include "VoriGraph.h"
#include "TopoGraph.h"
#include "cgal/CgalVoronoi.h"
#include "cgal/AlphaShape.h"
#include "cgal/AlphaShapeRemoval.h"
#include "qt/QImageVoronoi.h"
#include "RoomDect.h"
#include "roomGraph.h"
#include "Denoise.h"
#include "utils/ParamsLoader.h"
#include <yaml-cpp/yaml.h>
#include "room/RoomProcessor.h"

using namespace std;
namespace fs = boost::filesystem;

template<typename T>
std::string NumberToString(T Number) {
    std::ostringstream ss;
    ss << Number;
    return ss.str();
}

int nearint(double a) {
    return ceil(a) - a < 0.5 ? ceil(a) : floor(a);
}

VoriConfig *sConfig;

int main(int argc, char *argv[]) {
    // 参数解析和配置初始化
    if (argc < 2) {
        cout << "Usage " << argv[0]
             << " RGBimage.png [options]" << endl;
        cout << "Options:" << endl;
        cout << "  --resolution <value>        Map resolution (meters/pixel)" << endl;
        cout << "  --door-width <value>        Door width" << endl;
        cout << "  --corridor-width <value>    Corridor width" << endl;
        cout << "  --noise-percent <value>     Noise percentage (0-100)" << endl;

        cout << "  --root-lat <value>          Root node latitude" << endl;
        cout << "  --root-lon <value>          Root node longitude" << endl;
        cout << "  --root-pixel-x <value>      Root node pixel X position" << endl;
        cout << "  --root-pixel-y <value>      Root node pixel Y position" << endl;
        cout << "  --simplify-tolerance <value> Polygon simplification tolerance" << endl;
        cout << "  --spike-angle <value>       Spike removal angle threshold" << endl;
        cout << "  --spike-distance <value>    Spike removal distance threshold" << endl;
        cout << "  --min-room-area <value>     Minimum room area for filtering" << endl;
        cout << "  --clean-input <0|1>         Enable input cleaning" << endl;
        cout << "  --remove-furniture <0|1>    Enable furniture removal" << endl;
        cout << "  --record-time               Enable time recording" << endl;
        cout << "Legacy format: " << argv[0] << " RGBimage.png <resolution door_wide corridor_wide noise_precentage(0-100) record_time(0 or 1)>" << endl;
        return 255;
    }
    
    // 默认参数设置
    double door_wide = 1.15;
    double corridor_wide = 2;
    double res = 0.05;
    double noise_percent = 1.5;
    bool record_time = false;
    bool clean_input = false;
    bool remove_furniture = true;
    
    // 坐标参数
    double root_lat = -1;
    double root_lon = -1;
    double root_pixel_x = -1;
    double root_pixel_y = -1;
    
    // 多边形处理参数
    bool simplify_enabled = true;
    double simplify_tolerance = 0.05;
    bool spike_removal_enabled = true;
    double spike_angle_threshold = 60.0;
    double spike_distance_threshold = 0.30;
    double min_room_area = -1;
    
    // 尝试加载参数文件
    try {
        // 加载配置文件
        YAML::Node config = YAML::LoadFile("../config/params.yaml");
        
        // 将配置加载到ParamsLoader单例中
        ParamsLoader::getInstance().loadParams("../config/params.yaml");
        
        // 地图预处理参数
        if (config["map_preprocessing"]) {
            clean_input = config["map_preprocessing"]["clean_input"].as<bool>();
            res = config["map_preprocessing"]["resolution"].as<double>();
            door_wide = config["map_preprocessing"]["door_width"].as<double>();
            corridor_wide = config["map_preprocessing"]["corridor_width"].as<double>();
            noise_percent = config["map_preprocessing"]["noise_percent"].as<double>();
            remove_furniture = config["map_preprocessing"]["remove_furniture"].as<bool>();
        }
        

        
        // 根节点参数
        if (config["root_node"]) {
            if (config["root_node"]["latitude"]) {
                root_lat = config["root_node"]["latitude"].as<double>();
            }
            if (config["root_node"]["longitude"]) {
                root_lon = config["root_node"]["longitude"].as<double>();
            }
            if (config["root_node"]["pixel_x"]) {
                root_pixel_x = config["root_node"]["pixel_x"].as<double>();
            }
            if (config["root_node"]["pixel_y"]) {
                root_pixel_y = config["root_node"]["pixel_y"].as<double>();
            }
        }
        
        // 多边形处理参数
        if (config["polygon_processing"]["simplify"]) {
            simplify_enabled = config["polygon_processing"]["simplify"]["enabled"].as<bool>();
            simplify_tolerance = config["polygon_processing"]["simplify"]["tolerance"].as<double>();
        }
        
        if (config["polygon_processing"]["spike_removal"]) {
            spike_removal_enabled = config["polygon_processing"]["spike_removal"]["enabled"].as<bool>();
            spike_angle_threshold = config["polygon_processing"]["spike_removal"]["angle_threshold"].as<double>();
            spike_distance_threshold = config["polygon_processing"]["spike_removal"]["distance_threshold"].as<double>();
        }
        
        if (config["polygon_processing"]["small_room_filter"]) {
            if (config["polygon_processing"]["small_room_filter"]["min_area"]) {
                min_room_area = config["polygon_processing"]["small_room_filter"]["min_area"].as<double>();
            }
        }
        
        std::cout << "成功加载参数文件" << std::endl;
    } catch (const std::exception& e) {
        std::cout << "无法加载参数文件，使用默认参数: " << e.what() << std::endl;
    }
    
    // 获取输入图片的基础名称和输出目录
    fs::path input_path(argv[1]);
    string base_name = input_path.stem().string();
    string output_dir = base_name + "_output";
    
    // 创建输出目录
    fs::create_directory(output_dir);

    // 新的命令行参数解析 (支持 --parameter value 格式)
    for (int i = 2; i < argc; i++) {
        string arg = argv[i];
        
        if (arg == "--resolution" && i + 1 < argc) {
            res = atof(argv[++i]);
        } else if (arg == "--door-width" && i + 1 < argc) {
            door_wide = atof(argv[++i]);
        } else if (arg == "--corridor-width" && i + 1 < argc) {
            corridor_wide = atof(argv[++i]);
        } else if (arg == "--noise-percent" && i + 1 < argc) {
            noise_percent = atof(argv[++i]);

        } else if (arg == "--root-lat" && i + 1 < argc) {
            root_lat = atof(argv[++i]);
        } else if (arg == "--root-lon" && i + 1 < argc) {
            root_lon = atof(argv[++i]);
        } else if (arg == "--root-pixel-x" && i + 1 < argc) {
            root_pixel_x = atof(argv[++i]);
        } else if (arg == "--root-pixel-y" && i + 1 < argc) {
            root_pixel_y = atof(argv[++i]);
        } else if (arg == "--simplify-tolerance" && i + 1 < argc) {
            simplify_tolerance = atof(argv[++i]);
        } else if (arg == "--spike-angle" && i + 1 < argc) {
            spike_angle_threshold = atof(argv[++i]);
        } else if (arg == "--spike-distance" && i + 1 < argc) {
            spike_distance_threshold = atof(argv[++i]);
        } else if (arg == "--min-room-area" && i + 1 < argc) {
            min_room_area = atof(argv[++i]);
        } else if (arg == "--clean-input" && i + 1 < argc) {
            clean_input = atoi(argv[++i]) != 0;
        } else if (arg == "--remove-furniture" && i + 1 < argc) {
            remove_furniture = atoi(argv[++i]) != 0;
        } else if (arg == "--record-time") {
            record_time = true;
        } else if (i == 2 && arg.find("--") != 0) {
            // 兼容旧格式的位置参数
            res = atof(argv[2]);
            if (argc > 4) {
                door_wide = atof(argv[3]) == -1 ? 1.15 : atof(argv[3]);
                corridor_wide = atof(argv[4]) == -1 ? 1.35 : atof(argv[4]);

                if (argc > 5) {
                    noise_percent = atof(argv[5]);
                    if (argc > 6)
                        record_time = true;
                }
            }
            break; // 如果使用旧格式，跳出循环
        }
    }
    
    // 输出当前使用的参数
    cout << "=== 当前使用的参数 ===" << endl;
    cout << "分辨率: " << res << endl;
    cout << "门宽: " << door_wide << endl;
    cout << "廊宽: " << corridor_wide << endl;
    cout << "噪声百分比: " << noise_percent << endl;
    if (root_lat > -1) cout << "根节点纬度: " << root_lat << endl;
    if (root_lon > -1) cout << "根节点经度: " << root_lon << endl;
    cout << "===================" << endl;

    // 第0步：配置参数设定
    sConfig = new VoriConfig();
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = 1000;
    sConfig->doubleConfigVars["firstDeadEndRemovalDistance"] = 100000;
    sConfig->doubleConfigVars["secondDeadEndRemovalDistance"] = -100000;
    sConfig->doubleConfigVars["thirdDeadEndRemovalDistance"] = 0.25 / res;
    sConfig->doubleConfigVars["fourthDeadEndRemovalDistance"] = 8;
    sConfig->doubleConfigVars["topoGraphAngleCalcEndDistance"] = 10;
    sConfig->doubleConfigVars["topoGraphAngleCalcStartDistance"] = 3;
    sConfig->doubleConfigVars["topoGraphAngleCalcStepSize"] = 0.1;
    sConfig->doubleConfigVars["topoGraphDistanceToJoinVertices"] = 10;
    sConfig->doubleConfigVars["topoGraphMarkAsFeatureEdgeLength"] = 20;
    sConfig->doubleConfigVars["voronoiMinimumDistanceToObstacle"] = 0.25 / res;
    sConfig->doubleConfigVars["topoGraphDistanceToJoinVertices"] = 4;

    // ----------------------------------------------------------------------------
    // 第1步: 预处理输入图像 
        // 输入 - grid_map.png -> argv[1]
        // 输出 - clean.png

    int black_threshold = 210;
    bool is_denoise = false;
    
    // 根据clean_input标志决定是否进行去噪处理
    if (clean_input) {
        string clean_path = output_dir + "/clean.png";
        is_denoise = DenoiseImg(argv[1], clean_path.c_str(), black_threshold, 18, noise_percent);
        if (is_denoise)
            cout << "Denoise run successed!!" << endl;
    } else {
        // 如果不进行去噪，直接复制原图
        string clean_path = output_dir + "/clean.png";
        fs::copy_file(argv[1], clean_path, fs::copy_options::overwrite_existing);
        cout << "Skipped denoising as per configuration" << endl;
    }
    
    // ----------------------------------------------------------------------------
    // 第2步: 移除家具 - 使用Alpha Shape算法
        // 输入 - clean.png -> test (QImage对象)
        // 输出 - afterAlphaRemoval.png

    QImage test;
    string clean_path = output_dir + "/clean.png";
    test.load(clean_path.c_str());
    
    // 确保图像格式为支持的格式（ARGB32或RGB888）
    if (test.format() != QImage::Format_ARGB32 && test.format() != QImage::Format_RGB888) {
        cout << "Converting image to supported format..." << endl;
        test = test.convertToFormat(QImage::Format_ARGB32);
    }

    bool isTriple;
    analyseImage(test, isTriple);

    double AlphaShapeSquaredDist = 
            (sConfig->voronoiMinimumDistanceToObstacle()) * (sConfig->voronoiMinimumDistanceToObstacle());
    
    // 根据remove_furniture标志决定是否执行家具移除
    if (remove_furniture) {
        // 关键函数，执行家具移除
        performAlphaRemoval(test, AlphaShapeSquaredDist, MAX_PLEN_REMOVAL);
        cout << "Furniture removal performed" << endl;
    } else {
        cout << "Skipped furniture removal as per configuration" << endl;
    }
    
    // 家具移除后再次确保图像格式正确
    if (test.format() != QImage::Format_ARGB32 && test.format() != QImage::Format_RGB888) {
        cout << "Re-converting image to supported format after furniture removal..." << endl;
        test = test.convertToFormat(QImage::Format_ARGB32);
    }
    
    string alpha_removal_path = output_dir + "/afterAlphaRemoval.png";
    test.save(alpha_removal_path.c_str());

    // ----------------------------------------------------------------------------
    // 第3步： 提取障碍物点
        // 输入 - test  （处理后的图像）
        // 输出 - sites （障碍物点集合）

    // 在提取障碍物点前再次确保图像格式正确
    if (test.format() != QImage::Format_ARGB32 && test.format() != QImage::Format_RGB888) {
        cout << "Re-converting image to supported format before extracting sites..." << endl;
        test = test.convertToFormat(QImage::Format_ARGB32);
    }
    
    std::vector<topo_geometry::point> sites;
    bool ret = getSites(test, sites);

    // ----------------------------------------------------------------------------
    // 第4步: Voronoi图生成
        // 输入 - sites - 障碍物点集
        // 输出 - voriGraph - Voronoi图结构 
    int remove_alpha_value = 3600;

    // alpha参数策略
    double a;
    // 这里用到了读入的参数 - door_wide, corridor_wide
    // a = 两个当中的较小值 
    if (door_wide < corridor_wide) {
        a = door_wide + 0.1;
    } else {
         a= corridor_wide - 0.1;
    }

    int alpha_value = ceil(a * a * 0.25 / (res * res));
    // alpha_value越小，越不会过度分割
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = alpha_value;
    std::cout << "a = " << a << ", where alpha = " << alpha_value << std::endl;
    
    VoriGraph voriGraph;
    // 关键函数 -- 创建 VoriGraph
    ret = createVoriGraph(sites, voriGraph, sConfig);

    // 统计一些参数作为调试输出
    printGraphStatistics(voriGraph);
    
    // -----------------------------------------------------------------------------
    // 第5步： Alpha Shape处理
        // 输入 - voriGraph 和 test图像
        // 输出 - 修改后的 voriGraph
    
    QImage alpha = test;
    AlphaShapePolygon alphaSP, tem_alphaSP;
    AlphaShapePolygon::Polygon_2 *poly = alphaSP.performAlpha_biggestArea(alpha, remove_alpha_value, true);
    if (poly) {
        cout << "Removing vertices outside of polygon" << endl;
        removeOutsidePolygon(voriGraph, *poly);
    }
    
    AlphaShapePolygon::Polygon_2 *tem_poly = tem_alphaSP.performAlpha_biggestArea(alpha, sConfig->alphaShapeRemovalSquaredSize(), false);

    // 修剪voriGraph
    voriGraph.joinHalfEdges_jiawei();
    cout << "size of Polygons: " << tem_alphaSP.sizeOfPolygons() << endl;
    

    // -----------------------------------------------------------------------------
    // 第6步: 拓扑图生成 voriGraph -> TopoGraph
        // 输入 - voriGraph
        // 输出 - 优化后的voriGraph
    std::list<std::list<VoriGraphHalfEdge>::iterator> zeroHalfEdge;

        // 移除零长度的边
    for (std::list<VoriGraphHalfEdge>::iterator pathEdgeItr = voriGraph.halfEdges.begin();
         pathEdgeItr != voriGraph.halfEdges.end(); pathEdgeItr++) {
        if (pathEdgeItr->distance <= EPSINON) {
            zeroHalfEdge.push_back(pathEdgeItr);
        }
    }
    
    for (std::list<std::list<VoriGraphHalfEdge>::iterator>::iterator zeroHalfEdgeItr = zeroHalfEdge.begin();
         zeroHalfEdgeItr != zeroHalfEdge.end(); zeroHalfEdgeItr++) {
        voriGraph.removeHalfEdge_jiawei(*zeroHalfEdgeItr);
    }
    
        // 移除死端
    if (sConfig->firstDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->firstDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
    
    if (sConfig->secondDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->secondDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
    }
        // 保留最大连通分量
    gernerateGroupId(voriGraph);
    keepBiggestGroup(voriGraph);

    removeRays(voriGraph);
    voriGraph.joinHalfEdges_jiawei();

    if (sConfig->thirdDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->thirdDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
        // printGraphStatistics(voriGraph, "Third dead ends");
    }
    
    if (sConfig->fourthDeadEndRemovalDistance() > 0.) {
        voriGraph.markDeadEnds();
        removeDeadEnds_addFacetoPolygon(voriGraph, sConfig->fourthDeadEndRemovalDistance());
        voriGraph.joinHalfEdges_jiawei();
        // printGraphStatistics(voriGraph, "Fourth dead ends");
    }
    
    // ----------------------------------------------------------------------------------------------
    // 第7步: 初始区域图生成 - 房间检测
        // 输入 - voriGraph 和 tem_alphaSP
        // 输出 - 带有房间信息的 voriGraph

    RoomDect roomtest;
    roomtest.forRoomDect(tem_alphaSP, voriGraph, tem_poly);


    // ----------------------------------------------------------------------------------------------

    // 保存彩色区域图
    // QImage dectRoom = test;
    // paintVori_onlyArea(dectRoom, voriGraph);
    // 这和roomGraph是重复的
    // string tem_s = output_dir + "/" + base_name + "_area_" + NumberToString(nearint(a * 100)) + ".png";
    // dectRoom.save(tem_s.c_str());
    

    //-----------------------------------------------------------------------------------------------
    // 第8步: 区域合并 - 生成最终区域图 (也即经过优化后彩色区域图)

    RMG::AreaGraph RMGraph(voriGraph);
    RMGraph.mergeAreas();
    RMGraph.mergeRoomCell();
    RMGraph.prunning();
    RMGraph.arrangeRoomId();
    RMGraph.show();

    RMGraph.mergeRoomPolygons();

    // 保存最终区域图
    QImage RMGIm = test;
    RMGraph.draw(RMGIm);
    // 检查小房间合并是否启用
    bool merge_enabled = false;
    bool filter_enabled = false;
    try {
        auto& params = ParamsLoader::getInstance();
        if (params.params["polygon_processing"]["small_room_merge"]) {
            merge_enabled = params.params["polygon_processing"]["small_room_merge"]["enabled"].as<bool>();
        }
        if (params.params["polygon_processing"]["small_room_filter"]) {
            filter_enabled = params.params["polygon_processing"]["small_room_filter"]["enabled"].as<bool>();
        }
    } catch (const std::exception& e) {
        std::cout << "警告: 读取小房间合并参数失败，使用默认值" << std::endl;
    }
    
    string suffix = "";
    if (merge_enabled) suffix += "_merged";
    if (filter_enabled) suffix += "_filtered";
    string room_graph_path = output_dir + "/" + base_name + NumberToString(nearint(a * 100)) + suffix + "_roomGraph.png";
    RMGIm.save(room_graph_path.c_str());
    
    // 导出为osmAG.xml格式
    std::cout << "正在导出为osmAG.xml格式..." << std::endl;
    string osm_path = output_dir + "/" + base_name + NumberToString(nearint(a * 100)) + suffix + "_osmAG.osm";
    
    // 传递多边形处理参数
    RMGraph.exportToOsmAG(osm_path.c_str(), simplify_enabled, simplify_tolerance, 
        spike_removal_enabled, spike_angle_threshold, spike_distance_threshold);
    
    // 输出房间面积排序CSV和柱状图数据
    RMG::RoomProcessor::printRoomAreasSorted(&RMGraph);
    return 0;
}
