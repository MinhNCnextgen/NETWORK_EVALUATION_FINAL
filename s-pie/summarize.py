"""Tổng hợp một run theo khoảng giây nguyên [start, end) trong giai đoạn phát."""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path


def rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        yield from csv.DictReader(stream)


def summarize(path, start, end):
    def companion(suffix):
        return path.with_name(f"{path.stem}-{suffix}.csv")

    config = {row["key"]: row["value"] for row in rows(companion("config"))}
    end = int(config["traffic_s"]) if end is None else end
    if not 0 <= start < end <= int(config["traffic_s"]):
        raise ValueError("Khoảng đo phải nằm trong giai đoạn phát.")
    seconds = end - start
    lo, hi = start * 10**9, end * 10**9
    count = int(config["flows"])
    received = [0] * count
    samples = 0
    for row in rows(path):
        # end_s=1 là cửa sổ đầu tiên, từ 0 đến 1 giây.
        if start < int(row["end_s"]) <= end:
            received[int(row["flow"]) - 1] += int(row["payload_bytes"])
            samples += 1
    if samples != count * seconds:
        raise ValueError("CSV goodput thiếu dòng hoặc sai cửa sổ.")
    total = sum(received)
    squares = sum(value**2 for value in received)
    result = {"scenario": config["scenario"], "aqm": config["aqm"], "seed": config["seed"],
              "run": config["run"], "start_s": start, "end_s": end,
              "goodput_mbps": total * 8 / seconds / 10**6,
              "jain": total**2 / (count * squares) if squares else "NA"}
    if config["scenario"] == "1":
        result["small_goodput_mbps"] = sum(received[:count // 2]) * 8 / seconds / 10**6
        result["large_goodput_mbps"] = sum(received[count // 2:]) * 8 / seconds / 10**6

    # Tích phân hàm bậc thang. Giữ trạng thái trước start cho tới lần đổi tiếp theo.
    previous_time = 0
    packets = byte_count = packet_area = byte_area = 0
    for row in rows(companion("queue")):
        now = int(row["time_ns"])
        overlap = max(0, min(now, hi) - max(previous_time, lo))
        packet_area += packets * overlap
        byte_area += byte_count * overlap
        if now >= hi:
            break
        previous_time = now
        packets, byte_count = int(row["packets"]), int(row["bytes"])
    else:
        raise ValueError("Trace hàng đợi kết thúc trước khoảng đo.")
    result["mean_queue_packets"] = packet_area / (hi - lo)
    result["mean_queue_bytes"] = byte_area / (hi - lo)

    def in_window(row):
        return lo <= int(row["time_ns"]) < hi

    for metric, label in [("LastRTT", "last_rtt"), ("RTT", "srtt")]:
        # Trung bình trên sự kiện thay đổi của toàn bộ socket trong khoảng đo.
        n = total_ns = 0
        for row in rows(companion("rtt")):
            if row["metric"] == metric and in_window(row):
                total_ns += int(row["value_ns"])
                n += 1
        result[f"{label}_samples"] = n
        result[f"{label}_mean_ms"] = total_ns / n / 10**6 if n else "NA"

    wire = sum(int(row["wire_bytes"]) for row in rows(companion("link")) if in_window(row))
    result["forward_wire_mbps"] = wire * 8 / seconds / 10**6
    reasons = Counter()
    outside = 0
    for row in rows(companion("drops")):
        if in_window(row):
            if row["location"] == "core-forward" and row["layer"] == "qdisc":
                reasons[row["reason"]] += 1
            else:
                outside += 1
    result["forward_qdisc_drops"] = sum(reasons.values())
    result["other_queue_drops"] = outside
    for reason, n in sorted(reasons.items()):
        result["drop: " + reason] = n
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("goodput", type=Path)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()
    values = summarize(args.goodput, args.start, args.end)
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("metric", "value"))
    writer.writerows(values.items())
