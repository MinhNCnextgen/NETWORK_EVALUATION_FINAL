#!/usr/bin/env bash
# Ubuntu/WSL: bash scratch/s-pie/run-simulation.sh
# Cấu hình batch ở đầu file; mỗi job là một scenario/run/AQM.
set -euo pipefail

# ==================== CẤU HÌNH ====================
# Để trống: tự tìm gốc ns-3 khi script nằm trong scratch/s-pie.
NS3_ROOT=""
PYTHON="python3"

SCENARIOS=(1 2)
RNG_RUNS=(1 2 3)                # Ví dụ: (1 2 3 4 5 6 7 8 9 10)
MAX_PARALLEL=2                  # Số mô phỏng chạy đồng thời (Bash >= 4.3)
ALGORITHMS=(Spie Pie Red CoDel)
FLOWS=100                        # Số chẵn, 2..32000
DURATION=30                      # Giây nguyên, 1..86400 (chưa gồm 5s drain)
SMALL_RATE="1Mbps"
LARGE_RATE="50Mbps"
EQUAL_RATE="10Mbps"
ON_TIME="ns3::ExponentialRandomVariable[Mean=1]"
OFF_TIME="ns3::ExponentialRandomVariable[Mean=1]"
PAYLOAD=1000                     # Byte mỗi lần ứng dụng gửi; khác TCP MSS
ACCESS_RATE="100Mbps"
ACCESS_DELAY="5ms"
CORE_RATE="50Mbps"
CORE_DELAY="20ms"
LIMIT="50p"                      # Giới hạn qdisc chiều đi
RESULT_DIR="result"              # Thư mục trong gốc NS3_ROOT
WRITE_EVENTS=false               # true = ghi thêm trace enqueue/drop riêng mỗi AQM
RNG_SEED=1
OVERWRITE=false                 # true cho phép ghi đè CSV cùng seed/run

# Sketch: chỉ áp dụng cho Spie.
SKETCH_ENABLED=true
SKETCH_ROWS=4
SKETCH_WIDTH=1024
SKETCH_WINDOW="500ms"
HASH_SEED=1                      # Độc lập với RNG_RUN
DELAY_DIVISOR=3

# Bộ điều khiển: cùng bộ biến cho Pie và Spie.
PIE_A=0.125
PIE_B=1.25
PIE_QUEUE_DELAY_REFERENCE="5ms"
PIE_TUPDATE="30ms"
PIE_SUPDATE="0s"
PIE_DEQUEUE_THRESHOLD=10000
PIE_MAX_BURST_ALLOWANCE="100ms"
PIE_MEAN_PKT_SIZE=1000
PIE_USE_DEQUEUE_RATE_ESTIMATOR=true
PIE_USE_CAP_DROP_ADJUSTMENT=true
PIE_USE_DERANDOMIZATION=false
PIE_USE_ECN=false
PIE_MARK_ECN_THRESHOLD=0.1
# Trống = giữ Time::Max() của C++, tức vô hiệu ngưỡng tùy chọn.
PIE_ACTIVE_THRESHOLD=""
PIE_CE_THRESHOLD=""
PIE_USE_L4S=false

# RED (LinkBandwidth/LinkDelay tự lấy CORE_RATE/CORE_DELAY).
RED_MIN_TH=5
RED_MAX_TH=15
RED_QW=0.002
RED_LINTERM=50
RED_MEAN_PKT_SIZE=1000
RED_IDLE_PKT_SIZE=0
RED_WAIT=true
RED_GENTLE=true
RED_ARED=false
RED_ADAPT_MAX_P=false
RED_FENG_ADAPTIVE=false
RED_NLRED=false
RED_TARGET_DELAY="5ms"
RED_INTERVAL="500ms"
RED_TOP=0.5
RED_BOTTOM=0
RED_ALPHA=0.01
RED_BETA=0.9
RED_FENG_ALPHA=3
RED_FENG_BETA=2
RED_LAST_SET="0s"
RED_RTT="100ms"
RED_NS1_COMPAT=false
RED_USE_ECN=false
RED_USE_HARD_DROP=true

# CoDel.
CODEL_TARGET="5ms"
CODEL_INTERVAL="100ms"
CODEL_MIN_BYTES=1500
CODEL_USE_ECN=false
CODEL_USE_L4S=false
CODEL_CE_THRESHOLD=""           # Trống = Time::Max() của C++

# TCP, giá trị khởi đầu của chương trình trên ns-3.45.
TCP_SOCKET_TYPE="ns3::TcpNewReno"
TCP_RECOVERY_TYPE="ns3::TcpPrrRecovery"
TCP_SEGMENT_SIZE=1000
TCP_INITIAL_CWND=10
TCP_SND_BUF_SIZE=131072
TCP_RCV_BUF_SIZE=131072
TCP_DEL_ACK_COUNT=2
TCP_DEL_ACK_TIMEOUT="200ms"
TCP_USE_ECN="Off"               # Enum; bật ECN cần cấu hình cả TCP và AQM

# ==================== THỰC THI ====================
# Các giá trị chưa có tùy chọn C++ (muốn đổi phải sửa C++):
# 2 router; chia nhóm 50/50; drain 5s; lấy goodput mỗi 1s;
# jitter start [0,0.1]s; reverse FIFO 50p; access FIFO 100p;
# device queue 1p; port 5000; EWMA dequeue 0.5; quy tắc Sketch dấu >.

usage() {
    cat <<'HELP'
Usage: bash scratch/s-pie/run-simulation.sh [options]
  --runs N          Number of runs per scenario, starting at 1 by default
  --start-run N     First run ID (default: 1); uses configured count if --runs omitted
  --parallel N      Maximum concurrent simulation jobs
  --scenario 1|2|both
  --result-dir DIR  Output root (default: result)
  --dry-run         Print commands without building or running
  -h, --help        Show this help
Examples:
  bash scratch/s-pie/run-simulation.sh --runs 10 --parallel 4
  bash scratch/s-pie/run-simulation.sh --scenario 1 --start-run 4 --runs 5
HELP
}
DRY_RUN=false
RUN_COUNT=""
START_RUN=1
CUSTOM_RANGE=false
while (( $# )); do
    if [[ "$1" == --*=* ]]; then set -- "${1%%=*}" "${1#*=}" "${@:2}"; fi
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --runs|--start-run|--parallel|--scenario|--result-dir)
            option="$1"
            if (( $# < 2 )) || [[ -z "$2" || "$2" == --* ]]; then
                echo "Thiếu giá trị cho $option" >&2; exit 1
            fi
            case "$option" in
                --runs) RUN_COUNT="$2"; CUSTOM_RANGE=true ;;
                --start-run) START_RUN="$2"; CUSTOM_RANGE=true ;;
                --parallel) MAX_PARALLEL="$2" ;;
                --scenario)
                    case "$2" in
                        1|2) SCENARIOS=("$2") ;;
                        both) SCENARIOS=(1 2) ;;
                        *) echo '--scenario phải là 1, 2 hoặc both.' >&2; exit 1 ;;
                    esac ;;
                --result-dir) RESULT_DIR="$2" ;;
            esac
            shift 2 ;;
        *) echo "Tùy chọn không hợp lệ: $1" >&2; usage >&2; exit 1 ;;
    esac
done
if [[ "$CUSTOM_RANGE" == true ]]; then
    RUN_COUNT="${RUN_COUNT:-${#RNG_RUNS[@]}}"
    for number in "$RUN_COUNT" "$START_RUN"; do
        if [[ ! "$number" =~ ^[1-9][0-9]{0,8}$ ]]; then
            echo '--runs và --start-run phải là số nguyên dương (tối đa 9 chữ số).' >&2; exit 1
        fi
    done
    RNG_RUNS=()
    for ((offset=0; offset<RUN_COUNT; offset++)); do RNG_RUNS+=("$((START_RUN + offset))"); done
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$NS3_ROOT" ]]; then
    NS3_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
fi
cd -- "$NS3_ROOT"
if [[ ! -f ns3 ]]; then
    printf 'Không thấy tệp ns3 tại %s. Hãy chỉnh NS3_ROOT hoặc chép s-pie vào scratch/.\n' "$NS3_ROOT" >&2
    exit 1
fi
if (( ${#ALGORITHMS[@]} == 0 || ${#SCENARIOS[@]} == 0 || ${#RNG_RUNS[@]} == 0 )); then echo 'Danh sách job không được rỗng.' >&2; exit 1; fi
if [[ ! "$MAX_PARALLEL" =~ ^[1-9][0-9]*$ ]]; then echo 'MAX_PARALLEL phải là số nguyên dương.' >&2; exit 1; fi
declare -A planned=()
for scenario in "${SCENARIOS[@]}"; do
    [[ "$scenario" == 1 || "$scenario" == 2 ]] || { echo 'Scenario phải là 1 hoặc 2.' >&2; exit 1; }
    for run in "${RNG_RUNS[@]}"; do
        [[ "$run" =~ ^[1-9][0-9]*$ ]] || { echo 'Run phải là số nguyên dương.' >&2; exit 1; }
        for aqm in "${ALGORITHMS[@]}"; do
            job="$scenario/$run/$aqm"
            [[ -z "${planned[$job]:-}" ]] || { echo "Job bị lặp: $job" >&2; exit 1; }
            planned[$job]=1
            prefix="$RESULT_DIR/scenario_${scenario}_run_${run}/$aqm/s${scenario}-${aqm}-seed${RNG_SEED}-r${run}"
            if [[ "$OVERWRITE" != true ]] && compgen -G "${prefix}*.csv" >/dev/null; then
                echo "Đã có kết quả: $prefix. Chọn run mới hoặc đặt OVERWRITE=true." >&2
                exit 1
            fi
        done
    done
done
for AQM in "${ALGORITHMS[@]}"; do
    case "$AQM" in Spie|Pie|Red|CoDel) ;; *) echo 'Thuật toán phải là Spie, Pie, Red hoặc CoDel.' >&2; exit 1;; esac
done
if [[ "$DRY_RUN" == false ]]; then
    mkdir -p -- "$RESULT_DIR"
    "$PYTHON" ns3 configure
    "$PYTHON" ns3 build s-pie
fi

add() { args+=("--$1=$2"); }
attr() { [[ -z "$3" ]] || add "ns3::$1::$2" "$3"; }
run_one() (
SCENARIO="$1"
RNG_RUN="$2"
AQM="$3"
ALGORITHM_DIR="$RESULT_DIR/scenario_${SCENARIO}_run_${RNG_RUN}/$AQM"
OUTPUT="$ALGORITHM_DIR/s${SCENARIO}-${AQM}-seed${RNG_SEED}-r${RNG_RUN}.csv"
EVENTS=""
if [[ "$WRITE_EVENTS" == true ]]; then EVENTS="${OUTPUT%.csv}-events.csv"; fi
args=()
add scenario "$SCENARIO"; add aqm "$AQM"; add flows "$FLOWS"
add duration "$DURATION"; add payload "$PAYLOAD"
add smallRate "$SMALL_RATE"; add largeRate "$LARGE_RATE"; add equalRate "$EQUAL_RATE"
add onTime "$ON_TIME"; add offTime "$OFF_TIME"
add accessRate "$ACCESS_RATE"; add accessDelay "$ACCESS_DELAY"
add coreRate "$CORE_RATE"; add coreDelay "$CORE_DELAY"
add limit "$LIMIT"; add output "$OUTPUT"
if [[ -n "$EVENTS" ]]; then add events "$EVENTS"; fi
add RngSeed "$RNG_SEED"; add RngRun "$RNG_RUN"

if [[ "$AQM" == Spie ]]; then
    attr SpieQueueDisc SketchEnabled "$SKETCH_ENABLED"
    attr SpieQueueDisc SketchRows "$SKETCH_ROWS"
    attr SpieQueueDisc SketchWidth "$SKETCH_WIDTH"
    attr SpieQueueDisc SketchWindow "$SKETCH_WINDOW"
    attr SpieQueueDisc HashSeed "$HASH_SEED"
    attr SpieQueueDisc DelayDivisor "$DELAY_DIVISOR"
fi
if [[ "$AQM" == Spie || "$AQM" == Pie ]]; then
    cls="${AQM}QueueDisc"
    attr "$cls" A "$PIE_A"; attr "$cls" B "$PIE_B"
    attr "$cls" QueueDelayReference "$PIE_QUEUE_DELAY_REFERENCE"
    attr "$cls" Tupdate "$PIE_TUPDATE"; attr "$cls" Supdate "$PIE_SUPDATE"
    attr "$cls" DequeueThreshold "$PIE_DEQUEUE_THRESHOLD"
    attr "$cls" MaxBurstAllowance "$PIE_MAX_BURST_ALLOWANCE"
    attr "$cls" MeanPktSize "$PIE_MEAN_PKT_SIZE"
    attr "$cls" UseDequeueRateEstimator "$PIE_USE_DEQUEUE_RATE_ESTIMATOR"
    attr "$cls" UseCapDropAdjustment "$PIE_USE_CAP_DROP_ADJUSTMENT"
    attr "$cls" UseDerandomization "$PIE_USE_DERANDOMIZATION"
    attr "$cls" UseEcn "$PIE_USE_ECN"
    attr "$cls" MarkEcnThreshold "$PIE_MARK_ECN_THRESHOLD"
    attr "$cls" ActiveThreshold "$PIE_ACTIVE_THRESHOLD"
    attr "$cls" CeThreshold "$PIE_CE_THRESHOLD"
    attr "$cls" UseL4s "$PIE_USE_L4S"
fi
if [[ "$AQM" == Red ]]; then
    for pair in 'MinTh RED_MIN_TH' 'MaxTh RED_MAX_TH' 'QW RED_QW' 'LInterm RED_LINTERM' \
        'MeanPktSize RED_MEAN_PKT_SIZE' 'IdlePktSize RED_IDLE_PKT_SIZE' 'Wait RED_WAIT' \
        'Gentle RED_GENTLE' 'ARED RED_ARED' 'AdaptMaxP RED_ADAPT_MAX_P' \
        'FengAdaptive RED_FENG_ADAPTIVE' 'NLRED RED_NLRED' 'TargetDelay RED_TARGET_DELAY' \
        'Interval RED_INTERVAL' 'Top RED_TOP' 'Bottom RED_BOTTOM' 'Alpha RED_ALPHA' \
        'Beta RED_BETA' 'FengAlpha RED_FENG_ALPHA' 'FengBeta RED_FENG_BETA' \
        'LastSet RED_LAST_SET' 'Rtt RED_RTT' 'Ns1Compat RED_NS1_COMPAT' \
        'UseEcn RED_USE_ECN' 'UseHardDrop RED_USE_HARD_DROP'; do
        read -r key var <<< "$pair"
        attr RedQueueDisc "$key" "${!var}"
    done
fi
if [[ "$AQM" == CoDel ]]; then
    attr CoDelQueueDisc Target "$CODEL_TARGET"
    attr CoDelQueueDisc Interval "$CODEL_INTERVAL"
    attr CoDelQueueDisc MinBytes "$CODEL_MIN_BYTES"
    attr CoDelQueueDisc UseEcn "$CODEL_USE_ECN"
    attr CoDelQueueDisc UseL4s "$CODEL_USE_L4S"
    attr CoDelQueueDisc CeThreshold "$CODEL_CE_THRESHOLD"
fi
attr TcpL4Protocol SocketType "$TCP_SOCKET_TYPE"
attr TcpL4Protocol RecoveryType "$TCP_RECOVERY_TYPE"
attr TcpSocket SegmentSize "$TCP_SEGMENT_SIZE"
attr TcpSocket InitialCwnd "$TCP_INITIAL_CWND"
attr TcpSocket SndBufSize "$TCP_SND_BUF_SIZE"
attr TcpSocket RcvBufSize "$TCP_RCV_BUF_SIZE"
attr TcpSocket DelAckCount "$TCP_DEL_ACK_COUNT"
attr TcpSocket DelAckTimeout "$TCP_DEL_ACK_TIMEOUT"
attr TcpSocketBase UseEcn "$TCP_USE_ECN"

# shlex.join tạo chuỗi đối số an toàn cho bộ phân tích lệnh của wrapper ns3.
run_spec="$("$PYTHON" -c 'import shlex,sys; print(shlex.join(["s-pie"] + sys.argv[1:]))' "${args[@]}")"
printf '%s\n' "$run_spec"
# Chỉ in cấu hình, không build/chạy: bash .../run-simulation.sh --dry-run
if [[ "$DRY_RUN" == true ]]; then return 0; fi
mkdir -p -- "$ALGORITHM_DIR"
"$PYTHON" ns3 run --no-build "$run_spec"
printf '\nĐã chạy xong. Goodput: %s\n' "$OUTPUT"
"$PYTHON" "$SCRIPT_DIR/summarize.py" "$OUTPUT" > "${OUTPUT%.csv}-summary.csv"
cat -- "${OUTPUT%.csv}-summary.csv"
)

pids=()
logs=()
failed=0
cleanup() {
    trap - INT TERM
    for pid in "${pids[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
    wait || true
    exit 130
}
trap cleanup INT TERM
wait_first() {
    if ! wait "${pids[0]}"; then
        echo "Job lỗi, xem log: ${logs[0]}" >&2
        failed=1
    fi
    pids=("${pids[@]:1}")
    logs=("${logs[@]:1}")
}
for scenario in "${SCENARIOS[@]}"; do
    for run in "${RNG_RUNS[@]}"; do
        for aqm in "${ALGORITHMS[@]}"; do
            if [[ "$DRY_RUN" == true ]]; then
                run_one "$scenario" "$run" "$aqm"
                continue
            fi
            directory="$RESULT_DIR/scenario_${scenario}_run_${run}/$aqm"
            mkdir -p -- "$directory"
            log="$directory/s${scenario}-${aqm}-seed${RNG_SEED}-r${run}.log"
            echo "Chạy scenario=$scenario run=$run aqm=$aqm -> $log"
            run_one "$scenario" "$run" "$aqm" >"$log" 2>&1 &
            pids+=("$!")
            logs+=("$log")
            if (( ${#pids[@]} >= MAX_PARALLEL )); then wait_first; fi
        done
    done
done
while (( ${#pids[@]} )); do wait_first; done
if (( failed )); then echo 'Batch có job thất bại; kiểm tra log trước khi vẽ.' >&2; exit 1; fi
echo "Hoàn tất batch. Kết quả: $RESULT_DIR"
