#include "geometry/GeometryUtils.h"
#include "WGS84toCartesian.h"
#include <cmath>
#include <iostream>

namespace RMG {
namespace GeometryUtils {

// 判断两个点是否相等（考虑浮点误差）
bool equalLineVertex(const topo_geometry::point &a, const topo_geometry::point &b) {
    const double EPSILON = 1e-6;
    return boost::geometry::distance(a, b) < EPSILON;
}

// 计算多边形面积
double calcPolyArea(std::list<topo_geometry::point> &polygon) {
    double area = 0;
    std::list<topo_geometry::point>::iterator itj = polygon.end();
    itj--;
    for (std::list<topo_geometry::point>::iterator it = polygon.begin(); it != polygon.end(); it++) {
        area += ((topo_geometry::getX(*itj) * topo_geometry::getY(*it)) -
                 (topo_geometry::getY(*itj) * topo_geometry::getX(*it)));
        itj = it;
    }
    return std::abs(area / 2.0);
}

// 将笛卡尔坐标转换为经纬度
std::pair<double, double> cartesianToLatLon(double x, double y, double root_lat, double root_lon) {
    // 使用WGS84坐标系统进行转换
    // 创建参考点（root_node的经纬度）
    std::array<double, 2> reference{root_lat, root_lon};

    // root_node 在 PNG 中的像素位置
    // 使用静态局部变量来存储像素位置，这样可以通过 setRootNodePixelPosition 函数来更新
    static double& root_pixel_x = []() -> double& {
        static double x = 3804.0; // 默认值，根据测量的 root_node 像素 x 坐标
        return x;
    }();

    static double& root_pixel_y = []() -> double& {
        static double y = 2801.0; // 默认值，根据测量的 root_node 像素 y 坐标
        return y;
    }();

    // 获取当前设置的分辨率（米/像素）
    static double& resolution = []() -> double& {
        static double res = 0.044; // 默认分辨率值
        return res;
    }();

    // 将输入的坐标相对于 root_node 的像素位置进行调整
    // 计算相对于 root_node 的偏移量
    double relativeX = x - root_pixel_x;
    double relativeY = y - root_pixel_y;

    // 注意：在图像坐标系中，y轴是从上到下的，而在地理坐标系中，纬度是从下到上的
    // 因此，我们需要翻转 y 坐标
    relativeY = -relativeY; // 翻转 y 坐标，使其符合地理坐标系的方向

    // 应用分辨率缩放因子，将像素坐标转换为实际的米单位
    relativeX *= resolution;
    relativeY *= resolution;

    // 创建笛卡尔坐标（相对于 root_node）
    std::array<double, 2> cartesian{relativeX, relativeY};

    // 使用 WGS84 从笛卡尔坐标转换为经纬度
    std::array<double, 2> wgs84Position = ::wgs84::fromCartesian(reference, cartesian);

    return std::make_pair(wgs84Position[0], wgs84Position[1]);
}

// 设置 root_node 在 PNG 中的像素位置
void setRootNodePixelPosition(double x, double y) {
    // 更新 cartesianToLatLon 函数中使用的静态变量
    static double& root_pixel_x_ref = []() -> double& {
        static double x = 3804.0;
        return x;
    }();

    static double& root_pixel_y_ref = []() -> double& {
        static double y = 2801.0;
        return y;
    }();

    root_pixel_x_ref = x;
    root_pixel_y_ref = y;

    std::cout << "Root node pixel position set to (" << x << ", " << y << ")" << std::endl;
}

// 设置 PNG 图像的分辨率（米/像素）
void setResolution(double resolution) {
    // 更新 cartesianToLatLon 函数中使用的静态分辨率变量
    static double& resolution_ref = []() -> double& {
        static double res = 0.044; // 默认分辨率值
        return res;
    }();

    resolution_ref = resolution;

    std::cout << "Resolution set to " << resolution << " meters/pixel" << std::endl;
}

// 计算点到线段的距离
double pointToLineDistance(const topo_geometry::point& p, const topo_geometry::point& lineStart, const topo_geometry::point& lineEnd) {
    // 如果线段实际上是一个点，直接返回点到这个点的距离
    if (equalLineVertex(lineStart, lineEnd)) {
        return boost::geometry::distance(p, lineStart);
    }

    // 计算向量
    double x1 = topo_geometry::getX(lineStart);
    double y1 = topo_geometry::getY(lineStart);
    double x2 = topo_geometry::getX(lineEnd);
    double y2 = topo_geometry::getY(lineEnd);
    double x0 = topo_geometry::getX(p);
    double y0 = topo_geometry::getY(p);

    // 计算线段长度的平方
    double lineLength2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);

    // 计算投影比例
    double t = ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / lineLength2;

    // 如果投影在线段外，返回点到线段端点的最小距离
    if (t < 0.0) {
        return boost::geometry::distance(p, lineStart);
    }
    if (t > 1.0) {
        return boost::geometry::distance(p, lineEnd);
    }

    // 计算投影点
    double projX = x1 + t * (x2 - x1);
    double projY = y1 + t * (y2 - y1);
    topo_geometry::point projPoint(projX, projY);

    // 返回点到投影点的距离
    return boost::geometry::distance(p, projPoint);
}

// 计算局部曲率
double calculateLocalCurvature(const std::vector<topo_geometry::point>& points, int index, int windowSize) {
    int n = points.size();
    double totalAngleChange = 0;

    for (int i = 1; i < windowSize; i++) {
        int prev = (index - i + n) % n;
        int curr = (index - i + 1 + n) % n;
        int next = (index - i + 2 + n) % n;

        // 计算相邻三点的角度
        double ax = topo_geometry::getX(points[prev]) - topo_geometry::getX(points[curr]);
        double ay = topo_geometry::getY(points[prev]) - topo_geometry::getY(points[curr]);
        double bx = topo_geometry::getX(points[next]) - topo_geometry::getX(points[curr]);
        double by = topo_geometry::getY(points[next]) - topo_geometry::getY(points[curr]);

        double lenA = std::sqrt(ax*ax + ay*ay);
        double lenB = std::sqrt(bx*bx + by*by);

        if (lenA < 1e-6 || lenB < 1e-6) continue;

        ax /= lenA; ay /= lenA;
        bx /= lenB; by /= lenB;

        double dotProduct = ax*bx + ay*by;
        dotProduct = std::max(-1.0, std::min(1.0, dotProduct));

        double angle = std::acos(dotProduct) * 180.0 / M_PI;
        totalAngleChange += std::abs(angle - 180.0); // 计算与直线的偏差
    }

    return totalAngleChange / windowSize;
}

// 检测是否是平滑曲线的一部分
bool isPartOfSmoothCurve(const std::vector<topo_geometry::point>& points, int index, int windowSize) {
    double curvature = calculateLocalCurvature(points, index, windowSize);

    // 如果局部曲率在一个合理范围内，可能是平滑曲线的一部分
    // 曲率太小表示直线，曲率太大表示尖角
    return curvature > 5.0 && curvature < 30.0;
}

// 计算点到质心的距离
double distanceToCenter(const topo_geometry::point& p, double centerX, double centerY) {
    double dx = topo_geometry::getX(p) - centerX;
    double dy = topo_geometry::getY(p) - centerY;
    return std::sqrt(dx*dx + dy*dy);
}

// 检测多边形是否近似圆形
bool isApproximatelyCircular(const std::vector<topo_geometry::point>& points) {
    if (points.size() < 8) return false; // 点太少无法判断是否为圆

    // 计算质心
    double centerX = 0, centerY = 0;
    for (const auto& p : points) {
        centerX += topo_geometry::getX(p);
        centerY += topo_geometry::getY(p);
    }
    centerX /= points.size();
    centerY /= points.size();

    // 计算到质心的平均距离
    double avgRadius = 0;
    for (const auto& p : points) {
        avgRadius += distanceToCenter(p, centerX, centerY);
    }
    avgRadius /= points.size();

    // 计算每个点到质心距离与平均距离的差异
    double variance = 0;
    for (const auto& p : points) {
        double radius = distanceToCenter(p, centerX, centerY);
        variance += (radius - avgRadius) * (radius - avgRadius);
    }
    variance /= points.size();

    // 如果方差小，说明点到质心的距离接近一致，可能是圆形
    double relativeVariance = variance / (avgRadius * avgRadius);
    return relativeVariance < 0.05; // 相对方差小于5%可能是圆
}

} // namespace GeometryUtils
} // namespace RMG
