"""Export simulation snapshots to JSON/CSV with richer context."""

from __future__ import annotations

import csv
import json
import os
import datetime
from typing import Any, Dict, List


def export_results(*, sim_env, metrics, history: Dict[str, Any], loader, run_meta: Dict[str, Any] | None = None) -> Dict[str, str]:
    """
    Export a snapshot of the simulation state and metrics.

    Returns paths of the JSON and CSV files written.
    """
    os.makedirs("exports", exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    run_meta = run_meta or {}
    run_meta.setdefault("seed", getattr(sim_env, "seed", None))
    summary = metrics.summary()
    topic_rates = metrics.get_topic_rates(sim_env.now, window=3.0)
    pub_counts = metrics.topic_publish_counts()
    delivery_stats = metrics.topic_delivery_stats()
    energy_per_node = metrics.energy_by_device()

    # Per-node snapshot from loader
    nodes_data = loader.get_gui_node_data()
    for n in nodes_data:
        nid = n["id"]
        n["energy_j"] = energy_per_node.get(nid, 0.0)

    failover_info = {
        "last_start": getattr(loader.broker, "last_failover_start", None) if hasattr(loader, "broker") else None,
        "last_end": getattr(loader.broker, "last_failover_end", None) if hasattr(loader, "broker") else None,
    }

    data = {
        "timestamp": ts,
        "sim_time": sim_env.now,
        "run_meta": run_meta,
        "protocol": getattr(loader, "active_protocol", "unknown"),
        "gateway_position": getattr(loader, "gw_pos", None),
        "failover_info": failover_info,
        "summary": summary,
        "topic_rates_msgs_per_sec": topic_rates,
        "topic_publish_counts": pub_counts,
        "topic_delivery_stats": delivery_stats,
        "queue_depth_history": list(history.get("queue", [])),
        "nodes": nodes_data,
    }

    json_path = os.path.join("exports", f"results-{ts}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    csv_path = os.path.join("exports", f"results-{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "value"])
        for k, v in summary.items():
            writer.writerow([k, v])
        writer.writerow([])

        writer.writerow(["topic_publish_counts"])
        writer.writerow(["topic", "count"])
        _write_dict_rows(writer, pub_counts)
        writer.writerow([])

        writer.writerow(["topic_delivery_stats"])
        writer.writerow(["topic", "delivered", "avg_latency"])
        for t, stats in delivery_stats.items():
            writer.writerow([t, stats.get("delivered", 0), stats.get("avg_latency", 0.0)])
        writer.writerow([])

        writer.writerow(["topic_rates_msgs_per_sec"])
        writer.writerow(["topic", "msgs_per_sec"])
        _write_dict_rows(writer, topic_rates)
        writer.writerow([])

        writer.writerow(["queue_depth_history"])
        writer.writerow(list(history.get("queue", [])))
        writer.writerow([])

        writer.writerow(["failover_info"])
        writer.writerow(["last_start", failover_info["last_start"]])
        writer.writerow(["last_end", failover_info["last_end"]])
        writer.writerow([])

        writer.writerow(["nodes"])
        writer.writerow(["id", "type", "state", "battery", "protocol", "x", "y", "energy_j"])
        for n in nodes_data:
            writer.writerow([
                n.get("id", ""),
                n.get("type", ""),
                n.get("state", ""),
                n.get("battery", ""),
                n.get("protocol", ""),
                n.get("x", ""),
                n.get("y", ""),
                n.get("energy_j", ""),
            ])

    return {"json": json_path, "csv": csv_path}


def _write_dict_rows(writer: csv.writer, data: Dict[str, Any]) -> None:
    for k, v in data.items():
        writer.writerow([k, v])

