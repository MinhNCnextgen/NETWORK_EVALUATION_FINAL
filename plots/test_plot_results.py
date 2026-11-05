"""Checks for aggregation semantics; synthetic data are never mixed with real runs."""
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from plot_results import queue_mean, jain, window, DROP
from plot_results import main, Plotter, ORDER, discover_batches, recover_flow_groups
import matplotlib.pyplot as plt


class MetricsTest(unittest.TestCase):
    def test_recover_exact_flow_endpoints(self):
        link=pd.DataFrame([
            ["10.0.0.5","10.0.0.10",6,5000,0,"unknown",100],
            ["10.0.0.13","10.0.0.18",6,5000,0,"unknown",200],
            ["10.0.0.5","10.0.0.18",6,5000,0,"unknown",50],
            ["10.0.0.5","10.0.0.10",17,5000,0,"unknown",25]],
            columns=["src_ip","dst_ip","protocol","dst_port","flow","group","wire_bytes"])
        fixed,n,byte_count=recover_flow_groups(link,2,1)
        self.assertEqual((n,byte_count),(2,300))
        self.assertEqual(fixed.group.tolist(),["small","large","unknown","unknown"])
        self.assertEqual(fixed.flow.tolist(),[1,2,0,0])
        self.assertEqual(fixed.wire_bytes.sum(),link.wire_bytes.sum())
        self.assertTrue((link.flow==0).all())
        again,n,_=recover_flow_groups(fixed,2,1)
        self.assertEqual(n,0)
        equal,_,_=recover_flow_groups(link,2,2)
        self.assertEqual(equal.group.tolist()[:2],["equal","equal"])
        link.loc[0,"flow"]=2
        with self.assertRaises(ValueError): recover_flow_groups(link,2,1)

    def test_named_batches_have_separate_output_directories(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root=Path(folder)
            for name in ["sim_1_run_1", "scenario_1_run_2"]:
                p=root/name/"Spie"
                p.mkdir(parents=True)
                pd.DataFrame(dict(scenario=1,seed=1,run=1).items(),columns=["key","value"]).to_csv(p/"sample-config.csv",index=False)
            with patch("sys.argv",["plot_results.py","--data",str(root),"--output",str(root/"output")]), patch("plot_results.render_batch") as render:
                main()
            self.assertEqual(render.call_count,2)
            self.assertEqual({call.args[0].output.name for call in render.call_args_list}, {"sim_1_run_1","scenario_1_run_2"})
            self.assertTrue(all(len(call.args[1])==1 for call in render.call_args_list))
            paths=list((root/"sim_1_run_1").rglob("*-config.csv"))
            self.assertEqual(next(iter(discover_batches(paths))).name,"sim_1_run_1")

    def test_queue_weights_time_and_last_simultaneous_state(self):
        q = pd.DataFrame({"time_ns": [0, 1_000_000_000, 1_000_000_000, 3_000_000_000],
                          "packets": [0, 9, 4, 0]})
        self.assertAlmostEqual(queue_mean(q, 0, 3), 8/3)
        self.assertAlmostEqual(queue_mean(q, .5, 2), 4/1.5)
        with self.assertRaises(ValueError):
            queue_mean(q, 0, 4)

    def test_jain_zero_flows_and_aggregation(self):
        self.assertTrue(np.isnan(jain([0,0])))
        self.assertEqual(jain([10,10]), 1)
        self.assertEqual(jain([10,0]), .5)
        self.assertEqual(jain(np.array([[10,0],[0,10]]).sum(axis=0)), 1)

    def test_half_open_windows_and_algorithm_specific_drops(self):
        f = pd.DataFrame({"time_ns": [0,1_000_000_000,2_000_000_000]})
        self.assertEqual(window(f,0,1).time_ns.tolist(),[0])
        self.assertEqual(DROP["Red"]["Forced drop"],"active")
        self.assertEqual(DROP["Pie"]["Forced drop"],"overflow")

    def test_scenario2_multiple_runs_end_to_end(self):
        # Tiny artificial fixture only inside a disposable test directory.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            for aqm in ORDER:
                for run in [1,2]:
                    prefix = root/f"s2-{aqm}-{run}"
                    config = dict(scenario=2, aqm=aqm, seed=1, run=run, flows=2, traffic_s=5)
                    pd.DataFrame(config.items(),columns=["key","value"]).to_csv(str(prefix)+"-config.csv",index=False)
                    pd.DataFrame([(t,f,1000*run,.008*run) for t in range(1,6) for f in [1,2]],
                                 columns=["end_s","flow","payload_bytes","goodput_mbps"]).to_csv(str(prefix)+".csv",index=False)
                    pd.DataFrame([[0,0,0],[1_000_000_000,1,1000],[5_000_000_000,0,0]],
                                 columns=["time_ns","packets","bytes"]).to_csv(str(prefix)+"-queue.csv",index=False)
                    pd.DataFrame([[100,1,"LastRTT",60_000_000],[100,1,"RTT",60_000_000]],
                                 columns=["time_ns","flow","metric","value_ns"]).to_csv(str(prefix)+"-rtt.csv",index=False)
                    pd.DataFrame(columns=["time_ns","location","layer","reason"]).to_csv(str(prefix)+"-drops.csv",index=False)
                    pd.DataFrame([[100,1000]],columns=["time_ns","wire_bytes"]).to_csv(str(prefix)+"-link.csv",index=False)
            figures=[]
            def save_without_export(self, fig, name, note):
                figures.append(name)
                plt.close(fig)
            with patch("sys.argv",["plot_results.py","--data",str(root),"--output",str(root/"out")]), patch.object(Plotter,"save",save_without_export):
                main()
            for name in ["scenario_2_queue_packets_1s","scenario_2_rtt_samples","scenario_2_throughput_bars_window","scenario_2_throughput_across_runs","scenario_2_jain_cumulative","scenario_2_overflow_drops","scenario_2_active_drops"]:
                self.assertIn(name,figures)
            table=pd.read_csv(root/"out"/"summary.csv")
            self.assertTrue(np.allclose(table.jain,1))
            self.assertEqual(set(table.run),{1,2})
            full=table[(table.start_s==0)&(table.end_s==5)]
            self.assertTrue(np.allclose(full.throughput_mbytes_s,1000/5/1e6))
            self.assertTrue(np.allclose(full.forward_wire_mbps,full.throughput_mbytes_s*8))
            self.assertFalse(np.allclose(full.goodput_mbps,full.forward_wire_mbps))
            manifest=json.loads((root/"out"/"manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest["inputs"]),8)
            # Exercise the new per-flow schema and Figure 6, including unknown bytes.
            for config_path in root.glob("*-config.csv"):
                c=pd.read_csv(config_path)
                c.loc[c.key=="scenario","value"]="1"
                c.to_csv(config_path,index=False)
                link_path=str(config_path).replace("-config.csv","-link.csv")
                pd.DataFrame([[100,1000,1,"small"],[200,2000,2,"large"],[300,500,0,"unknown"]],
                             columns=["time_ns","wire_bytes","flow","group"]).to_csv(link_path,index=False)
            figures.clear()
            with patch("sys.argv",["plot_results.py","--data",str(root),"--output",str(root/"out2")]), patch.object(Plotter,"save",save_without_export):
                main()
            self.assertIn("scenario_1_group_throughput_window",figures)
            t=pd.read_csv(root/"out2"/"summary.csv")
            full=t[(t.start_s==0)&(t.end_s==5)]
            self.assertTrue(np.allclose(full.small_throughput_mbytes_s,1000/5/1e6))
            self.assertTrue(np.allclose(full.large_throughput_mbytes_s,2000/5/1e6))
            cols=[f"{g}_throughput_mbytes_s" for g in ["small","large","equal","unknown"]]
            self.assertTrue(np.allclose(full[cols].sum(axis=1),full.throughput_mbytes_s))


if __name__ == "__main__":
    unittest.main()
