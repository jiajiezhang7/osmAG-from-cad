//
// Created by houjiawei on 18-1-23.
//

#include "Denoise.h"

QImage paintPoints(const char *file_name, const vector<Point> &points, int width, int height) {

    QImage img(width, height, QImage::Format_RGB888);
    img.fill(QColor(255, 255, 255));
    for (vector<Point>::const_iterator itr = points.begin(); itr != points.end(); ++itr) {
        img.setPixel(itr->x(), itr->y(), 0);
    }
    img.save(QString::fromStdString(file_name));
    return img;
}

bool isBlack(uchar *pixel, int black_threshold) {
    return *pixel + *(pixel + 1) + *(pixel + 2) <= black_threshold;
}

int pixel_value(uchar* pixel){
    return *pixel + *(pixel+1) + *(pixel+2);
}

void getPoints_bk(QImage &img, int &black_threshold, vector<Point> &points) {
    for (unsigned int y = 0; y < img.height(); y++) {
        uchar *pointer = img.scanLine(y);
        uchar *endP = pointer + img.width() * 3;
        for (unsigned int x = 0; pointer < endP; pointer += 3, x++) {
            if (isBlack(pointer, black_threshold)) {
                points.push_back(Point(x, y, 0.));
            }
        }
    }
}
void getPoints(QImage &img, int &black_threshold, vector<Point> &points) {
    unsigned int iy=9;
    uchar* pointer = img.scanLine(iy);
    unsigned int ix=9*3;
    pointer+=ix;
    black_threshold=pixel_value(pointer)-1;
    cout<<"black_threshold = "<<black_threshold<<endl;
    long long black_ave=0;
    for (unsigned int y = 0; y < img.height(); y++) {
        uchar *pointer = img.scanLine(y);
        uchar *endP = pointer + img.width() * 3;
        for (unsigned int x = 0; pointer < endP; pointer += 3, x++) {
            int tem_v=pixel_value(pointer);
            if (tem_v<= black_threshold) {
                points.push_back(Point(x, y, 0.));
                black_ave+=tem_v;
            }
        }
    }
    if(points.size()>0.3*img.height()*img.width()){
        black_threshold=black_ave/(points.size()+1);
        points.clear();
        for (unsigned int y = 0; y < img.height(); y++) {
            uchar *pointer = img.scanLine(y);
            uchar *endP = pointer + img.width() * 3;
            for (unsigned int x = 0; pointer < endP; pointer += 3, x++) {
                int tem_v=pixel_value(pointer);
                if (tem_v<= black_threshold) {
                    points.push_back(Point(x, y, 0.));
                }
            }
        }
    }
}

void usage() {
    cout << "Denoises a map by removing a percentage of black pixels " << endl;
}


bool DenoiseImg(const char *input_name, const char *output_name, int &black_threshold, int neighbors, double percentage) {
    QImage img;
    img.load(input_name);
    if (img.isNull()) {
        cerr << "Error loading image " << input_name << endl;
        return false;
    }
    black_threshold *= 3;
    QImage rgb = img.convertToFormat(QImage::Format_RGB888);
    if (rgb.isNull()) {
        cerr << "Error convertig image to RGB" << endl;
        return false;
    }

    vector<CGAL::Point_3<CGAL::Epick>> points;
    getPoints(rgb, black_threshold, points);

    // Removes outliers using erase-remove idiom.
    // The Dereference_property_map property map can be omitted here as it is the default value.
    int sec_percent = percentage >= 1 ? 1 : 0;

#if CGAL_VERSION_NR > 1040201000
    auto new_end = CGAL::remove_outliers<CGAL::Sequential_tag>(points,
                                                            neighbors,
                                                            CGAL::parameters::point_map(CGAL::Identity_property_map<CGAL::Point_3<CGAL::Epick>>())
                                                            .threshold_percent(percentage));

    points.erase(new_end, points.end());

    new_end = CGAL::remove_outliers<CGAL::Sequential_tag>(points,
                                                        neighbors,
                                                        CGAL::parameters::point_map(CGAL::Identity_property_map<CGAL::Point_3<CGAL::Epick>>())
                                                        .threshold_percent(sec_percent));

    points.erase(new_end, points.end());
#else
    auto new_end = CGAL::remove_outliers(points,
                                         neighbors,
                                         CGAL::parameters::point_map(CGAL::Dereference_property_map<CGAL::Point_3<CGAL::Epick>>()).threshold_percent(percentage));
    points.erase(new_end, points.end());

    new_end = CGAL::remove_outliers(points,
                                    neighbors,
                                    CGAL::parameters::point_map(CGAL::Dereference_property_map<CGAL::Point_3<CGAL::Epick>>()).threshold_percent(sec_percent));
    points.erase(new_end, points.end());
#endif

    // Optional: after erase(), use Scott Meyer's "swap trick" to trim excess capacity
    std::vector<CGAL::Point_3<CGAL::Epick>>(points).swap(points);

    paintPoints(output_name, points, rgb.width(), rgb.height());
    return true;
}