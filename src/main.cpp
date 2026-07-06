#include <windows.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <stdexcept>
#include <string>
#include <thread>

#include "mozaAPI.h"

using Clock = std::chrono::steady_clock;
using namespace std::chrono_literals;

namespace {

constexpr unsigned long kLoopedDurationMs = 0xffff;
constexpr auto kEffectRefreshTime = std::chrono::milliseconds(55000);
constexpr auto kShockEvery = std::chrono::milliseconds(2200);
constexpr unsigned long kShockDurationMs = 120;

bool g_keepRunning = true;

int clampInt(int value, int low, int high)
{
    return std::clamp(value, low, high);
}

std::string readTextFile(const std::filesystem::path& path)
{
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open " + path.string());
    }

    return std::string(std::istreambuf_iterator<char>(file), {});
}

std::optional<std::string> objectForKey(const std::string& text, const std::string& key)
{
    const auto keyText = '"' + key + '"';
    const auto keyPos = text.find(keyText);
    if (keyPos == std::string::npos) {
        return std::nullopt;
    }

    const auto start = text.find('{', keyPos + keyText.size());
    if (start == std::string::npos) {
        return std::nullopt;
    }

    int depth = 0;
    for (std::size_t i = start; i < text.size(); ++i) {
        if (text[i] == '{') {
            ++depth;
        } else if (text[i] == '}') {
            --depth;
            if (depth == 0) {
                return text.substr(start, i - start + 1);
            }
        }
    }

    return std::nullopt;
}

int findInt(const std::string& text, const std::string& key, int fallback)
{
    const std::regex rx("\"" + key + R"("\s*:\s*(-?\d+))");
    std::smatch match;
    if (!std::regex_search(text, match, rx)) {
        return fallback;
    }
    return std::stoi(match[1].str());
}

bool findBool(const std::string& text, const std::string& key, bool fallback)
{
    const std::regex rx("\"" + key + R"("\s*:\s*(true|false))");
    std::smatch match;
    if (!std::regex_search(text, match, rx)) {
        return fallback;
    }
    return match[1].str() == "true";
}

struct WheelbaseSettings {
    int limitAngle = 900;
    int ffbStrength = 65;
    int roadSensitivity = 5;
    int naturalDamper = 25;
    int naturalFriction = 15;
    int limitWheelSpeed = 50;
    int peakTorqueLimit = 80;
};

struct SineSettings {
    bool active = false;
    int magnitude = 0;
    int periodMs = 80;
    int phase = 0;
    int offset = 0;
};

struct ShockSettings {
    bool active = false;
    int magnitude = 0;
};

struct SpringSettings {
    bool active = false;
    int offset = 0;
    int deadBand = 0;
    int positiveCoefficient = 0;
    int negativeCoefficient = 0;
};

struct AppConfig {
    WheelbaseSettings wheelbase;
    std::map<std::string, int> equalizer;
    SineSettings sine;
    ShockSettings shock;
    SpringSettings spring;
};

AppConfig parseConfig(const std::string& json)
{
    AppConfig cfg;

    if (auto body = objectForKey(json, "wheelbase_basic_settings")) {
        cfg.wheelbase.limitAngle = clampInt(findInt(*body, "limit_angle", cfg.wheelbase.limitAngle), 90, 2000);
        cfg.wheelbase.ffbStrength = clampInt(findInt(*body, "game_ffb_strength", cfg.wheelbase.ffbStrength), 0, 100);
        cfg.wheelbase.roadSensitivity = clampInt(findInt(*body, "road_sensitivity", cfg.wheelbase.roadSensitivity), 0, 10);
        cfg.wheelbase.naturalDamper = clampInt(findInt(*body, "natural_damper", cfg.wheelbase.naturalDamper), 0, 100);
        cfg.wheelbase.naturalFriction = clampInt(findInt(*body, "natural_friction", cfg.wheelbase.naturalFriction), 0, 100);
        cfg.wheelbase.limitWheelSpeed = clampInt(findInt(*body, "limit_wheel_speed", cfg.wheelbase.limitWheelSpeed), 10, 100);
        cfg.wheelbase.peakTorqueLimit = clampInt(findInt(*body, "peak_torque_limit", cfg.wheelbase.peakTorqueLimit), 50, 100);
    }

    if (auto body = objectForKey(json, "road_vibrations_equalizer")) {
        for (const std::string key : {
                 "EqualizerAmp7_5",
                 "EqualizerAmp13",
                 "EqualizerAmp22_5",
                 "EqualizerAmp39",
                 "EqualizerAmp55",
                 "EqualizerAmp100",
             }) {
            cfg.equalizer[key] = clampInt(findInt(*body, key, 0), 0, 100);
        }
    }

    if (auto effects = objectForKey(json, "directinput_effects")) {
        if (auto body = objectForKey(*effects, "periodic_sine_vibration")) {
            cfg.sine.active = findBool(*body, "active", cfg.sine.active);
            cfg.sine.magnitude = clampInt(findInt(*body, "magnitude", cfg.sine.magnitude), -10000, 10000);
            cfg.sine.periodMs = clampInt(findInt(*body, "period_ms", cfg.sine.periodMs), 10, 100);
            cfg.sine.phase = clampInt(findInt(*body, "phase", cfg.sine.phase), 0, 36000);
            cfg.sine.offset = clampInt(findInt(*body, "offset", cfg.sine.offset), -10000, 10000);
        }

        if (auto body = objectForKey(*effects, "constant_shock_force")) {
            cfg.shock.active = findBool(*body, "active", cfg.shock.active);
            cfg.shock.magnitude = clampInt(findInt(*body, "magnitude", cfg.shock.magnitude), -10000, 10000);
        }

        if (auto body = objectForKey(*effects, "spring_return_force")) {
            cfg.spring.active = findBool(*body, "active", cfg.spring.active);
            cfg.spring.offset = clampInt(findInt(*body, "offset", cfg.spring.offset), -10000, 10000);
            cfg.spring.deadBand = clampInt(findInt(*body, "dead_band", cfg.spring.deadBand), 0, 10000);
            cfg.spring.positiveCoefficient = clampInt(findInt(*body, "positive_coefficient", cfg.spring.positiveCoefficient), 0, 10000);
            cfg.spring.negativeCoefficient = clampInt(findInt(*body, "negative_coefficient", cfg.spring.negativeCoefficient), 0, 10000);
        }
    }

    return cfg;
}

void logSdkCall(const char* name, ERRORCODE err)
{
    if (err != NORMAL) {
        std::cout << name << " -> error " << static_cast<int>(err) << '\n';
    }
}

void applyWheelbaseSettings(const WheelbaseSettings& cfg, const std::map<std::string, int>& equalizer)
{
    logSdkCall("setMotorLimitAngle", moza::setMotorLimitAngle(cfg.limitAngle, cfg.limitAngle));
    logSdkCall("setMotorFfbStrength", moza::setMotorFfbStrength(cfg.ffbStrength));
    logSdkCall("setMotorRoadSensitivity", moza::setMotorRoadSensitivity(cfg.roadSensitivity));
    logSdkCall("setMotorNaturalDamper", moza::setMotorNaturalDamper(cfg.naturalDamper));
    logSdkCall("setMotorNaturalFriction", moza::setMotorNaturalFriction(cfg.naturalFriction));
    logSdkCall("setMotorLimitWheelSpeed", moza::setMotorLimitWheelSpeed(cfg.limitWheelSpeed));
    logSdkCall("setMotorPeakTorque", moza::setMotorPeakTorque(cfg.peakTorqueLimit));

    if (!equalizer.empty()) {
        logSdkCall("setMotorEqualizerAmp", moza::setMotorEqualizerAmp(equalizer));
    }
}

class AppWindow {
public:
    AppWindow()
    {
        WNDCLASSA wc{};
        wc.lpfnWndProc = DefWindowProcA;
        wc.hInstance = GetModuleHandleA(nullptr);
        wc.lpszClassName = "MozaEffectMvpWindow";

        RegisterClassA(&wc);

        hwnd_ = CreateWindowExA(
            0,
            wc.lpszClassName,
            "MOZA effect MVP",
            WS_OVERLAPPEDWINDOW,
            CW_USEDEFAULT,
            CW_USEDEFAULT,
            420,
            160,
            nullptr,
            nullptr,
            wc.hInstance,
            nullptr);

        if (!hwnd_) {
            throw std::runtime_error("Failed to create Win32 window");
        }

        ShowWindow(hwnd_, SW_SHOW);
        UpdateWindow(hwnd_);
        SetForegroundWindow(hwnd_);
        SetFocus(hwnd_);
    }

    ~AppWindow()
    {
        if (hwnd_) {
            DestroyWindow(hwnd_);
        }
    }

    HWND get() const { return hwnd_; }

private:
    HWND hwnd_ = nullptr;
};

template <class EffectPtr>
bool startEffect(const char* name, const EffectPtr& effect)
{
    if (!effect) {
        return false;
    }

    try {
        effect->start();
        return true;
    } catch (const std::exception& e) {
        std::cout << name << " start failed: " << e.what() << '\n';
    } catch (...) {
        std::cout << name << " start failed\n";
    }

    return false;
}

template <class EffectPtr>
void stopEffect(const char* name, const EffectPtr& effect)
{
    if (!effect) {
        return;
    }

    try {
        effect->stop();
    } catch (const std::exception& e) {
        std::cout << name << " stop failed: " << e.what() << '\n';
    } catch (...) {
        std::cout << name << " stop failed\n";
    }
}

class MozaEffects {
public:
    MozaEffects(HWND hwnd, const AppConfig& cfg)
        : cfg_(cfg)
    {
        ERRORCODE err = NORMAL;

        if (cfg_.sine.active) {
            sine_ = moza::createWheelbaseETSine(hwnd, err);
            logSdkCall("createWheelbaseETSine", err);
            if (sine_) {
                const auto periodUs = static_cast<unsigned long>(cfg_.sine.periodMs) * 1000UL;
                sine_->setMagnitude(static_cast<unsigned long>(std::abs(cfg_.sine.magnitude)));
                sine_->setPeriod(periodUs);
                sine_->setPhase(static_cast<unsigned long>(cfg_.sine.phase));
                std::cout << "Sine vibration: magnitude " << std::abs(cfg_.sine.magnitude)
                          << ", period " << cfg_.sine.periodMs << " ms"
                          << " (" << periodUs << " us for DirectInput)\n";
                sine_->setOffset(cfg_.sine.offset);
                sine_->setDuration(kLoopedDurationMs);
                sine_->setGain(10000);
            }
        }

        if (cfg_.spring.active) {
            spring_ = moza::createWheelbaseETSpring(hwnd, err);
            logSdkCall("createWheelbaseETSpring", err);
            if (spring_) {
                spring_->setOffset(cfg_.spring.offset);
                spring_->setDeadBand(cfg_.spring.deadBand);
                spring_->setPositiveCoefficient(cfg_.spring.positiveCoefficient);
                spring_->setNegativeCoefficient(cfg_.spring.negativeCoefficient);
                spring_->setPositiveSaturation(10000);
                spring_->setNegativeSaturation(10000);
                spring_->setDuration(kLoopedDurationMs);
                spring_->setGain(10000);
            }
        }

        if (cfg_.shock.active) {
            shock_ = moza::createWheelbaseETConstantForce(hwnd, err);
            logSdkCall("createWheelbaseETConstantForce", err);
            if (shock_) {
                shock_->setMagnitude(cfg_.shock.magnitude);
                shock_->setDuration(kShockDurationMs);
                shock_->setGain(10000);
                std::cout << "Shock auto pulse: magnitude " << cfg_.shock.magnitude
                          << ", every " << kShockEvery.count() << " ms"
                          << ", duration " << kShockDurationMs << " ms\n";
            }
        }
    }

    void start()
    {
        if (enabled_) {
            return;
        }

        const auto now = Clock::now();
        bool anyEffectReady = false;

        if (startEffect("sine", sine_)) {
            anyEffectReady = true;
            nextSineRefresh_ = now + kEffectRefreshTime;
        }

        if (startEffect("spring", spring_)) {
            anyEffectReady = true;
            nextSpringRefresh_ = now + kEffectRefreshTime;
        }

        if (shock_) {
            anyEffectReady = true;
            nextShock_ = now + 500ms;
        }

        enabled_ = anyEffectReady;
        std::cout << (enabled_ ? "Effects enabled\n" : "No effects were created\n");
    }

    void stop()
    {
        stopEffect("shock", shock_);
        stopEffect("spring", spring_);
        stopEffect("sine", sine_);

        enabled_ = false;
        std::cout << "Effects disabled\n";
    }

    void toggle()
    {
        enabled_ ? stop() : start();
    }

    void triggerShock()
    {
        if (!enabled_) {
            std::cout << "Effects are disabled; F1 enables them\n";
            return;
        }
        startEffect("shock", shock_);
    }

    void tick()
    {
        if (!enabled_) {
            return;
        }

        const auto now = Clock::now();

        if (sine_ && now >= nextSineRefresh_) {
            if (startEffect("sine", sine_)) {
                nextSineRefresh_ = now + kEffectRefreshTime;
            }
        }

        if (spring_ && now >= nextSpringRefresh_) {
            if (startEffect("spring", spring_)) {
                nextSpringRefresh_ = now + kEffectRefreshTime;
            }
        }

        if (shock_ && now >= nextShock_) {
            startEffect("shock", shock_);
            nextShock_ = now + kShockEvery;
        }
    }

private:
    AppConfig cfg_;
    bool enabled_ = false;
    std::shared_ptr<RS21::direct_input::ETSine> sine_;
    std::shared_ptr<RS21::direct_input::ETConstantForce> shock_;
    std::shared_ptr<RS21::direct_input::ETSpring> spring_;
    Clock::time_point nextSineRefresh_{};
    Clock::time_point nextSpringRefresh_{};
    Clock::time_point nextShock_{};
};

BOOL WINAPI onConsoleEvent(DWORD event)
{
    if (event == CTRL_C_EVENT || event == CTRL_CLOSE_EVENT || event == CTRL_BREAK_EVENT) {
        g_keepRunning = false;
        return TRUE;
    }
    return FALSE;
}

std::filesystem::path configPathFromArgs(int argc, char** argv)
{
    if (argc > 1) {
        return std::filesystem::path(argv[1]);
    }

    const auto cwdPath = std::filesystem::current_path() / "output.txt";
    if (std::filesystem::exists(cwdPath)) {
        return cwdPath;
    }

    const auto projectPath = std::filesystem::path(PROJECT_ROOT_PATH) / "output.txt";
    if (std::filesystem::exists(projectPath)) {
        return projectPath;
    }

    return cwdPath;
}

void pumpWindowMessages()
{
    MSG msg{};
    while (PeekMessageA(&msg, nullptr, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessageA(&msg);
    }
}

} // namespace

int main(int argc, char** argv)
{
    SetConsoleCtrlHandler(onConsoleEvent, TRUE);

    try {
        const auto configPath = configPathFromArgs(argc, argv);
        const auto config = parseConfig(readTextFile(configPath));

        std::cout << "Loaded " << configPath.string() << '\n';
        std::cout << "F1 toggles effects. F2 fires one shock. Esc exits.\n";

        AppWindow window;

        moza::installMozaSDK();
        std::this_thread::sleep_for(2500ms);

        ERRORCODE wheelbaseErr = NORMAL;
        const char* wheelbaseName = moza::getDeviceParent(PRODUCT_WHEELBASE, wheelbaseErr);
        const bool hasWheelbase = wheelbaseErr == NORMAL && wheelbaseName && wheelbaseName[0] != '\0';

        if (hasWheelbase) {
            std::cout << "Wheelbase: " << wheelbaseName << '\n';
            applyWheelbaseSettings(config.wheelbase, config.equalizer);
        } else {
            std::cout << "Wheelbase settings API did not find a base, error "
                      << static_cast<int>(wheelbaseErr)
                      << ". Skipping motor profile and trying DirectInput effects.\n";
        }

        std::cout << "Keep the MOZA effect MVP window focused while effects start.\n";

        MozaEffects effects(window.get(), config);
        effects.start();

        while (g_keepRunning) {
            pumpWindowMessages();

            if (GetAsyncKeyState(VK_F1) & 1) {
                effects.toggle();
            }

            if (GetAsyncKeyState(VK_F2) & 1) {
                effects.triggerShock();
            }

            if (GetAsyncKeyState(VK_ESCAPE) & 1) {
                g_keepRunning = false;
            }

            effects.tick();
            std::this_thread::sleep_for(10ms);
        }

        effects.stop();
        moza::stopForceFeedback();
        moza::removeMozaSDK();
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Fatal: " << e.what() << '\n';
        moza::stopForceFeedback();
        moza::removeMozaSDK();
        return 1;
    }
}
