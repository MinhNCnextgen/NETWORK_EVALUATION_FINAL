/*
 * Copyright (c) 2016 NITK Surathkal
 *
 * SPDX-License-Identifier: GPL-2.0-only
 *
 * Authors: Shravya Ks <shravya.ks0@gmail.com>
 *          Smriti Murali <m.smriti.95@gmail.com>
 *          Mohit P. Tahiliani <tahiliani@nitk.edu.in>
 */

/*
 * PORT NOTE: This code was ported from ns-2.36rc1 (queue/pie.cc).
 * Most of the comments are also ported from the same.
 */

#include "spie-queue-disc.h"

#include "ns3/abort.h"
#include "ns3/ipv4-queue-disc-item.h"
#include "ns3/tcp-header.h"
#include "ns3/udp-header.h"

#include <algorithm>
#include "ns3/double.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/enum.h"
#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/uinteger.h"

namespace ns3
{

NS_LOG_COMPONENT_DEFINE("SpieQueueDisc");

NS_OBJECT_ENSURE_REGISTERED(SpieQueueDisc);

TypeId
SpieQueueDisc::GetTypeId()
{
    static TypeId tid =
        TypeId("ns3::SpieQueueDisc")
            .SetParent<QueueDisc>()
            .SetGroupName("TrafficControl")
            .AddConstructor<SpieQueueDisc>()
            // Các thuộc tính Sketch được cấu hình trước khi khởi tạo QueueDisc.
            .AddAttribute("SketchEnabled", "Enable flow discrimination",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          BooleanValue(true), MakeBooleanAccessor(&SpieQueueDisc::m_sketchEnabled),
                          MakeBooleanChecker())
            .AddAttribute("SketchRows", "Number of independent hash rows",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          UintegerValue(4), MakeUintegerAccessor(&SpieQueueDisc::m_rows),
                          MakeUintegerChecker<uint32_t>(1))
            .AddAttribute("SketchWidth", "Counters per row",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          UintegerValue(1024), MakeUintegerAccessor(&SpieQueueDisc::m_width),
                          MakeUintegerChecker<uint32_t>(1))
            .AddAttribute("HashSeed", "Base seed for row hashes",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          UintegerValue(1), MakeUintegerAccessor(&SpieQueueDisc::m_hashSeed),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("SketchWindow", "Hard reset interval",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          TimeValue(MilliSeconds(500)), MakeTimeAccessor(&SpieQueueDisc::m_window),
                          MakeTimeChecker(TimeStep(1)))
            .AddAttribute("DelayDivisor", "Enter Sketch at reference delay divided by this value",
                          TypeId::ATTR_GET | TypeId::ATTR_CONSTRUCT,
                          DoubleValue(3), MakeDoubleAccessor(&SpieQueueDisc::m_delayDivisor),
                          MakeDoubleChecker<double>(1))
            .AddAttribute("MeanPktSize",
                          "Average of packet size",
                          UintegerValue(1000),
                          MakeUintegerAccessor(&SpieQueueDisc::m_meanPktSize),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("A",
                          "Value of alpha",
                          DoubleValue(0.125),
                          MakeDoubleAccessor(&SpieQueueDisc::m_a),
                          MakeDoubleChecker<double>())
            .AddAttribute("B",
                          "Value of beta",
                          DoubleValue(1.25),
                          MakeDoubleAccessor(&SpieQueueDisc::m_b),
                          MakeDoubleChecker<double>())
            .AddAttribute("Tupdate",
                          "Time period to calculate drop probability",
                          TimeValue(MilliSeconds(15)),
                          MakeTimeAccessor(&SpieQueueDisc::m_tUpdate),
                          MakeTimeChecker())
            .AddAttribute("Supdate",
                          "Start time of the update timer",
                          TimeValue(Seconds(0)),
                          MakeTimeAccessor(&SpieQueueDisc::m_sUpdate),
                          MakeTimeChecker())
            .AddAttribute("MaxSize",
                          "The maximum number of packets accepted by this queue disc",
                          QueueSizeValue(QueueSize("25p")),
                          MakeQueueSizeAccessor(&QueueDisc::SetMaxSize, &QueueDisc::GetMaxSize),
                          MakeQueueSizeChecker())
            .AddAttribute("DequeueThreshold",
                          "Minimum queue size in bytes before dequeue rate is measured",
                          UintegerValue(16384),
                          MakeUintegerAccessor(&SpieQueueDisc::m_dqThreshold),
                          MakeUintegerChecker<uint32_t>())
            .AddAttribute("QueueDelayReference",
                          "Desired queue delay",
                          TimeValue(MilliSeconds(15)),
                          MakeTimeAccessor(&SpieQueueDisc::m_qDelayRef),
                          MakeTimeChecker())
            .AddAttribute("MaxBurstAllowance",
                          "Current max burst allowance before random drop",
                          TimeValue(MilliSeconds(150)),
                          MakeTimeAccessor(&SpieQueueDisc::m_maxBurst),
                          MakeTimeChecker())
            .AddAttribute("UseDequeueRateEstimator",
                          "Enable/Disable usage of Dequeue Rate Estimator",
                          BooleanValue(false),
                          MakeBooleanAccessor(&SpieQueueDisc::m_useDqRateEstimator),
                          MakeBooleanChecker())
            .AddAttribute("UseCapDropAdjustment",
                          "Enable/Disable Cap Drop Adjustment feature mentioned in RFC 8033",
                          BooleanValue(true),
                          MakeBooleanAccessor(&SpieQueueDisc::m_isCapDropAdjustment),
                          MakeBooleanChecker())
            .AddAttribute("UseEcn",
                          "True to use ECN (packets are marked instead of being dropped)",
                          BooleanValue(false),
                          MakeBooleanAccessor(&SpieQueueDisc::m_useEcn),
                          MakeBooleanChecker())
            .AddAttribute("MarkEcnThreshold",
                          "ECN marking threshold (RFC 8033 suggests 0.1 (i.e., 10%) default)",
                          DoubleValue(0.1),
                          MakeDoubleAccessor(&SpieQueueDisc::m_markEcnTh),
                          MakeDoubleChecker<double>(0, 1))
            .AddAttribute("UseDerandomization",
                          "Enable/Disable Derandomization feature mentioned in RFC 8033",
                          BooleanValue(false),
                          MakeBooleanAccessor(&SpieQueueDisc::m_useDerandomization),
                          MakeBooleanChecker())
            .AddAttribute("ActiveThreshold",
                          "Threshold for activating PIE (disabled by default)",
                          TimeValue(Time::Max()),
                          MakeTimeAccessor(&SpieQueueDisc::m_activeThreshold),
                          MakeTimeChecker())
            .AddAttribute("CeThreshold",
                          "The FqPie CE threshold for marking packets",
                          TimeValue(Time::Max()),
                          MakeTimeAccessor(&SpieQueueDisc::m_ceThreshold),
                          MakeTimeChecker())
            .AddAttribute("UseL4s",
                          "True to use L4S (only ECT1 packets are marked at CE threshold)",
                          BooleanValue(false),
                          MakeBooleanAccessor(&SpieQueueDisc::m_useL4s),
                          MakeBooleanChecker());

    return tid;
}

SpieQueueDisc::SpieQueueDisc()
    : QueueDisc(QueueDiscSizePolicy::SINGLE_INTERNAL_QUEUE)
{
    NS_LOG_FUNCTION(this);
    m_uv = CreateObject<UniformRandomVariable>();
    m_rtrsEvent = Simulator::Schedule(m_sUpdate, &SpieQueueDisc::CalculateP, this);
}

SpieQueueDisc::~SpieQueueDisc()
{
    NS_LOG_FUNCTION(this);
}

void
SpieQueueDisc::DoDispose()
{
    NS_LOG_FUNCTION(this);
    m_uv = nullptr;
    m_resetEvent.Cancel();
    m_rtrsEvent.Cancel();
    QueueDisc::DoDispose();
}

Time
SpieQueueDisc::GetQueueDelay()
{
    return m_qDelay;
}

int64_t
SpieQueueDisc::AssignStreams(int64_t stream)
{
    NS_LOG_FUNCTION(this << stream);
    m_uv->SetStream(stream);
    return 1;
}

bool
SpieQueueDisc::DoEnqueue(Ptr<QueueDiscItem> item)
{
    NS_LOG_FUNCTION(this << item);

    QueueSize nQueued = GetCurrentSize();
    // If L4S is enabled, then check if the packet is ECT1, and if it is then set isEct true
    bool isEct1 = false;
    if (item && m_useL4s)
    {
        uint8_t tosByte = 0;
        if (item->GetUint8Value(QueueItem::IP_DSFIELD, tosByte) &&
            (((tosByte & 0x3) == 1) || (tosByte & 0x3) == 3))
        {
            if ((tosByte & 0x3) == 1)
            {
                NS_LOG_DEBUG("Enqueueing ECT1 packet " << static_cast<uint16_t>(tosByte & 0x3));
            }
            else
            {
                NS_LOG_DEBUG("Enqueueing CE packet " << static_cast<uint16_t>(tosByte & 0x3));
            }
            isEct1 = true;
        }
    }

    if (nQueued + item > GetMaxSize())
    {
        // Drops due to queue limit: reactive
        DropBeforeEnqueue(item, FORCED_DROP);
        m_accuProb = 0;
        return false;
    }
    // Kiểm tra đầy trước. Nếu chưa đủ dữ liệu, để PIE xử lý như bình thường.
    std::optional<FlowKey> key;
    if (m_sketchEnabled)
    {
        key = ReadFlowKey(item);
    }
    const bool useSketch = key && m_accepted > 0 && (!m_useDqRateEstimator || m_avgDqRate > 0) &&
                           m_qDelay.GetSeconds() >= m_qDelayRef.GetSeconds() / m_delayDivisor;
    if (useSketch && AboveThreshold(*key))
    {
        DropBeforeEnqueue(item, "Sketch large-flow drop");
        return false;
    }
    // Trong nhánh Sketch, gói bằng hoặc dưới ngưỡng được nhận, không rút thăm PIE nữa.
    // isEct1 will be true only if L4S enabled as well as the packet is ECT1.
    // If L4S is enabled and packet is ECT1 then directly enqueue the packet.
    if (!useSketch && (m_activeThreshold == Time::Max() || m_active) && !isEct1 &&
             DropEarly(item, nQueued.GetValue()))
    {
        if (!m_useEcn || m_dropProb >= m_markEcnTh || !Mark(item, UNFORCED_MARK))
        {
            // Early probability drop: proactive
            DropBeforeEnqueue(item, UNFORCED_DROP);
            m_accuProb = 0;
            return false;
        }
    }

    // No drop
    bool retval = GetInternalQueue(0)->Enqueue(item);

    if (retval && key)
    {
        RecordAccepted(*key);
    }

    // If the queue is over a certain threshold, Turn ON PIE
    if (m_activeThreshold != Time::Max() && !m_active && m_qDelay >= m_activeThreshold)
    {
        m_active = true;
        m_qDelayOld = Seconds(0);
        m_dropProb = 0;
        m_inMeasurement = true;
        m_dqCount = 0;
        m_avgDqRate = 0;
        m_burstAllowance = m_maxBurst;
        m_accuProb = 0;
        m_dqStart = Now();
    }

    // If queue has been Idle for a while, Turn OFF PIE
    // Reset Counters when accessing the queue after some idle period if PIE was active before
    if (m_activeThreshold != Time::Max() && m_dropProb == 0 && m_qDelayOld.GetMilliSeconds() == 0 &&
        m_qDelay.GetMilliSeconds() == 0)
    {
        m_active = false;
        m_inMeasurement = false;
    }

    // If Queue::Enqueue fails, QueueDisc::DropBeforeEnqueue is called by the
    // internal queue because QueueDisc::AddInternalQueue sets the trace callback

    NS_LOG_LOGIC("\t bytesInQueue  " << GetInternalQueue(0)->GetNBytes());
    NS_LOG_LOGIC("\t packetsInQueue  " << GetInternalQueue(0)->GetNPackets());

    return retval;
}

void
SpieQueueDisc::InitializeParams()
{
    if (m_sketchEnabled)
    {
        NS_ABORT_MSG_IF(m_width > m_counters.max_size() / m_rows, "Sketch too large");
        m_counters.resize(static_cast<size_t>(m_rows) * m_width);
        ResetWindow();
    }
    // Initially queue is empty so variables are initialize to zero except m_dqCount
    m_inMeasurement = false;
    m_dqCount = DQCOUNT_INVALID;
    m_dropProb = 0;
    m_avgDqRate = 0.0;
    m_dqStart = Seconds(0);
    m_burstState = NO_BURST;
    m_qDelayOld = Seconds(0);
    m_accuProb = 0.0;
    m_active = false;
}

// Trên dumbbell, ứng dụng dùng IPv4/TCP. UDP cũng có cặp cổng rõ ràng.
// Gói không hỗ trợ hoặc phân mảnh dùng PIE, không trộn vào một khóa giả.
std::optional<SpieQueueDisc::FlowKey>
SpieQueueDisc::ReadFlowKey(Ptr<QueueDiscItem> item) const
{
    auto ip = DynamicCast<Ipv4QueueDiscItem>(item);
    if (!ip)
    {
        return std::nullopt;
    }
    const auto& header = ip->GetHeader();
    if (!header.IsLastFragment() || header.GetFragmentOffset() != 0)
    {
        return std::nullopt;
    }
    FlowKey key{header.GetSource().Get(), header.GetDestination().Get(), header.GetProtocol(), 0, 0};
    if (header.GetProtocol() == 6 && item->GetPacket()->GetSize() >= 20)
    {
        TcpHeader tcp;
        item->GetPacket()->PeekHeader(tcp);
        key[3] = tcp.GetSourcePort();
        key[4] = tcp.GetDestinationPort();
        return key;
    }
    if (header.GetProtocol() == 17 && item->GetPacket()->GetSize() >= 8)
    {
        UdpHeader udp;
        item->GetPacket()->PeekHeader(udp);
        key[3] = udp.GetSourcePort();
        key[4] = udp.GetDestinationPort();
        return key;
    }
    return std::nullopt;
}

size_t
SpieQueueDisc::Bucket(const FlowKey& key, uint32_t row) const
{
    // Trộn SplitMix64 theo từng trường, seed riêng cho mỗi hàng.
    // Phép tràn unsigned là một phần của hàm băm; không tiêu thụ RNG của PIE.
    uint64_t hash = (static_cast<uint64_t>(m_hashSeed) << 32) | row;
    for (uint32_t field : key)
    {
        hash += field + UINT64_C(0x9e3779b97f4a7c15);
        hash = (hash ^ (hash >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
        hash = (hash ^ (hash >> 27)) * UINT64_C(0x94d049bb133111eb);
        hash ^= hash >> 31;
    }
    return static_cast<size_t>(row) * m_width + hash % m_width;
}

uint64_t
SpieQueueDisc::Estimate(const FlowKey& key) const
{
    uint64_t estimate = std::numeric_limits<uint64_t>::max();
    for (uint32_t row = 0; row < m_rows; ++row)
    {
        estimate = std::min(estimate, m_counters[Bucket(key, row)]);
    }
    return estimate;
}

bool
SpieQueueDisc::AboveThreshold(const FlowKey& key) const
{
    // Eq. 8–9: G_i = c_i/M; ngưỡng = sum(c_i * G_i) / sum(c_i).
    // Khử M chung ở hai vế: c_k * sum(c_i) > sum(c_i²).
    // Phải lấy tổng các ước lượng thực tế: va chạm CMS có thể làm tổng vượt M.
    long double sum = 0;
    long double sumSquares = 0;
    for (const auto& activeKey : m_keys)
    {
        const long double count = Estimate(activeKey);
        sum += count;
        sumSquares += count * count;
    }
    return Estimate(key) * sum > sumSquares;
}

void
SpieQueueDisc::RecordAccepted(const FlowKey& key)
{
    for (uint32_t row = 0; row < m_rows; ++row)
    {
        ++m_counters[Bucket(key, row)];
    }
    ++m_accepted; // Chỉ tăng một lần cho cả gói, không tăng theo số hàng.
    m_keys.insert(key);
}

void
SpieQueueDisc::ResetWindow()
{
    std::fill(m_counters.begin(), m_counters.end(), 0);
    m_keys.clear();
    m_accepted = 0;
    m_resetEvent = Simulator::Schedule(m_window, &SpieQueueDisc::ResetWindow, this);
}

bool
SpieQueueDisc::DropEarly(Ptr<QueueDiscItem> item, uint32_t qSize)
{
    NS_LOG_FUNCTION(this << item << qSize);
    if (m_burstAllowance.GetSeconds() > 0)
    {
        // If there is still burst_allowance left, skip random early drop.
        return false;
    }

    if (m_burstState == NO_BURST)
    {
        m_burstState = IN_BURST_PROTECTING;
        m_burstAllowance = m_maxBurst;
    }

    double p = m_dropProb;

    uint32_t packetSize = item->GetSize();

    if (GetMaxSize().GetUnit() == QueueSizeUnit::BYTES)
    {
        p = p * packetSize / m_meanPktSize;
    }

    // Safeguard PIE to be work conserving (Section 4.1 of RFC 8033)
    if ((m_qDelayOld.GetSeconds() < (0.5 * m_qDelayRef.GetSeconds()) && m_dropProb < 0.2) ||
        (GetMaxSize().GetUnit() == QueueSizeUnit::BYTES && qSize <= 2 * m_meanPktSize) ||
        (GetMaxSize().GetUnit() == QueueSizeUnit::PACKETS && qSize <= 2))
    {
        return false;
    }

    if (m_useDerandomization)
    {
        if (m_dropProb == 0)
        {
            m_accuProb = 0;
        }
        m_accuProb += m_dropProb;
        if (m_accuProb < 0.85)
        {
            return false;
        }
        else if (m_accuProb >= 8.5)
        {
            return true;
        }
    }

    double u = m_uv->GetValue();
    return u <= p;
}

void
SpieQueueDisc::CalculateP()
{
    NS_LOG_FUNCTION(this);
    Time qDelay;
    double p = 0.0;
    bool missingInitFlag = false;

    if (m_useDqRateEstimator)
    {
        if (m_avgDqRate > 0)
        {
            qDelay = Seconds(GetInternalQueue(0)->GetNBytes() / m_avgDqRate);
        }
        else
        {
            qDelay = Seconds(0);
            missingInitFlag = true;
        }
        m_qDelay = qDelay;
    }
    else
    {
        qDelay = m_qDelay;
    }
    NS_LOG_DEBUG("Queue delay while calculating probability: " << qDelay.GetMilliSeconds() << "ms");

    if (m_burstAllowance.GetSeconds() > 0)
    {
        m_dropProb = 0;
    }
    else
    {
        p = m_a * (qDelay.GetSeconds() - m_qDelayRef.GetSeconds()) +
            m_b * (qDelay.GetSeconds() - m_qDelayOld.GetSeconds());
        if (m_dropProb < 0.000001)
        {
            p /= 2048;
        }
        else if (m_dropProb < 0.00001)
        {
            p /= 512;
        }
        else if (m_dropProb < 0.0001)
        {
            p /= 128;
        }
        else if (m_dropProb < 0.001)
        {
            p /= 32;
        }
        else if (m_dropProb < 0.01)
        {
            p /= 8;
        }
        else if (m_dropProb < 0.1)
        {
            p /= 2;
        }
        else
        {
            // The pseudocode in Section 4.2 of RFC 8033 suggests to use this for
            // assignment of p, but this assignment causes build failure on Mac OS
            // p = p;
        }

        // Cap Drop Adjustment (Section 5.5 of RFC 8033)
        if (m_isCapDropAdjustment && (m_dropProb >= 0.1) && (p > 0.02))
        {
            p = 0.02;
        }
    }

    p += m_dropProb;

    // For non-linear drop in prob
    // Decay the drop probability exponentially (Section 4.2 of RFC 8033)
    if (qDelay.GetSeconds() == 0 && m_qDelayOld.GetSeconds() == 0)
    {
        p *= 0.98;
    }

    // bound the drop probability (Section 4.2 of RFC 8033)
    if (p < 0)
    {
        m_dropProb = 0;
    }
    else if (p > 1)
    {
        m_dropProb = 1;
    }
    else
    {
        m_dropProb = p;
    }

    // Section 4.4 #2
    if (m_burstAllowance < m_tUpdate)
    {
        m_burstAllowance = Seconds(0);
    }
    else
    {
        m_burstAllowance -= m_tUpdate;
    }

    auto burstResetLimit = static_cast<uint32_t>(SPIE_BURST_RESET_TIMEOUT / m_tUpdate.GetSeconds());
    if ((qDelay.GetSeconds() < 0.5 * m_qDelayRef.GetSeconds()) &&
        (m_qDelayOld.GetSeconds() < (0.5 * m_qDelayRef.GetSeconds())) && (m_dropProb == 0) &&
        !missingInitFlag)
    {
        m_dqCount = DQCOUNT_INVALID;
        m_avgDqRate = 0.0;
    }
    if ((qDelay.GetSeconds() < 0.5 * m_qDelayRef.GetSeconds()) &&
        (m_qDelayOld.GetSeconds() < (0.5 * m_qDelayRef.GetSeconds())) && (m_dropProb == 0) &&
        (m_burstAllowance.GetSeconds() == 0))
    {
        if (m_burstState == IN_BURST_PROTECTING)
        {
            m_burstState = IN_BURST;
            m_burstReset = 0;
        }
        else if (m_burstState == IN_BURST)
        {
            m_burstReset++;
            if (m_burstReset > burstResetLimit)
            {
                m_burstReset = 0;
                m_burstState = NO_BURST;
            }
        }
    }
    else if (m_burstState == IN_BURST)
    {
        m_burstReset = 0;
    }

    m_qDelayOld = qDelay;
    m_rtrsEvent = Simulator::Schedule(m_tUpdate, &SpieQueueDisc::CalculateP, this);
}

Ptr<QueueDiscItem>
SpieQueueDisc::DoDequeue()
{
    NS_LOG_FUNCTION(this);

    if (GetInternalQueue(0)->IsEmpty())
    {
        NS_LOG_LOGIC("Queue empty");
        return nullptr;
    }

    Ptr<QueueDiscItem> item = GetInternalQueue(0)->Dequeue();
    NS_ASSERT_MSG(item, "Dequeue null, but internal queue not empty");

    // If L4S is enabled and packet is ECT1, then check if delay is greater
    // than CE threshold and if it is then mark the packet,
    // skip PIE steps, and return the item.
    if (m_useL4s)
    {
        uint8_t tosByte = 0;
        if (item->GetUint8Value(QueueItem::IP_DSFIELD, tosByte) &&
            (((tosByte & 0x3) == 1) || (tosByte & 0x3) == 3))
        {
            if ((tosByte & 0x3) == 1)
            {
                NS_LOG_DEBUG("ECT1 packet " << static_cast<uint16_t>(tosByte & 0x3));
            }
            else
            {
                NS_LOG_DEBUG("CE packet " << static_cast<uint16_t>(tosByte & 0x3));
            }
            if ((Now() - item->GetTimeStamp() > m_ceThreshold) &&
                Mark(item, CE_THRESHOLD_EXCEEDED_MARK))
            {
                NS_LOG_LOGIC("Marking due to CeThreshold " << m_ceThreshold.GetSeconds());
            }
            return item;
        }
    }

    // if not in a measurement cycle and the queue has built up to dq_threshold,
    // start the measurement cycle
    if (m_useDqRateEstimator)
    {
        if ((GetInternalQueue(0)->GetNBytes() >= m_dqThreshold) && (!m_inMeasurement))
        {
            m_dqStart = Now();
            m_dqCount = 0;
            m_inMeasurement = true;
        }

        if (m_inMeasurement)
        {
            m_dqCount += item->GetSize();

            // done with a measurement cycle
            if (m_dqCount >= m_dqThreshold)
            {
                Time dqTime = Now() - m_dqStart;
                if (dqTime.IsStrictlyPositive())
                {
                    if (m_avgDqRate == 0)
                    {
                        m_avgDqRate = m_dqCount / dqTime.GetSeconds();
                    }
                    else
                    {
                        m_avgDqRate =
                            (0.5 * m_avgDqRate) + (0.5 * (m_dqCount / dqTime.GetSeconds()));
                    }
                }
                NS_LOG_DEBUG("Average Dequeue Rate after Dequeue: " << m_avgDqRate);

                // restart a measurement cycle if there is enough data
                if (GetInternalQueue(0)->GetNBytes() > m_dqThreshold)
                {
                    m_dqStart = Now();
                    m_dqCount = 0;
                    m_inMeasurement = true;
                }
                else
                {
                    m_dqCount = 0;
                    m_inMeasurement = false;
                }
            }
        }
    }
    else
    {
        m_qDelay = Now() - item->GetTimeStamp();

        if (GetInternalQueue(0)->GetNBytes() == 0)
        {
            m_qDelay = Seconds(0);
        }
    }
    return item;
}

bool
SpieQueueDisc::CheckConfig()
{
    NS_LOG_FUNCTION(this);
    if (GetNQueueDiscClasses() > 0)
    {
        NS_LOG_ERROR("SpieQueueDisc cannot have classes");
        return false;
    }

    if (GetNPacketFilters() > 0)
    {
        NS_LOG_ERROR("SpieQueueDisc cannot have packet filters");
        return false;
    }

    if (GetNInternalQueues() == 0)
    {
        // add  a DropTail queue
        AddInternalQueue(
            CreateObjectWithAttributes<DropTailQueue<QueueDiscItem>>("MaxSize",
                                                                     QueueSizeValue(GetMaxSize())));
    }

    if (GetNInternalQueues() != 1)
    {
        NS_LOG_ERROR("SpieQueueDisc needs 1 internal queue");
        return false;
    }

    return true;
}

} // namespace ns3
