// SPDX-License-Identifier: GPL-2.0-only
// Bộ thu trace chỉ quan sát đối tượng ns-3; không dùng RNG hoặc sửa trạng thái mô hình.
#pragma once

#include "ns3/applications-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <filesystem>
#include <fstream>
#include <map>
#include <tuple>

class RunMetrics
{
  public:
    RunMetrics(const std::filesystem::path& goodput, ns3::Time duration);
    void ObserveQueues(ns3::Ptr<ns3::QueueDisc> disc, ns3::Ptr<ns3::NetDevice> device,
                       const std::string& location);
    void ObserveForward(ns3::Ptr<ns3::QueueDisc> disc, ns3::Ptr<ns3::NetDevice> device);
    void ObserveSender(ns3::Ptr<ns3::OnOffApplication> app, uint32_t flow);
    void RegisterFlow(ns3::Ipv4Address source, ns3::Ipv4Address destination,
                      uint16_t destinationPort, uint32_t flow, const std::string& group);
    void RecordSetting(const std::string& name, const std::string& value);
    void RecordAttributes(ns3::Ptr<ns3::Object> object, const std::string& prefix,
                          const std::vector<std::string>& names);
    void Finish(ns3::Ptr<ns3::QueueDisc> forward);

  private:
    const char* Phase() const;
    void QueueState(ns3::QueueDisc* disc, ns3::Ptr<const ns3::QueueDiscItem> item);
    void QueueDrop(std::string location, std::string stage, ns3::Ptr<const ns3::QueueDiscItem> item,
                   const char* reason);
    void DeviceDrop(std::string location, ns3::Ptr<const ns3::Packet> packet);
    void Rtt(uint32_t flow, std::string metric, ns3::Time previous, ns3::Time current);
    void Transmit(ns3::Ptr<const ns3::Packet> packet);

    ns3::Time m_duration;
    std::ofstream m_queue, m_drops, m_rtt, m_link, m_config;
    uint64_t m_forwardDrops{0};
    // One TCP application per source/destination pair in this experiment.
    std::map<std::tuple<uint32_t, uint32_t, uint16_t>,
             std::pair<uint32_t, std::string>> m_flows;
};
