// SPDX-License-Identifier: GPL-2.0-only
#include "run-metrics.h"
#include "ns3/core-module.h"
#include "ns3/socket.h"
#include "ns3/ipv4-header.h"
#include "ns3/tcp-header.h"
#include "ns3/ppp-header.h"

using namespace ns3;

namespace
{
// Mọi CSV phụ có cùng tiền tố với goodput, kể cả khi người dùng đổi thư mục.
std::ofstream OpenCsv(const std::filesystem::path& goodput, const std::string& suffix,
                      const std::string& header)
{
    auto path = goodput.parent_path() / (goodput.stem().string() + suffix + ".csv");
    std::ofstream stream(path);
    NS_ABORT_MSG_IF(!stream, "Cannot write " << path);
    stream.exceptions(std::ios::badbit | std::ios::failbit);
    stream << header << '\n';
    return stream;
}

std::string CsvField(const std::string& value)
{
    std::string field = "\"";
    for (char ch : value)
    {
        if (ch == '"')
        {
            field += '"';
        }
        field += ch;
    }
    return field + '"';
}

void Connect(Ptr<Object> object, const std::string& trace, const CallbackBase& cb)
{
    NS_ABORT_MSG_IF(!object->TraceConnectWithoutContext(trace, cb), "Missing trace: " << trace);
}
} // namespace

RunMetrics::RunMetrics(const std::filesystem::path& path, Time duration)
    : m_duration(duration),
      m_queue(OpenCsv(path, "-queue", "time_ns,phase,packets,bytes")),
      m_drops(OpenCsv(path, "-drops", "time_ns,phase,location,layer,stage,reason,packet_uid,size_bytes")),
      m_rtt(OpenCsv(path, "-rtt", "time_ns,phase,flow,metric,value_ns")),
      m_link(OpenCsv(path, "-link", "time_ns,phase,wire_bytes,flow,group,src_ip,dst_ip,protocol,src_port,dst_port")),
      m_config(OpenCsv(path, "-config", "key,value"))
{
    m_queue << "0,traffic,0,0\n";
}

const char* RunMetrics::Phase() const
{
    return Simulator::Now() < m_duration ? "traffic" : "drain";
}

void RunMetrics::ObserveQueues(Ptr<QueueDisc> disc, Ptr<NetDevice> device,
                               const std::string& location)
{
    for (std::string stage : {"DropBeforeEnqueue", "DropAfterDequeue"})
    {
        Connect(disc, stage, MakeCallback(&RunMetrics::QueueDrop, this).Bind(location, stage));
    }
    auto queue = DynamicCast<PointToPointNetDevice>(device)->GetQueue();
    Connect(queue, "Drop", MakeCallback(&RunMetrics::DeviceDrop, this).Bind(location));
}

void RunMetrics::QueueDrop(std::string location, std::string stage, Ptr<const QueueDiscItem> item,
                           const char* reason)
{
    if (location == "core-forward")
    {
        ++m_forwardDrops;
    }
    m_drops << Simulator::Now().GetNanoSeconds() << ',' << Phase() << ',' << location
            << ",qdisc," << stage << ',' << CsvField(reason) << ','
            << item->GetPacket()->GetUid() << ',' << item->GetSize() << '\n';
}

void RunMetrics::DeviceDrop(std::string location, Ptr<const Packet> packet)
{
    m_drops << Simulator::Now().GetNanoSeconds() << ',' << Phase() << ',' << location
            << ",device,Drop,Device queue drop," << packet->GetUid() << ',' << packet->GetSize()
            << '\n';
}

void RunMetrics::ObserveForward(Ptr<QueueDisc> disc, Ptr<NetDevice> device)
{
    // Hai bộ đếm đã được ns-3 cập nhật trước khi phát Enqueue/Dequeue.
    for (std::string trace : {"Enqueue", "Dequeue"})
    {
        Connect(disc, trace, MakeCallback(&RunMetrics::QueueState, this).Bind(PeekPointer(disc)));
    }
    Connect(device, "PhyTxBegin", MakeCallback(&RunMetrics::Transmit, this));
}

void RunMetrics::QueueState(QueueDisc* disc, Ptr<const QueueDiscItem>)
{
    m_queue << Simulator::Now().GetNanoSeconds() << ',' << Phase() << ',' << disc->GetNPackets()
            << ',' << disc->GetNBytes() << '\n';
}

void RunMetrics::Transmit(Ptr<const Packet> packet)
{
    NS_ABORT_MSG_IF(m_flows.empty(), "No flow mappings registered: copy updated s-pie.cc together with run-metrics.cc/.h");
    uint32_t flow = 0;
    std::string group = "unknown";
    Ipv4Address source, destination;
    uint16_t sourcePort = 0, destinationPort = 0;
    uint8_t protocol = 0;
    // Parse a copy: never remove headers from the packet being simulated.
    auto copy = packet->Copy();
    PppHeader ppp;
    if (copy->GetSize() >= ppp.GetSerializedSize())
    {
        copy->RemoveHeader(ppp);
        if (ppp.GetProtocol() == 0x0021 && copy->GetSize() >= 20)
        {
            Ipv4Header ip;
            copy->RemoveHeader(ip);
            source = ip.GetSource();
            destination = ip.GetDestination();
            protocol = ip.GetProtocol();
            if (protocol == 6 && ip.GetFragmentOffset() == 0 && ip.IsLastFragment() &&
                copy->GetSize() >= 20)
            {
                TcpHeader tcp;
                copy->PeekHeader(tcp);
                sourcePort = tcp.GetSourcePort();
                destinationPort = tcp.GetDestinationPort();
                auto found = m_flows.find({source.Get(), destination.Get(), destinationPort});
                if (found != m_flows.end())
                {
                    flow = found->second.first;
                    group = found->second.second;
                }
            }
        }
    }
    // Kích thước khung PPP khi bắt đầu phát trên bottleneck chiều Router1 → Router2.
    m_link << Simulator::Now().GetNanoSeconds() << ',' << Phase() << ',' << packet->GetSize()
           << ',' << flow << ',' << group << ',' << source << ',' << destination
           << ',' << static_cast<unsigned>(protocol) << ',' << sourcePort << ',' << destinationPort
           << '\n';
}

void RunMetrics::RegisterFlow(Ipv4Address source, Ipv4Address destination,
                              uint16_t destinationPort, uint32_t flow, const std::string& group)
{
    auto inserted = m_flows.emplace(std::make_tuple(source.Get(), destination.Get(), destinationPort),
                                   std::make_pair(flow, group));
    NS_ABORT_MSG_IF(!inserted.second, "Duplicate flow endpoint mapping");
    const std::string prefix = "flow." + std::to_string(flow) + ".";
    RecordSetting(prefix + "source", std::to_string(source.Get()));
    RecordSetting(prefix + "destination", std::to_string(destination.Get()));
    RecordSetting(prefix + "destinationPort", std::to_string(destinationPort));
    RecordSetting(prefix + "group", group);
}

void RunMetrics::ObserveSender(Ptr<OnOffApplication> app, uint32_t flow)
{
    auto socket = app->GetSocket();
    NS_ABORT_MSG_IF(!socket, "TCP socket missing for flow " << flow);
    for (std::string metric : {"LastRTT", "RTT"})
    {
        Connect(socket, metric, MakeCallback(&RunMetrics::Rtt, this).Bind(flow, metric));
    }
    if (flow == 1)
    {
        TypeId::AttributeInformation ecn;
        socket->GetInstanceTypeId().LookupAttributeByName("UseEcn", &ecn);
        RecordSetting("tcp.UseEcnConfigured", ecn.initialValue->SerializeToString(ecn.checker));
        RecordAttributes(socket, "tcp", {"SegmentSize", "InitialCwnd", "SndBufSize", "RcvBufSize",
                                        "DelAckCount", "DelAckTimeout"});
    }
}

void RunMetrics::Rtt(uint32_t flow, std::string metric, Time, Time current)
{
    m_rtt << Simulator::Now().GetNanoSeconds() << ',' << Phase() << ',' << flow << ',' << metric
          << ',' << current.GetNanoSeconds() << '\n';
}

void RunMetrics::RecordSetting(const std::string& name, const std::string& value)
{
    m_config << CsvField(name) << ',' << CsvField(value) << '\n';
}

void RunMetrics::RecordAttributes(Ptr<Object> object, const std::string& prefix,
                                  const std::vector<std::string>& names)
{
    for (const auto& name : names)
    {
        StringValue value;
        object->GetAttribute(name, value);
        RecordSetting(prefix + "." + name, value.Get());
    }
}

void RunMetrics::Finish(Ptr<QueueDisc> forward)
{
    NS_ABORT_MSG_IF(m_forwardDrops != forward->GetStats().nTotalDroppedPackets,
                    "Drop CSV disagrees with forward QueueDisc stats");
    QueueState(PeekPointer(forward), nullptr); // Đóng khoảng cuối để tích phân Q(t).
    for (auto* stream : {&m_queue, &m_drops, &m_rtt, &m_link, &m_config})
    {
        stream->flush();
    }
}


