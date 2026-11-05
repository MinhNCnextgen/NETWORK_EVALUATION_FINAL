"""Plot ns-3 S-PIE CSV traces. Run with --help; no simulation data are modified."""
from __future__ import annotations

import argparse
import json
import re
from ipaddress import IPv4Address
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ORDER = ["Red", "CoDel", "Pie", "Spie"]
LABEL = dict(zip(ORDER, ["RED", "CoDel", "PIE", "S-PIE"]))
COLOR = dict(zip(ORDER, ["#d1495b", "#d48a00", "#2475b0", "#16856b"]))
ROOT = Path(__file__).resolve().parents[1]
DROP = {
    "Red": {"Dropped by internal queue": "overflow", "Forced drop": "active", "Unforced drop": "active"},
    "CoDel": {"Overlimit drop": "overflow", "Target exceeded drop": "active"},
    "Pie": {"Forced drop": "overflow", "Unforced drop": "active"},
    "Spie": {"Forced drop": "overflow", "Unforced drop": "active", "Sketch large-flow drop": "active"},
}


def recover_flow_groups(link, count, scenario):
    """Recover only exact endpoints of the current s-pie.cc /30 dumbbell layout.

    Core: 10.0.0.0/30; flow i (one-based): source=base+8*i-3,
    destination=base+8*i+2; one TCP sink, port 5000. Raw CSV is untouched.
    """
    required = {"src_ip", "dst_ip", "protocol", "dst_port", "flow", "group"}
    if not required.issubset(link.columns):
        return link, 0, 0
    base = int(IPv4Address("10.0.0.0"))
    endpoints = {(str(IPv4Address(base+8*i-3)), str(IPv4Address(base+8*i+2)), 6, 5000): i
                 for i in range(1,count+1)}
    keys = ["src_ip", "dst_ip", "protocol", "dst_port"]
    unique = link[keys].drop_duplicates()
    unique["_flow"] = [endpoints.get(tuple(row),0) for row in unique.itertuples(index=False,name=None)]
    matched = link[keys].merge(unique,on=keys,how="left",sort=False)["_flow"].to_numpy()
    known = link.flow.to_numpy()
    if ((known > 0) & (matched > 0) & (known != matched)).any():
        raise ValueError("Recorded flow conflicts with endpoint mapping; topology differs from s-pie.cc")
    recover = (known == 0) & (link.group.to_numpy() == "unknown") & (matched > 0)
    result = link.copy()
    result.loc[recover,"flow"] = matched[recover]
    groups = np.where(matched <= count//2,"small","large") if scenario == 1 else np.full(len(link),"equal")
    result.loc[recover,"group"] = groups[recover]
    return result, int(recover.sum()), int(result.loc[recover,"wire_bytes"].sum())


def jain(values):
    x = np.asarray(values, dtype=float)
    denominator = len(x) * np.sum(x * x)
    return float(x.sum() ** 2 / denominator) if denominator else np.nan


def queue_mean(frame, start, end, column="packets"):
    """Exact integral of post-event state; simultaneous events have zero duration."""
    t = frame.time_ns.to_numpy(dtype=np.int64)
    if t[0] != 0 or t[-1] < end * 1e9:
        raise ValueError("Queue trace does not cover requested interval")
    dt = np.maximum(0, np.minimum(t[1:], round(end * 1e9)) - np.maximum(t[:-1], round(start * 1e9)))
    return float(np.dot(dt.astype(float), frame[column].to_numpy()[:-1]) / ((end-start)*1e9))


def window(frame, start, end):
    return frame.loc[(frame.time_ns >= round(start*1e9)) & (frame.time_ns < round(end*1e9))]


class Run:
    def __init__(self, config_path):
        self.path = config_path
        c = pd.read_csv(config_path, dtype=str, keep_default_na=False)
        if c.key.duplicated().any():
            raise ValueError(f"Duplicate config key: {config_path}")
        self.config = dict(zip(c.key, c.value))
        self.aqm = self.config["aqm"]
        self.scenario, self.seed, self.run = (int(self.config[k]) for k in ["scenario", "seed", "run"])
        self.n, self.duration = (int(self.config[k]) for k in ["flows", "traffic_s"])
        if self.aqm not in ORDER or self.scenario not in (1, 2) or self.n <= 0 or self.duration <= 0:
            raise ValueError(f"Unsupported config: {config_path}")
        if self.scenario == 1 and self.n % 2:
            raise ValueError("Scenario 1 requires two equally sized flow groups")
        prefix = str(config_path)[:-len("-config.csv")]
        self.good = pd.read_csv(prefix + ".csv")
        if self.good.duplicated(["end_s", "flow"]).any():
            raise ValueError(f"Duplicate goodput keys: {prefix}")
        expected = pd.MultiIndex.from_product([range(1, self.duration+1), range(1, self.n+1)])
        actual = pd.MultiIndex.from_frame(self.good[["end_s", "flow"]])
        if len(expected.difference(actual)) or len(actual.difference(expected)):
            raise ValueError(f"Missing/extra goodput rows: {prefix}")
        if (self.good.payload_bytes < 0).any() or not np.allclose(self.good.goodput_mbps, self.good.payload_bytes*8/1e6):
            raise ValueError(f"Invalid payload/goodput: {prefix}")
        self.bytes = self.good.pivot(index="end_s", columns="flow", values="payload_bytes").sort_index().sort_index(axis=1).to_numpy()
        for name in ["queue", "rtt", "drops", "link"]:
            frame = pd.read_csv(prefix + f"-{name}.csv")
            if not frame.time_ns.is_monotonic_increasing or (frame.time_ns < 0).any():
                raise ValueError(f"Invalid timestamp order: {prefix}-{name}.csv")
            setattr(self, name, frame)
        if self.queue.empty or (self.queue[["packets", "bytes"]] < 0).any().any():
            raise ValueError(f"Invalid queue trace: {prefix}")
        limit = self.config.get("aqm.MaxSize", "")
        if limit.endswith("p") and self.queue.packets.max() > int(limit[:-1]):
            raise ValueError(f"Queue exceeds configured limit: {prefix}")
        if not self.rtt.metric.isin(["LastRTT", "RTT"]).all() or (self.rtt.value_ns < 0).any():
            raise ValueError(f"Invalid RTT trace: {prefix}")
        if not self.rtt.flow.between(1, self.n).all():
            raise ValueError(f"Invalid RTT flow ID: {prefix}")
        self.link, self.recovered_frames, self.recovered_bytes = recover_flow_groups(self.link,self.n,self.scenario)
        self.has_flow_trace = {"flow", "group"}.issubset(self.link.columns)
        if self.has_flow_trace:
            for flow, group in self.link[["flow", "group"]].drop_duplicates().itertuples(index=False):
                expected_group = "unknown" if flow == 0 else ("equal" if self.scenario == 2 else ("small" if flow <= self.n//2 else "large"))
                if flow != int(flow) or not 0 <= flow <= self.n or group != expected_group:
                    raise ValueError(f"Invalid flow/group mapping: {prefix}")

    def metrics(self, start, end):
        x = self.bytes[start:end].sum(axis=0)
        scale = 8 / ((end-start)*1e6)
        rr = window(self.rtt, start, end)
        dr = window(self.drops, start, end)
        core = dr.loc[(dr.location == "core-forward") & (dr.layer == "qdisc")]
        categories = core.reason.map(DROP[self.aqm]).fillna("unknown")
        link = window(self.link, start, end)
        def group_rate(group):
            return link.loc[link.group == group, "wire_bytes"].sum()/((end-start)*1e6) if self.has_flow_trace else np.nan
        return dict(scenario=self.scenario, aqm=self.aqm, seed=self.seed, run=self.run,
                    start_s=start, end_s=end, goodput_mbps=x.sum()*scale,
                    small_goodput_mbps=x[:self.n//2].sum()*scale if self.scenario == 1 else np.nan,
                    large_goodput_mbps=x[self.n//2:].sum()*scale if self.scenario == 1 else np.nan,
                    jain=jain(x), mean_queue_packets=queue_mean(self.queue, start, end),
                    mean_queue_bytes=queue_mean(self.queue, start, end, "bytes"),
                    last_rtt_mean_ms=rr.loc[rr.metric == "LastRTT", "value_ns"].mean()/1e6,
                    srtt_mean_ms=rr.loc[rr.metric == "RTT", "value_ns"].mean()/1e6,
                    forward_wire_mbps=window(self.link, start, end).wire_bytes.sum()*scale,
                    throughput_mbytes_s=window(self.link, start, end).wire_bytes.sum()/((end-start)*1e6),
                    small_throughput_mbytes_s=group_rate("small"),
                    large_throughput_mbytes_s=group_rate("large"),
                    equal_throughput_mbytes_s=group_rate("equal"),
                    unknown_throughput_mbytes_s=group_rate("unknown"),
                    overflow=int((categories == "overflow").sum()), active=int((categories == "active").sum()),
                    unknown=int((categories == "unknown").sum()), other_queue_drops=len(dr)-len(core))


class Plotter:
    def __init__(self, output, formats, dpi):
        self.output, self.formats, self.dpi = output, formats, dpi
        self.files = []
        output.mkdir(parents=True, exist_ok=True)
        plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                             "axes.spines.top": False, "axes.spines.right": False,
                             "axes.grid": True, "grid.alpha": .2, "savefig.facecolor": "white"})

    def save(self, fig, name, note):
        fig.text(.5, .015, note, ha="center", fontsize=8, color="#555555")
        fig.tight_layout(rect=(0, .06, 1, .97))
        for ext in self.formats:
            target = self.output / f"{name}.{ext}"
            fig.savefig(target, dpi=self.dpi)
            self.files.append(target.name)
        plt.close(fig)

    def lines(self, data, metric, title, name, ylabel, note, ylim=None):
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for aqm in ORDER:
            d = data.loc[data.aqm == aqm]
            if d.empty:
                continue
            g = d.groupby("end_s")[metric]
            mean, low, high = g.mean(), g.min(), g.max()
            n = d[["seed", "run"]].drop_duplicates().shape[0]
            ax.plot(mean.index, mean, marker="o", markersize=3, color=COLOR[aqm], label=f"{LABEL[aqm]} (n={n})")
            if n > 1:
                ax.fill_between(mean.index, low, high, color=COLOR[aqm], alpha=.12)
        ax.set(title=title, xlabel="Time (s)", ylabel=ylabel)
        if ylim:
            ax.set_ylim(*ylim)
        ax.legend(ncol=2)
        self.save(fig, name, note + " | Across runs: mean; shading: min–max (not CI).")

    def distribution(self, data, metric, title, name, ylabel, note):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        names = [a for a in ORDER if a in set(data.aqm)]
        labels = []
        for pos, aqm in enumerate(names, 1):
            v = data.loc[data.aqm == aqm, metric].dropna().to_numpy()
            labels.append(f"{LABEL[aqm]}\nn={len(v)}")
            if len(v) > 1:
                b = ax.boxplot([v], positions=[pos], widths=.5, patch_artist=True, showmeans=True)
                b["boxes"][0].set_facecolor(COLOR[aqm]); b["boxes"][0].set_alpha(.35)
            ax.scatter(np.full(len(v), pos), v, color=COLOR[aqm], s=28, zorder=3)
        ax.set_xticks(range(1, len(names)+1), labels)
        ax.set(title=title, ylabel=ylabel)
        self.save(fig, name, note + " | One point per run; boxplot only when n > 1.")


def check_comparability(runs):
    """Do not silently pool parameter sweeps as independent replicates."""
    seen = set()
    for r in runs:
        key = (r.scenario, r.aqm, r.seed, r.run)
        if key in seen:
            raise ValueError(f"Duplicate run identity {key}; select a single experiment directory")
        seen.add(key)
    for scenario in sorted({r.scenario for r in runs}):
        group = [r for r in runs if r.scenario == scenario]
        common = lambda r: {k:v for k,v in r.config.items() if not k.startswith("aqm") and k not in {"seed", "run"}}
        if any(common(r) != common(group[0]) for r in group):
            raise ValueError(f"Scenario {scenario}: different traffic/TCP configs; plot batches separately")
        for aqm in ORDER:
            subset = [r for r in group if r.aqm == aqm]
            configs = [{k:v for k,v in r.config.items() if k.startswith("aqm.") and k != "aqm.HashSeed"} for r in subset]
            if configs and any(c != configs[0] for c in configs):
                raise ValueError(f"{aqm}: parameter sweep cannot be pooled as replicates")


def discover_batches(paths):
    """Separate named experiment folders, including when --data names one directly."""
    batches = {}
    for path in paths:
        folder = next((p for p in path.parents
                       if re.fullmatch(r"(?:sim|scenario)_\d+_run_\d+", p.name, re.IGNORECASE)), None)
        batches.setdefault(folder, []).append(path)
    return batches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT/"data", help="Recursive search root for *-config.csv")
    parser.add_argument("--output", type=Path, default=ROOT/"plots"/"output")
    parser.add_argument("--scenario", type=int, choices=[1, 2])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--run", type=int)
    parser.add_argument("--period", type=int, default=5, help="Goodput/Jain period in integer seconds")
    parser.add_argument("--formats", nargs="+", choices=["png", "svg"], default=["png"])
    parser.add_argument("--dpi", type=int, default=180)
    parser.add_argument("--combine", action="store_true", help="Explicitly pool compatible runs into one output directory")
    args = parser.parse_args()
    if args.period < 1 or args.dpi < 50:
        parser.error("period must be >=1 and dpi >=50")
    paths = sorted(args.data.rglob("*-config.csv"))
    selected = []
    for path in paths:
        c = pd.read_csv(path, dtype=str).set_index("key")["value"]
        if all(value is None or int(c[key]) == value for key,value in
               [("scenario",args.scenario),("seed",args.seed),("run",args.run)]):
            selected.append(path)
    if not selected:
        parser.error("No matching run configs found")
    batches = {None: selected} if args.combine else discover_batches(selected)
    named = [folder.name for folder in batches if folder is not None]
    if len(named) != len(set(named)):
        parser.error("Duplicate experiment folder names; use a narrower --data root")
    for folder, batch_paths in batches.items():
        options = argparse.Namespace(**vars(args))
        if folder is not None:
            options.output = args.output / folder.name
        elif len(batches) > 1:
            options.output = args.output / "ungrouped"
        print(f"Batch: {folder.name if folder else 'combined/ungrouped'} -> {options.output}", flush=True)
        render_batch(options, batch_paths)


def render_batch(args, paths):
    runs = []
    summaries, series, periods, messages, recovery = [], [], [], [], []
    for path in paths:
        c = pd.read_csv(path, dtype=str).set_index("key")["value"]
        if any(value is not None and int(c[key]) != value for key,value in [("scenario",args.scenario),("seed",args.seed),("run",args.run)]):
            continue
        print(f"Loading {path.name}", flush=True)
        r = Run(path)
        runs.append(r)
        recovery.append(dict(scenario=r.scenario, aqm=r.aqm, seed=r.seed, run=r.run,
                             recovered_frames=r.recovered_frames, recovered_bytes=r.recovered_bytes))
        for start,end in sorted({(0,r.duration), (0,min(20,r.duration)), (min(5,r.duration-1),min(20,r.duration))}):
            summaries.append(r.metrics(start,end))
        for start in range(r.duration):
            series.append(r.metrics(start,start+1))
        for mode in ["window", "cumulative"]:
            for end in range(args.period, r.duration+1, args.period):
                row = r.metrics(end-args.period if mode == "window" else 0,end)
                periods.append(dict(row, aggregation=mode))
        # Keep only representative RTT events, not all multi-GB raw traces.
        earliest = min((x.seed,x.run) for x in runs if x.scenario == r.scenario)
        for x in runs:
            if x.scenario == r.scenario and (x.seed,x.run) != earliest:
                x.rtt = pd.DataFrame()
        r.queue = r.link = r.drops = r.good = None
        r.bytes = None
    if not runs:
        raise ValueError("No matching run configs found")
    check_comparability(runs)
    plot = Plotter(args.output, args.formats, args.dpi)
    summary, second, period = (pd.DataFrame(x) for x in [summaries,series,periods])
    for name,frame in [("summary",summary),("per_second",second),("periods",period)]:
        frame.to_csv(args.output/f"{name}.csv", index=False)
    pd.DataFrame(recovery).to_csv(args.output/"flow_recovery.csv",index=False)
    for scenario in [1,2]:
        group = [r for r in runs if r.scenario == scenario]
        if not group:
            messages.append(f"Scenario {scenario}: unavailable; corresponding paper figures skipped.")
            continue
        missing = [LABEL[a] for a in ORDER if not any(r.aqm == a for r in group)]
        if missing:
            messages.append(f"Scenario {scenario}: missing algorithms: {', '.join(missing)}")
        pairs = [{(r.seed,r.run) for r in group if r.aqm == a} for a in ORDER if any(r.aqm == a for r in group)]
        if any(p != pairs[0] for p in pairs):
            messages.append(f"Scenario {scenario}: unpaired seed/run sets across algorithms.")
        duration = group[0].duration
        if scenario == 1 and not all(r.has_flow_trace for r in group):
            messages.append("Figure 6 unavailable as group wire throughput: link.csv has no flow IDs. Group application goodput retained as a supplement.")
        end = min(20 if scenario == 1 else 30,duration)
        letter = "a" if scenario == 1 else "b"
        sec = second.loc[second.scenario == scenario]
        plot.lines(sec.loc[sec.end_s <= end], "mean_queue_packets", f"Scenario {scenario} — average queue length",
                   f"scenario_{scenario}_queue_packets_1s", "Time-weighted queue length (packets)", "1 s windows; not the paper's unspecified EWMA.", (0,None))
        # Show all raw change events for one explicitly named run; do not concatenate flows.
        chosen = min(group, key=lambda r:(r.seed,r.run))
        selected = [r for r in group if (r.seed,r.run) == (chosen.seed,chosen.run)]
        selected.sort(key=lambda r:ORDER.index(r.aqm))
        fig, axes = plt.subplots(len(selected),1,figsize=(9,2.1*len(selected)),sharex=True,sharey=True,squeeze=False)
        for ax,r in zip(axes[:,0],selected):
            rr = window(r.rtt.loc[r.rtt.metric == "LastRTT"],0,min(20,duration))
            ax.scatter(rr.time_ns/1e9,rr.value_ns/1e6,s=1,alpha=.22,color=COLOR[r.aqm],rasterized=True)
            ax.set_ylabel("RTT (ms)"); ax.set_title(LABEL[r.aqm],loc="right",fontsize=10)
            ax.set_ylim(bottom=0)
        axes[-1,0].set_xlabel("Time (s)")
        fig.suptitle(f"Scenario {scenario} — RTT samples")
        plot.save(fig,f"scenario_{scenario}_rtt_samples",f"All flows, LastRTT change events; seed={chosen.seed}, run={chosen.run}. No cross-flow connecting lines.")
        for mode in ["window","cumulative"]:
            p = period.loc[(period.scenario == scenario)&(period.aggregation == mode)&(period.end_s <= end)]
            if p.empty:
                messages.append(f"Scenario {scenario}: duration shorter than period; period plots skipped.")
                continue
            note = f"{args.period} s windows" if mode == "window" else "Cumulative [0,t) bytes per flow"
            plot.lines(p,"jain",f"Scenario {scenario} — Jain fairness ({mode})",f"scenario_{scenario}_jain_{mode}","Jain fairness index",note+"; all configured flows, including zeros.",(0,1.02))
            if scenario == 1:
                if all(r.has_flow_trace for r in group):
                    fig, ax = plt.subplots(figsize=(9,5))
                    for aqm in ORDER:
                        d = p.loc[p.aqm == aqm]
                        for kind, style in [("small", "-"), ("large", "--")]:
                            g = d.groupby("end_s")[f"{kind}_throughput_mbytes_s"].mean()
                            if not g.empty:
                                ax.plot(g.index,g,style,marker="o",color=COLOR[aqm],label=f"{LABEL[aqm]} ({kind})")
                    ax.set(title="Scenario 1 — small/large group link throughput",xlabel="Time (s)",ylabel="Group link throughput (10⁶ byte/s)",ylim=(0,None))
                    ax.legend(ncol=2,fontsize=9)
                    plot.save(fig,f"scenario_1_group_throughput_{mode}",note+" | Groups from source configuration; forward wire bytes incl. retransmissions.")
                    if (p.unknown_throughput_mbytes_s > 0).any():
                        messages.append(f"Figure 6 ({mode}): unclassified wire bytes excluded from groups; see unknown_throughput_mbytes_s.")
                fig,ax = plt.subplots(figsize=(9,5))
                for aqm in ORDER:
                    d = p.loc[p.aqm == aqm]
                    if d.empty:
                        continue
                    for kind,style in [("small","-"),("large","--")]:
                        g = d.groupby("end_s")[f"{kind}_goodput_mbps"].mean()
                        ax.plot(g.index,g,style,marker="o",color=COLOR[aqm],label=f"{LABEL[aqm]} ({kind})")
                ax.set(title="Scenario 1 — small/large group application goodput",xlabel="Time (s)",ylabel="Group application goodput (Mbps)",ylim=(0,None))
                ax.legend(ncol=2,fontsize=9)
                plot.save(fig,f"scenario_1_group_goodput_{mode}",note+" | Application payload received at sinks.")
            else:
                fig,ax = plt.subplots(figsize=(9,5))
                names = [a for a in ORDER if a in set(p.aqm)]
                times = sorted(p.end_s.unique()); x=np.arange(len(times)); width=.8/len(names)
                for i,aqm in enumerate(names):
                    y=p.loc[p.aqm==aqm].groupby("end_s").throughput_mbytes_s.mean().reindex(times)
                    ax.bar(x+(i-(len(names)-1)/2)*width,y,width,label=LABEL[aqm],color=COLOR[aqm])
                ax.set_xticks(x,times); ax.set(title="Scenario 2 — link throughput by period",xlabel="Time (s)",ylabel="Link throughput (10⁶ byte/s)")
                ax.legend(ncol=4)
                plot.save(fig,f"scenario_2_throughput_bars_{mode}",note+" | Forward link, includes headers/retransmissions; paper measurement layer unspecified.")
        full = summary.loc[(summary.scenario==scenario)&(summary.start_s==0)&(summary.end_s==duration)]
        if scenario == 2:
            plot.distribution(full,"throughput_mbytes_s","Scenario 2 — link throughput across runs","scenario_2_throughput_across_runs","Link throughput (10⁶ byte/s)",f"Forward link; [0,{duration}) s per run; paper measurement layer unspecified")
        for mode in ["window", "cumulative"]:
            throughput_period = period.loc[(period.scenario == scenario)&(period.aggregation == mode)]
            if not throughput_period.empty:
                plot.lines(throughput_period,"throughput_mbytes_s",f"Scenario {scenario} — total link throughput",f"scenario_{scenario}_total_throughput_{mode}","Link throughput (10⁶ byte/s)",f"{mode}; period={args.period} s; forward link incl. headers/retransmissions.",(0,None))
        for metric,letter_drop in [("overflow","a"),("active","b")]:
            name = f"scenario_{scenario}_{metric}_drops"
            title = f"Scenario {scenario} — {metric} packet drops"
            plot.distribution(full,metric,title,name,"Packets dropped",f"Forward bottleneck qdisc; [0,{duration}) s; {metric}")
        plot.lines(sec,"goodput_mbps",f"Scenario {scenario} — application goodput",f"scenario_{scenario}_goodput_1s","Mbps","1 s windows",(0,None))
        plot.lines(sec,"forward_wire_mbps",f"Scenario {scenario} — forward wire rate",f"scenario_{scenario}_link_throughput_mbps_1s","Mbps","Headers/retransmissions included; frame assigned at transmission start.",(0,None))
        plot.lines(sec,"mean_queue_bytes",f"Scenario {scenario} — queued bytes",f"scenario_{scenario}_queue_bytes_1s","Time-weighted queue length (bytes)","1 s windows",(0,None))
        plot.lines(sec,"srtt_mean_ms",f"Scenario {scenario} — SRTT",f"scenario_{scenario}_srtt_1s","SRTT (ms)","Mean of RTT trace change events per 1 s window.",(0,None))
        plot.lines(sec,"jain",f"Scenario {scenario} — fairness each second",f"scenario_{scenario}_jain_1s","Jain fairness index","Jain calculated separately from each 1 s window; all flows.",(0,1.02))
        if (full.unknown > 0).any():
            messages.append(f"Scenario {scenario}: unknown drop reasons; excluded from active/overflow. See summary.csv.")
        if all(sum(r.aqm == a for r in group) <= 1 for a in ORDER):
            messages.append(f"Scenario {scenario}: one run per algorithm; no between-run variability estimate.")
    manifest = dict(inputs=[str(r.path.resolve()) for r in runs], figures=plot.files, messages=messages,
                    period_s=args.period, units="Link throughput: 10^6 byte/s; goodput: Mbps; packets; milliseconds", rtt="LastRTT change events",
                    throughput_source="link.csv wire_bytes at forward bottleneck PhyTxBegin; frame counted at transmission start",
                    flow_recovery=recovery,
                    notes=["Simulation results only; no digitized paper curves.",
                           "Queue time mean differs from paper EWMA; throughput window unspecified in paper.",
                           "Drain excluded. Run-level metrics calculated before aggregation. No confidence intervals.",
                           "Link throughput matches the paper axis units but is not established as the same measurement layer."])
    (args.output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("\n".join(messages))
    print(f"Saved {len(plot.files)} figure files to {args.output.resolve()}")


if __name__ == "__main__":
    main()
