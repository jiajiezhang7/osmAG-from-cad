cmake_minimum_required(VERSION 3.10)

project(TOPO_GRAPH_2D)

# 设置CMP0011策略
cmake_policy(SET CMP0011 NEW)

# 设置CMAKE_BUILD_TYPE
set(CMAKE_BUILD_TYPE Release)

# 添加-fPIC标志
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")

# 查找Boost库
find_package(Boost REQUIRED)
if(NOT Boost_FOUND)
  message(STATUS "This project requires the Boost library, and will not be compiled.")
  return()
endif()

# 查找CGAL库及其组件
find_package(CGAL COMPONENTS Core)
if(NOT CGAL_FOUND)
  message(STATUS "This program requires the CGAL library, and will not be compiled.")
  return()
endif()

# 查找Qt5库及其组件
find_package(Qt5 REQUIRED COMPONENTS Core Widgets Gui)

if(NOT Qt5_FOUND)
  message(STATUS "This program requires the Qt5 library, and will not be compiled.")
  return()
endif()

# 包含CGAL和Qt5的配置文件
include(${CGAL_USE_FILE})

# 包含Qt5模块
set(QT_USE_QTMAIN TRUE)
include_directories(${Qt5Widgets_INCLUDE_DIRS})
include_directories(${Qt5Core_INCLUDE_DIRS})
include_directories(${Qt5Gui_INCLUDE_DIRS})
add_definitions(${Qt5Widgets_DEFINITIONS})
add_definitions(${Qt5Core_DEFINITIONS})
add_definitions(${Qt5Gui_DEFINITIONS})

# 设置RPATH
set(CMAKE_SKIP_BUILD_RPATH FALSE)
set(CMAKE_BUILD_WITH_INSTALL_RPATH FALSE)
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(CMAKE_INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib")

# 添加库文件
add_library(topo_graph_2d STATIC
  src/VoriConfig.cpp
  src/VoriGraph.cpp
  src/TopoGraph.cpp
  src/RoomDect.cpp
  src/roomGraph.cpp
  src/Denoise.cpp
  src/passageSearch.cpp
  src/cgal/CgalVoronoi.cpp
  src/cgal/AlphaShape.cpp
  src/qt/QImageVoronoi.cpp
  src/cgal/AlphaShapeRemoval.cpp)

# 包含头文件目录
include_directories(${TOPO_GRAPH_2D_SOURCE_DIR}/include)
include_directories(${CGAL_INCLUDE_DIRS})

# 设置输出目录
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# 添加可执行文件
add_executable(area_graph_segmentation examples/area_graph_segmentation.cpp)

# 添加测试可执行文件
add_executable(test_area_graph test/test_area_graph.cpp)

# 输出状态消息
message(STATUS "CGAL libraries: ${CGAL_LIBRARIES}")

# 链接库文件
target_link_libraries(area_graph_segmentation topo_graph_2d Qt5::Widgets Qt5::Core Qt5::Gui ${CGAL_LIBRARIES} ${Boost_LIBRARIES})
target_link_libraries(test_area_graph topo_graph_2d Qt5::Widgets Qt5::Core Qt5::Gui ${CGAL_LIBRARIES} ${Boost_LIBRARIES})
