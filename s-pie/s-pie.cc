// SPDX-License-Identifier: GPL-2.0-only
// Một chương trình chung cho hai kịch bản. Xem README.md để đổi cấu hình.
#include "spie-queue-disc.h"
#include "run-metrics.h"
#include "ns3/applications-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <fstream>
#include <iostream>
#include <vector>

using namespace ns3;

// Trace tùy chọn để so quyết định nhận/loại gói của PIE và S-PIE theo thứ tự.
static void
WriteQueueEvent(std::ostream* stream, std::string event, Ptr<const QueueDiscItem> item)
{
    *stream << Simulator::Now().GetNanoSeconds() << ',' << event << ','
            << item->GetPacket()->GetUid() << ',' << item->GetSize() << '\n';
}

int
main(int argc, char* argv[])
{
    uint32_t scenario = 1;
    uint32_t duration = 30;
    std::string aqm = "Spie";
    std::string output = "goodput.csv";
    std::string smallRate = "1Mbps", largeRate = "50Mbps", equalRate = "10Mbps";
    std::string onTime = "ns3::ExponentialRandomVariable[Mean=1]";
    std::string offTime = "ns3::ExponentialRandomVariable[Mean=1]";
    std::string accessRate = "100Mbps", coreRate = "50Mbps";
    std::string accessDelay = "5ms", coreDelay = "20ms";
    std::string eventFile;
    std::string limit = "50p";
    uint32_t flows = 100;
    uint32_t payload = 1000;

    // Khởi tạo cấu hình chung trước Parse: có thể ghi đè từ dòng lệnh.
    for (std::string type : {"ns3::PieQueueDisc", "ns3::SpieQueueDisc"})
    {
        Config::SetDefault(type + "::QueueDelayReference", TimeValue(MilliSeconds(5)));
        Config::SetDefault(type + "::Tupdate", TimeValue(MilliSeconds(30)));
        Config::SetDefault(type + "::DequeueThreshold", UintegerValue(10000));
        Config::SetDefault(type + "::MaxBurstAllowance", TimeValue(MilliSeconds(100)));
        Config::SetDefault(type + "::UseDequeueRateEstimator", BooleanValue(true));
    }
    Config::SetDefault("ns3::TcpL4Protocol::SocketType", TypeIdValue(TcpNewReno::GetTypeId()));
    Config::SetDefault("ns3::TcpSocket::SegmentSize", UintegerValue(1000));
    Config::SetDefault("ns3::TcpSocketBase::UseEcn", EnumValue(TcpSocketState::Off));
    Config::SetDefault("ns3::RedQueueDisc::MeanPktSize", UintegerValue(1000));
    Config::SetDefault("ns3::RedQueueDisc::UseEcn", BooleanValue(false));
    Config::SetDefault("ns3::CoDelQueueDisc::UseEcn", BooleanValue(false));

    CommandLine cmd(__FILE__);
    cmd.AddValue("scenario", "1: mixed rates; 2: uniform rates", scenario);
    cmd.AddValue("aqm", "Spie, Pie, Red or CoDel", aqm);
    cmd.AddValue("duration", "Whole seconds of traffic", duration);
    cmd.AddValue("flows", "Even number of sender/receiver pairs", flows);
    cmd.AddValue("smallRate", "Scenario 1 first group ON rate", smallRate);
    cmd.AddValue("largeRate", "Scenario 1 second group ON rate", largeRate);
    cmd.AddValue("equalRate", "Scenario 2 ON rate", equalRate);
    cmd.AddValue("onTime", "ON random variable specification", onTime);
    cmd.AddValue("offTime", "OFF random variable specification", offTime);
    cmd.AddValue("payload", "Bytes per application write", payload);
    cmd.AddValue("limit", "Forward bottleneck queue limit", limit);
    cmd.AddValue("output", "Per-flow goodput CSV path", output);
    cmd.AddValue("coreRate", "Bottleneck capacity (also used by RED)", coreRate);
    cmd.AddValue("coreDelay", "One-way bottleneck propagation delay", coreDelay);
    cmd.AddValue("accessRate", "Access link capacity", accessRate);
    cmd.AddValue("accessDelay", "One-way access propagation delay", accessDelay);
    cmd.AddValue("events", "Optional enqueue/drop event CSV path", eventFile);
    cmd.Parse(argc, argv);
    Config::SetDefault("ns3::RedQueueDisc::LinkBandwidth", DataRateValue(DataRate(coreRate)));
    Config::SetDefault("ns3::RedQueueDisc::LinkDelay", TimeValue(Time(coreDelay)));
    NS_ABORT_MSG_IF(scenario != 1 && scenario != 2, "scenario must be 1 or 2");
    NS_ABORT_MSG_IF(!flows || flows % 2 || flows > 32000, "flows must be even, 2..32000");
    NS_ABORT_MSG_IF(!duration || duration > 86400 || !payload, "Invalid duration or payload");
    NS_ABORT_MSG_IF(aqm != "Spie" && aqm != "Pie" && aqm != "Red" && aqm != "CoDel",
                    "Unknown AQM");
    // Ngăn trace tùy chọn ghi đè một trong các tệp kết quả của cùng run.
    const std::filesystem::path goodput(output);
    if (!eventFile.empty())
    {
        for (auto suffix : {"", "-queue", "-drops", "-rtt", "-link", "-config"})
        {
            auto path = suffix[0] ? goodput.parent_path() / (goodput.stem().string() + suffix + ".csv")
                                  : goodput;
            NS_ABORT_MSG_IF(std::filesystem::weakly_canonical(eventFile) ==
                                std::filesystem::weakly_canonical(path),
                            "Choose a distinct --events path");
        }
    }
    RunMetrics metrics(goodput, Seconds(duration));
    metrics.RecordSetting("ns3_version", "3.45");
    metrics.RecordSetting("scenario", std::to_string(scenario));
    metrics.RecordSetting("aqm", aqm);
    metrics.RecordSetting("seed", std::to_string(RngSeedManager::GetSeed()));
    metrics.RecordSetting("run", std::to_string(RngSeedManager::GetRun()));
    metrics.RecordSetting("flows", std::to_string(flows));
    metrics.RecordSetting("traffic_s", std::to_string(duration));
    metrics.RecordSetting("drain_s", "5");
    metrics.RecordSetting("coreRate", coreRate);
    metrics.RecordSetting("coreDelay", coreDelay);
    metrics.RecordSetting("accessRate", accessRate);
    metrics.RecordSetting("accessDelay", accessDelay);
    metrics.RecordSetting("smallRate", smallRate);
    metrics.RecordSetting("largeRate", largeRate);
    metrics.RecordSetting("equalRate", equalRate);
    metrics.RecordSetting("payload", std::to_string(payload));
    metrics.RecordSetting("onTime", onTime);
    metrics.RecordSetting("offTime", offTime);
    std::ofstream csv(output);
    NS_ABORT_MSG_IF(!csv, "Cannot write " << output);
    csv << "end_s,flow,on_rate,payload_bytes,goodput_mbps\n";

    NodeContainer routers, senders, receivers;
    routers.Create(2);
    senders.Create(flows);
    receivers.Create(flows);
    InternetStackHelper stack;
    stack.Install(routers);
    stack.Install(senders);
    stack.Install(receivers);

    // Cài qdisc trước khi gán IP, để không phát sinh qdisc mặc định.
    PointToPointHelper coreLink;
    coreLink.SetDeviceAttribute("DataRate", StringValue(coreRate));
    coreLink.SetChannelAttribute("Delay", StringValue(coreDelay));
    coreLink.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", StringValue("1p"));
    auto core = coreLink.Install(routers);
    TrafficControlHelper forward, reverse, accessQueue;
    forward.SetRootQueueDisc("ns3::" + aqm + "QueueDisc", "MaxSize", StringValue(limit));
    auto measured = forward.Install(core.Get(0)).Get(0);
    metrics.ObserveQueues(measured, core.Get(0), "core-forward");
    metrics.ObserveForward(measured, core.Get(0));
    metrics.RecordAttributes(routers.Get(0)->GetObject<TcpL4Protocol>(), "tcp",
                             {"SocketType", "RecoveryType"});
    // Lưu attribute thực tế sau khi áp dụng mọi override, kể cả tham số Sketch.
    auto type = measured->GetInstanceTypeId();
    for (std::size_t i = 0; i < type.GetAttributeN(); ++i)
    {
        auto attribute = type.GetAttribute(i);
        if ((attribute.flags & TypeId::ATTR_GET) && attribute.accessor->HasGetter())
        {
            metrics.RecordAttributes(measured, "aqm", {attribute.name});
        }
        else
        {
            metrics.RecordSetting("aqm.configured." + attribute.name,
                                  attribute.initialValue->SerializeToString(attribute.checker));
        }
    }
    std::ofstream events;
    if (!eventFile.empty())
    {
        NS_ABORT_MSG_IF(eventFile == output, "Choose separate event and goodput files");
        events.open(eventFile);
        NS_ABORT_MSG_IF(!events, "Cannot write " << eventFile);
        events << "time_ns,event,packet_uid,size_bytes\n";
        for (std::string name : {"Enqueue", "Drop"})
        {
            measured->TraceConnectWithoutContext(
                name, MakeBoundCallback(&WriteQueueEvent, static_cast<std::ostream*>(&events), name));
        }
    }
    if (aqm == "Spie")
    {
        DynamicCast<SpieQueueDisc>(measured)->AssignStreams(10);
    }
    else if (aqm == "Pie")
    {
        DynamicCast<PieQueueDisc>(measured)->AssignStreams(10);
    }
    reverse.SetRootQueueDisc("ns3::FifoQueueDisc", "MaxSize", StringValue("50p"));
    auto reverseDisc = reverse.Install(core.Get(1)).Get(0);
    metrics.ObserveQueues(reverseDisc, core.Get(1), "core-reverse");
    accessQueue.SetRootQueueDisc("ns3::FifoQueueDisc", "MaxSize", StringValue("100p"));
    Ipv4AddressHelper ip;
    ip.SetBase("10.0.0.0", "255.255.255.252");
    ip.Assign(core);

    PointToPointHelper access;
    access.SetDeviceAttribute("DataRate", StringValue(accessRate));
    access.SetChannelAttribute("Delay", StringValue(accessDelay));
    access.SetQueue("ns3::DropTailQueue<Packet>", "MaxSize", StringValue("1p"));
    auto starts = CreateObject<UniformRandomVariable>();
    starts->SetStream(20);
    std::vector<Ptr<PacketSink>> sinks;
    std::vector<std::string> rates;
    for (uint32_t i = 0; i < flows; ++i)
    {
        auto left = access.Install(senders.Get(i), routers.Get(0));
        auto right = access.Install(routers.Get(1), receivers.Get(i));
        auto leftQueues = accessQueue.Install(left);
        auto rightQueues = accessQueue.Install(right);
        std::string id = std::to_string(i + 1);
        for (uint32_t end = 0; end < 2; ++end)
        {
            metrics.ObserveQueues(leftQueues.Get(end), left.Get(end),
                                  "left-" + id + (end == 0 ? "-forward" : "-reverse"));
            metrics.ObserveQueues(rightQueues.Get(end), right.Get(end),
                                  "right-" + id + (end == 0 ? "-forward" : "-reverse"));
        }
        ip.NewNetwork();
        auto sourceAddress = ip.Assign(left).GetAddress(0);
        ip.NewNetwork();
        auto dest = ip.Assign(right).GetAddress(1);
        constexpr uint16_t port = 5000;
        metrics.RegisterFlow(sourceAddress, dest, port, i + 1,
                             scenario == 2 ? "equal" : (i < flows / 2 ? "small" : "large"));
        PacketSinkHelper receiver("ns3::TcpSocketFactory",
                                  InetSocketAddress(Ipv4Address::GetAny(), port));
        auto sink = receiver.Install(receivers.Get(i));
        sink.Start(Seconds(0));
        sinks.push_back(DynamicCast<PacketSink>(sink.Get(0)));

        std::string rate = scenario == 2 ? equalRate : (i < flows / 2 ? smallRate : largeRate);
        rates.push_back(rate);
        OnOffHelper source("ns3::TcpSocketFactory", InetSocketAddress(dest, port));
        source.SetAttribute("DataRate", DataRateValue(DataRate(rate)));
        source.SetAttribute("PacketSize", UintegerValue(payload));
        source.SetAttribute("OnTime", StringValue(onTime));
        source.SetAttribute("OffTime", StringValue(offTime));
        auto app = source.Install(senders.Get(i));
        // Hai stream ON/OFF riêng cho mỗi luồng, dùng lại khi đổi AQM.
        source.AssignStreams(NodeContainer(senders.Get(i)), 100 + 2 * i);
        Time start = Seconds(starts->GetValue(0, 0.1));
        app.Start(start);
        // Socket tồn tại sau StartApplication; 1 tick sau start vẫn trước ACK đầu tiên.
        Simulator::Schedule(start + TimeStep(1), &RunMetrics::ObserveSender, &metrics,
                            DynamicCast<OnOffApplication>(app.Get(0)), i + 1);
        app.Stop(Seconds(duration));
    }
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // Đếm payload mới nhận tại mỗi sink trong từng giây, bao gồm luồng 0 byte.
    std::vector<uint64_t> previous(flows, 0);
    for (uint32_t second = 1; second <= duration; ++second)
    {
        Simulator::Schedule(Seconds(second), [&, second]() {
            for (uint32_t i = 0; i < flows; ++i)
            {
                const auto total = sinks[i]->GetTotalRx();
                const auto bytes = total - previous[i];
                previous[i] = total;
                csv << second << ',' << i + 1 << ',' << rates[i] << ',' << bytes << ','
                    << bytes * 8.0 / 1e6 << '\n';
            }
        });
    }
    Simulator::Stop(Seconds(duration + 5)); // Thống kê qdisc gồm cả 5 s xả hàng đợi.
    Simulator::Run();
    metrics.Finish(measured);
    std::cout << measured->GetStats() << std::endl;
    Simulator::Destroy();
}

