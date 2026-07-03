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
#include <vector>
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

namespace {

void printUsage(const char* executable) {
    cout << "Usage: " << executable << " RGBimage.png [options]" << endl;
    cout << "Options:" << endl;
    cout << "  --config <path>             YAML configuration file" << endl;
    cout << "  --output-dir <path>         Directory for all generated outputs" << endl;
    cout << "  --dump-effective-config     Write effective_config.yaml to output-dir" << endl;
    cout << "  --resolution <value>        Map resolution (meters/pixel)" << endl;
    cout << "  --door-width <value>        Door width" << endl;
    cout << "  --corridor-width <value>    Corridor width" << endl;
    cout << "  --noise-percent <value>     Noise percentage (0-100)" << endl;
    cout << "  --png-width <value>         PNG image width metadata" << endl;
    cout << "  --png-height <value>        PNG image height metadata" << endl;
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
    cout << "Legacy format: " << executable
         << " RGBimage.png <resolution door_wide corridor_wide noise_precentage(0-100) record_time(0 or 1)>"
         << endl;
}

bool hasValue(int index, int argc, const string& arg) {
    if (index + 1 < argc) {
        return true;
    }

    cerr << "Missing value for option " << arg << endl;
    return false;
}

bool parseBoolArg(const char* value) {
    return atoi(value) != 0;
}

fs::path resolveDefaultConfigPath(const char* executable) {
    fs::path current("config/params.yaml");
    if (fs::exists(current)) {
        return current;
    }

    fs::path executablePath(executable);
    fs::path executableDir = executablePath.parent_path();
    std::vector<fs::path> candidates;
    if (!executableDir.empty()) {
        candidates.push_back(executableDir / "../config/params.yaml");
        candidates.push_back(executableDir / "../../config/params.yaml");
    }
    candidates.push_back(fs::path("../config/params.yaml"));

    for (const auto& candidate : candidates) {
        if (fs::exists(candidate)) {
            return candidate;
        }
    }

    return current;
}

void dumpYamlFile(const YAML::Node& node, const string& outputPath) {
    YAML::Emitter emitter;
    emitter << node;
    std::ofstream output(outputPath);
    output << emitter.c_str() << std::endl;
}

} // namespace

int main(int argc, char *argv[]) {
    // 参数解析和配置初始化
    if (argc < 2) {
        printUsage(argv[0]);
        return 255;
    }

    if (string(argv[1]) == "--help" || string(argv[1]) == "-h") {
        printUsage(argv[0]);
        return 0;
    }

    if (string(argv[1]).find("--") == 0) {
        cerr << "Input PNG must be the first positional argument." << endl;
        printUsage(argv[0]);
        return 255;
    }
    
    // 默认参数设置
    double door_wide = 1.15;
    double corridor_wide = 2;
    double res = 0.044;
    double noise_percent = 1.5;
    bool record_time = false;
    bool clean_input = false;
    bool remove_furniture = true;
    
    // 坐标参数
    double root_lat = 31.17947960435;
    double root_lon = 121.59139728509;
    double root_pixel_x = 3804.0;
    double root_pixel_y = 2801.0;
    int png_width = -1;
    int png_height = -1;
    
    // 多边形处理参数
    bool simplify_enabled = true;
    double simplify_tolerance = 0.05;
    bool spike_removal_enabled = true;
    double spike_angle_threshold = 60.0;
    double spike_distance_threshold = 0.30;
    bool small_room_filter_enabled = false;
    double small_room_filter_min_area = 10.0;
    bool small_room_merge_enabled = false;
    double small_room_merge_min_area = 10.0;
    double small_room_merge_max_distance = 3.0;

    // AreaGraph/VoriConfig参数
    double alpha_width_offset = 0.1;
    int outside_removal_alpha = 3600;
    int fixed_alpha_value = -1;
    double furniture_max_polygon_length = MAX_PLEN_REMOVAL;
    double first_dead_end_removal_distance = 100000;
    double second_dead_end_removal_distance = -100000;
    double third_dead_end_removal_distance_meters = 0.25;
    double fourth_dead_end_removal_distance = 8;
    double topo_graph_angle_calc_end_distance = 10;
    double topo_graph_angle_calc_start_distance = 3;
    double topo_graph_angle_calc_step_size = 0.1;
    double topo_graph_distance_to_join_vertices = 4;
    double topo_graph_mark_as_feature_edge_length = 20;
    double voronoi_minimum_distance_to_obstacle_meters = 0.25;
    string level = "1";
    double height_per_level = 3.2;
    bool dump_effective_config = false;

    fs::path input_path(argv[1]);
    string base_name = input_path.stem().string();
    string output_dir = base_name + "_output";

    fs::path config_path = resolveDefaultConfigPath(argv[0]);
    for (int i = 2; i < argc; i++) {
        string arg = argv[i];
        if (arg == "--config" && hasValue(i, argc, arg)) {
            config_path = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 255;
        } else if (arg == "--dump-effective-config" || arg == "--record-time") {
            continue;
        } else if (arg.find("--") == 0 && hasValue(i, argc, arg)) {
            i++;
        } else if (i == 2 && arg.find("--") != 0) {
            break;
        }
    }

    YAML::Node config;
    
    // 尝试加载参数文件
    if (fs::exists(config_path)) {
        try {
            config = YAML::LoadFile(config_path.string());

        // 地图预处理参数
        if (config["map_preprocessing"]) {
            if (config["map_preprocessing"]["clean_input"]) clean_input = config["map_preprocessing"]["clean_input"].as<bool>();
            if (config["map_preprocessing"]["resolution"]) res = config["map_preprocessing"]["resolution"].as<double>();
            if (config["map_preprocessing"]["door_width"]) door_wide = config["map_preprocessing"]["door_width"].as<double>();
            if (config["map_preprocessing"]["corridor_width"]) corridor_wide = config["map_preprocessing"]["corridor_width"].as<double>();
            if (config["map_preprocessing"]["noise_percent"]) noise_percent = config["map_preprocessing"]["noise_percent"].as<double>();
            if (config["map_preprocessing"]["remove_furniture"]) remove_furniture = config["map_preprocessing"]["remove_furniture"].as<bool>();
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

        if (config["png_dimensions"]) {
            if (config["png_dimensions"]["width"]) png_width = config["png_dimensions"]["width"].as<int>();
            if (config["png_dimensions"]["height"]) png_height = config["png_dimensions"]["height"].as<int>();
        }
        
        // 多边形处理参数
        if (config["polygon_processing"] && config["polygon_processing"]["simplify"]) {
            simplify_enabled = config["polygon_processing"]["simplify"]["enabled"].as<bool>();
            simplify_tolerance = config["polygon_processing"]["simplify"]["tolerance"].as<double>();
        }
        
        if (config["polygon_processing"] && config["polygon_processing"]["spike_removal"]) {
            spike_removal_enabled = config["polygon_processing"]["spike_removal"]["enabled"].as<bool>();
            spike_angle_threshold = config["polygon_processing"]["spike_removal"]["angle_threshold"].as<double>();
            spike_distance_threshold = config["polygon_processing"]["spike_removal"]["distance_threshold"].as<double>();
        }
        
        if (config["polygon_processing"] && config["polygon_processing"]["small_room_filter"]) {
            if (config["polygon_processing"]["small_room_filter"]["enabled"]) {
                small_room_filter_enabled = config["polygon_processing"]["small_room_filter"]["enabled"].as<bool>();
            }
            if (config["polygon_processing"]["small_room_filter"]["min_area"]) {
                small_room_filter_min_area = config["polygon_processing"]["small_room_filter"]["min_area"].as<double>();
            }
        }

        if (config["polygon_processing"] && config["polygon_processing"]["small_room_merge"]) {
            if (config["polygon_processing"]["small_room_merge"]["enabled"]) {
                small_room_merge_enabled = config["polygon_processing"]["small_room_merge"]["enabled"].as<bool>();
            }
            if (config["polygon_processing"]["small_room_merge"]["min_area"]) {
                small_room_merge_min_area = config["polygon_processing"]["small_room_merge"]["min_area"].as<double>();
            }
            if (config["polygon_processing"]["small_room_merge"]["max_merge_distance"]) {
                small_room_merge_max_distance = config["polygon_processing"]["small_room_merge"]["max_merge_distance"].as<double>();
            }
        }

        if (config["area_graph"]) {
            if (config["area_graph"]["alpha"]) {
                auto alphaConfig = config["area_graph"]["alpha"];
                if (alphaConfig["width_offset"]) alpha_width_offset = alphaConfig["width_offset"].as<double>();
                if (alphaConfig["outside_removal_alpha"]) outside_removal_alpha = alphaConfig["outside_removal_alpha"].as<int>();
                if (alphaConfig["fixed_value"] && !alphaConfig["fixed_value"].IsNull()) fixed_alpha_value = alphaConfig["fixed_value"].as<int>();
            }
            if (config["area_graph"]["furniture_removal"]) {
                auto furnitureConfig = config["area_graph"]["furniture_removal"];
                if (furnitureConfig["max_polygon_length"]) furniture_max_polygon_length = furnitureConfig["max_polygon_length"].as<double>();
            }
            if (config["area_graph"]["vori_config"]) {
                auto voriConfig = config["area_graph"]["vori_config"];
                if (voriConfig["first_dead_end_removal_distance"]) first_dead_end_removal_distance = voriConfig["first_dead_end_removal_distance"].as<double>();
                if (voriConfig["second_dead_end_removal_distance"]) second_dead_end_removal_distance = voriConfig["second_dead_end_removal_distance"].as<double>();
                if (voriConfig["third_dead_end_removal_distance_meters"]) third_dead_end_removal_distance_meters = voriConfig["third_dead_end_removal_distance_meters"].as<double>();
                if (voriConfig["fourth_dead_end_removal_distance"]) fourth_dead_end_removal_distance = voriConfig["fourth_dead_end_removal_distance"].as<double>();
                if (voriConfig["topo_graph_angle_calc_end_distance"]) topo_graph_angle_calc_end_distance = voriConfig["topo_graph_angle_calc_end_distance"].as<double>();
                if (voriConfig["topo_graph_angle_calc_start_distance"]) topo_graph_angle_calc_start_distance = voriConfig["topo_graph_angle_calc_start_distance"].as<double>();
                if (voriConfig["topo_graph_angle_calc_step_size"]) topo_graph_angle_calc_step_size = voriConfig["topo_graph_angle_calc_step_size"].as<double>();
                if (voriConfig["topo_graph_distance_to_join_vertices"]) topo_graph_distance_to_join_vertices = voriConfig["topo_graph_distance_to_join_vertices"].as<double>();
                if (voriConfig["topo_graph_mark_as_feature_edge_length"]) topo_graph_mark_as_feature_edge_length = voriConfig["topo_graph_mark_as_feature_edge_length"].as<double>();
                if (voriConfig["voronoi_minimum_distance_to_obstacle_meters"]) voronoi_minimum_distance_to_obstacle_meters = voriConfig["voronoi_minimum_distance_to_obstacle_meters"].as<double>();
            }
        }

        if (config["level"]) level = config["level"].as<std::string>();
        if (config["height_per_level"]) height_per_level = config["height_per_level"].as<double>();
        
            std::cout << "成功加载参数文件: " << config_path.string() << std::endl;
        } catch (const std::exception& e) {
            std::cout << "无法加载参数文件，使用默认参数: " << e.what() << std::endl;
        }
    } else {
        std::cout << "未找到参数文件，使用内置默认参数: " << config_path.string() << std::endl;
    }

    // 新的命令行参数解析 (支持 --parameter value 格式)
    for (int i = 2; i < argc; i++) {
        string arg = argv[i];
        
        if (arg == "--config" && hasValue(i, argc, arg)) {
            config_path = argv[++i];
        } else if (arg == "--output-dir" && hasValue(i, argc, arg)) {
            output_dir = argv[++i];
        } else if (arg == "--dump-effective-config") {
            dump_effective_config = true;
        } else if (arg == "--resolution" && hasValue(i, argc, arg)) {
            res = atof(argv[++i]);
        } else if (arg == "--door-width" && hasValue(i, argc, arg)) {
            door_wide = atof(argv[++i]);
        } else if (arg == "--corridor-width" && hasValue(i, argc, arg)) {
            corridor_wide = atof(argv[++i]);
        } else if (arg == "--noise-percent" && hasValue(i, argc, arg)) {
            noise_percent = atof(argv[++i]);
        } else if (arg == "--png-width" && hasValue(i, argc, arg)) {
            png_width = atoi(argv[++i]);
        } else if (arg == "--png-height" && hasValue(i, argc, arg)) {
            png_height = atoi(argv[++i]);
        } else if (arg == "--root-lat" && hasValue(i, argc, arg)) {
            root_lat = atof(argv[++i]);
        } else if (arg == "--root-lon" && hasValue(i, argc, arg)) {
            root_lon = atof(argv[++i]);
        } else if (arg == "--root-pixel-x" && hasValue(i, argc, arg)) {
            root_pixel_x = atof(argv[++i]);
        } else if (arg == "--root-pixel-y" && hasValue(i, argc, arg)) {
            root_pixel_y = atof(argv[++i]);
        } else if (arg == "--simplify-tolerance" && hasValue(i, argc, arg)) {
            simplify_tolerance = atof(argv[++i]);
        } else if (arg == "--spike-angle" && hasValue(i, argc, arg)) {
            spike_angle_threshold = atof(argv[++i]);
        } else if (arg == "--spike-distance" && hasValue(i, argc, arg)) {
            spike_distance_threshold = atof(argv[++i]);
        } else if (arg == "--min-room-area" && hasValue(i, argc, arg)) {
            small_room_filter_min_area = atof(argv[++i]);
        } else if (arg == "--clean-input" && hasValue(i, argc, arg)) {
            clean_input = parseBoolArg(argv[++i]);
        } else if (arg == "--remove-furniture" && hasValue(i, argc, arg)) {
            remove_furniture = parseBoolArg(argv[++i]);
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
        } else if (arg.find("--") == 0) {
            cerr << "Unknown option: " << arg << endl;
            printUsage(argv[0]);
            return 255;
        }
    }

    config["map_preprocessing"]["clean_input"] = clean_input;
    config["map_preprocessing"]["resolution"] = res;
    config["map_preprocessing"]["door_width"] = door_wide;
    config["map_preprocessing"]["corridor_width"] = corridor_wide;
    config["map_preprocessing"]["noise_percent"] = noise_percent;
    config["map_preprocessing"]["remove_furniture"] = remove_furniture;
    config["root_node"]["latitude"] = root_lat;
    config["root_node"]["longitude"] = root_lon;
    config["root_node"]["pixel_x"] = root_pixel_x;
    config["root_node"]["pixel_y"] = root_pixel_y;
    if (png_width > 0) config["png_dimensions"]["width"] = png_width;
    if (png_height > 0) config["png_dimensions"]["height"] = png_height;
    config["png_dimensions"]["resolution"] = res;
    config["polygon_processing"]["simplify"]["enabled"] = simplify_enabled;
    config["polygon_processing"]["simplify"]["tolerance"] = simplify_tolerance;
    config["polygon_processing"]["spike_removal"]["enabled"] = spike_removal_enabled;
    config["polygon_processing"]["spike_removal"]["angle_threshold"] = spike_angle_threshold;
    config["polygon_processing"]["spike_removal"]["distance_threshold"] = spike_distance_threshold;
    config["polygon_processing"]["small_room_filter"]["enabled"] = small_room_filter_enabled;
    config["polygon_processing"]["small_room_filter"]["min_area"] = small_room_filter_min_area;
    config["polygon_processing"]["small_room_merge"]["enabled"] = small_room_merge_enabled;
    config["polygon_processing"]["small_room_merge"]["min_area"] = small_room_merge_min_area;
    config["polygon_processing"]["small_room_merge"]["max_merge_distance"] = small_room_merge_max_distance;
    config["area_graph"]["alpha"]["mode"] = fixed_alpha_value > 0 ? "fixed" : "dynamic";
    if (fixed_alpha_value > 0) {
        config["area_graph"]["alpha"]["fixed_value"] = fixed_alpha_value;
    } else {
        config["area_graph"]["alpha"]["fixed_value"] = YAML::Node();
    }
    config["area_graph"]["alpha"]["width_offset"] = alpha_width_offset;
    config["area_graph"]["alpha"]["outside_removal_alpha"] = outside_removal_alpha;
    config["area_graph"]["furniture_removal"]["max_polygon_length"] = furniture_max_polygon_length;
    config["area_graph"]["vori_config"]["first_dead_end_removal_distance"] = first_dead_end_removal_distance;
    config["area_graph"]["vori_config"]["second_dead_end_removal_distance"] = second_dead_end_removal_distance;
    config["area_graph"]["vori_config"]["third_dead_end_removal_distance_meters"] = third_dead_end_removal_distance_meters;
    config["area_graph"]["vori_config"]["fourth_dead_end_removal_distance"] = fourth_dead_end_removal_distance;
    config["area_graph"]["vori_config"]["topo_graph_angle_calc_end_distance"] = topo_graph_angle_calc_end_distance;
    config["area_graph"]["vori_config"]["topo_graph_angle_calc_start_distance"] = topo_graph_angle_calc_start_distance;
    config["area_graph"]["vori_config"]["topo_graph_angle_calc_step_size"] = topo_graph_angle_calc_step_size;
    config["area_graph"]["vori_config"]["topo_graph_distance_to_join_vertices"] = topo_graph_distance_to_join_vertices;
    config["area_graph"]["vori_config"]["topo_graph_mark_as_feature_edge_length"] = topo_graph_mark_as_feature_edge_length;
    config["area_graph"]["vori_config"]["voronoi_minimum_distance_to_obstacle_meters"] = voronoi_minimum_distance_to_obstacle_meters;
    config["level"] = level;
    config["height_per_level"] = height_per_level;
    config["runtime"]["config_path"] = config_path.string();
    config["runtime"]["input_png"] = argv[1];
    config["runtime"]["output_dir"] = output_dir;
    config["runtime"]["record_time"] = record_time;

    ParamsLoader::getInstance().params = config;

    // 创建输出目录
    fs::create_directories(output_dir);

    if (dump_effective_config) {
        string effective_config_path = (fs::path(output_dir) / "effective_config.yaml").string();
        dumpYamlFile(config, effective_config_path);
        cout << "Effective config written to: " << effective_config_path << endl;
    }
    
    // 输出当前使用的参数
    cout << "=== 当前使用的参数 ===" << endl;
    cout << "分辨率: " << res << endl;
    cout << "门宽: " << door_wide << endl;
    cout << "廊宽: " << corridor_wide << endl;
    cout << "噪声百分比: " << noise_percent << endl;
    cout << "根节点纬度: " << root_lat << endl;
    cout << "根节点经度: " << root_lon << endl;
    cout << "输出目录: " << output_dir << endl;
    cout << "===================" << endl;

    // 第0步：配置参数设定
    sConfig = new VoriConfig();
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = fixed_alpha_value > 0 ? fixed_alpha_value : 1000;
    sConfig->doubleConfigVars["firstDeadEndRemovalDistance"] = first_dead_end_removal_distance;
    sConfig->doubleConfigVars["secondDeadEndRemovalDistance"] = second_dead_end_removal_distance;
    sConfig->doubleConfigVars["thirdDeadEndRemovalDistance"] = third_dead_end_removal_distance_meters / res;
    sConfig->doubleConfigVars["fourthDeadEndRemovalDistance"] = fourth_dead_end_removal_distance;
    sConfig->doubleConfigVars["topoGraphAngleCalcEndDistance"] = topo_graph_angle_calc_end_distance;
    sConfig->doubleConfigVars["topoGraphAngleCalcStartDistance"] = topo_graph_angle_calc_start_distance;
    sConfig->doubleConfigVars["topoGraphAngleCalcStepSize"] = topo_graph_angle_calc_step_size;
    sConfig->doubleConfigVars["topoGraphDistanceToJoinVertices"] = topo_graph_distance_to_join_vertices;
    sConfig->doubleConfigVars["topoGraphMarkAsFeatureEdgeLength"] = topo_graph_mark_as_feature_edge_length;
    sConfig->doubleConfigVars["voronoiMinimumDistanceToObstacle"] = voronoi_minimum_distance_to_obstacle_meters / res;

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
        performAlphaRemoval(test, AlphaShapeSquaredDist, furniture_max_polygon_length);
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
    int remove_alpha_value = outside_removal_alpha;

    // alpha参数策略
    double a;
    // 这里用到了读入的参数 - door_wide, corridor_wide
    // a = 两个当中的较小值 
    if (door_wide < corridor_wide) {
        a = door_wide + alpha_width_offset;
    } else {
         a= corridor_wide - alpha_width_offset;
    }

    int alpha_value = fixed_alpha_value > 0 ? fixed_alpha_value : ceil(a * a * 0.25 / (res * res));
    // alpha_value越小，越不会过度分割
    sConfig->doubleConfigVars["alphaShapeRemovalSquaredSize"] = alpha_value;
    ParamsLoader::getInstance().params["area_graph"]["alpha"]["calculated_value"] = alpha_value;
    if (dump_effective_config) {
        string effective_config_path = (fs::path(output_dir) / "effective_config.yaml").string();
        dumpYamlFile(ParamsLoader::getInstance().params, effective_config_path);
    }
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
