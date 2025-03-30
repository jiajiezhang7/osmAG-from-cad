#pragma once

#include <yaml-cpp/yaml.h>
#include <string>

class ParamsLoader {
public:
    static ParamsLoader& getInstance() {
        static ParamsLoader instance;
        return instance;
    }

    void loadParams(const std::string& file_path) {
        params = YAML::LoadFile(file_path);
    }

    bool getCleanInput() const {
        return params["map_preprocessing"]["clean_input"].as<bool>();
    }

    bool getRemoveFurniture() const {
        return params["map_preprocessing"]["remove_furniture"].as<bool>();
    }

    double getResolution() const {
        return params["map_preprocessing"]["resolution"].as<double>();
    }

    double getDoorWidth() const {
        return params["map_preprocessing"]["door_width"].as<double>();
    }

    double getCorridorWidth() const {
        return params["map_preprocessing"]["corridor_width"].as<double>();
    }

    double getNoisePercent() const {
        return params["map_preprocessing"]["noise_percent"].as<double>();
    }

    bool getSimplifyEnabled() const {
        return params["polygon_processing"]["simplify"]["enabled"].as<bool>();
    }

    double getSimplifyTolerance() const {
        return params["polygon_processing"]["simplify"]["tolerance"].as<double>();
    }

    bool getSpikeRemovalEnabled() const {
        return params["polygon_processing"]["spike_removal"]["enabled"].as<bool>();
    }

    double getSpikeAngleThreshold() const {
        return params["polygon_processing"]["spike_removal"]["angle_threshold"].as<double>();
    }

    double getSpikeDistanceThreshold() const {
        return params["polygon_processing"]["spike_removal"]["distance_threshold"].as<double>();
    }

private:
    ParamsLoader() = default;
    YAML::Node params;
};
