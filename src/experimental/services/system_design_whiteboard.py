"""
system_design_whiteboard.py — System Design Whiteboard Co-Pilot (Agent 24).
Provides real-time back-of-the-envelope capacity estimation, Mermaid & ASCII system
architecture diagrams, and defensive failure-mode mitigation matrices for System Design rounds.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("system_design_whiteboard")

SYSTEM_DESIGN_ARCHETYPES: List[Dict[str, Any]] = [
    {
        "archetype_id": "realtime_trading_engine",
        "title": "Design a Low-Latency High-Frequency Trading & Order-Matching Engine",
        "domain": "Fintech / Core Infrastructure",
        "default_dau": 5000000,
        "default_read_write_ratio": "1:4 (Write-Heavy)",
        "avg_payload_bytes": 512,
        "p99_sla_target": "< 500 microseconds",
        "recommended_db": "In-Memory Lock-Free Ring Buffer + LMAX Disruptor + Aeron UDP + TimescaleDB WAL",
    },
    {
        "archetype_id": "ride_hailing_platform",
        "title": "Design Global Ride-Hailing & Real-Time Driver Matching (Uber/Lyft)",
        "domain": "Distributed Geo-Spatial Systems",
        "default_dau": 30000000,
        "default_read_write_ratio": "5:1 (Location Telemetry Heavy)",
        "avg_payload_bytes": 1024,
        "p99_sla_target": "< 25 milliseconds",
        "recommended_db": "Redis Geohash / H3 Spatial Index + Kafka + Cassandra (Trip History)",
    },
    {
        "archetype_id": "video_streaming_platform",
        "title": "Design Distributed Video Transcoder & Streaming Mesh (YouTube/Netflix)",
        "domain": "Content Delivery & Media Processing",
        "default_dau": 100000000,
        "default_read_write_ratio": "100:1 (Read-Heavy)",
        "avg_payload_bytes": 2048,
        "p99_sla_target": "< 50 milliseconds",
        "recommended_db": "S3 Object Store + Cloudflare CDN Edge Cache + DynamoDB Metadata",
    },
    {
        "archetype_id": "distributed_rate_limiter",
        "title": "Design Multi-Region Distributed Rate Limiter & Token Bucket",
        "domain": "API Gateway & Security",
        "default_dau": 50000000,
        "default_read_write_ratio": "1:1 (Dual Read/Write on every API Call)",
        "avg_payload_bytes": 256,
        "p99_sla_target": "< 2 milliseconds",
        "recommended_db": "Redis Cluster (Sliding Window / Lua Scripts) + Local In-Memory Cache (Singleflight)",
    },
]


class WhiteboardRequest(BaseModel):
    archetype_id: str = "realtime_trading_engine"
    daily_active_users: Optional[int] = Field(default=10000000, ge=1000, description="Daily Active Users (DAU)")
    avg_actions_per_user_day: Optional[int] = Field(default=20, ge=1, description="Average requests per user per day")
    payload_size_bytes: Optional[int] = Field(default=1024, ge=64, description="Average payload size in bytes")


class SystemDesignWhiteboardService:
    """Computes capacity estimations, synthesizes Mermaid architectures, and generates defensive matrices."""

    def get_archetypes(self) -> List[Dict[str, Any]]:
        return SYSTEM_DESIGN_ARCHETYPES

    def estimate_and_diagram(
        self,
        archetype_id: str,
        dau: int = 10000000,
        actions_per_day: int = 20,
        payload_bytes: int = 1024,
    ) -> Dict[str, Any]:
        archetype = next((a for a in SYSTEM_DESIGN_ARCHETYPES if a["archetype_id"] == archetype_id), SYSTEM_DESIGN_ARCHETYPES[0])

        # 1. Back-of-the-Envelope Math
        total_requests_per_day = dau * actions_per_day
        avg_qps = round(total_requests_per_day / 86400.0, 1)
        peak_qps = round(avg_qps * 2.5, 1)  # 2.5x peak traffic multiplier

        # Storage calculations
        daily_storage_bytes = total_requests_per_day * payload_bytes
        daily_storage_gb = round(daily_storage_bytes / (1024 ** 3), 2)
        daily_storage_tb = round(daily_storage_gb / 1024.0, 3)
        annual_storage_tb = round(daily_storage_tb * 365.0, 2)

        # RAM Cache sizing (80/20 Pareto rule: 20% of daily data cached in RAM)
        ram_cache_gb = round((daily_storage_gb * 0.20), 1)

        # Network Egress Bandwidth
        egress_bytes_per_sec = avg_qps * payload_bytes
        egress_mbps = round((egress_bytes_per_sec * 8) / (1000 ** 2), 2)
        egress_gbps = round(egress_mbps / 1000.0, 3)

        # 2. Synthesize Mermaid Architecture Diagram
        mermaid_diagram = f"""graph TD
    Client["📱 Global Clients (Web / iOS / Android)"] --> DNS["🌐 Route53 Anycast DNS"]
    DNS --> CDN["⚡ Cloudflare Edge CDN (Static Assets & TLS Termination)"]
    CDN --> LB["⚖️ L4/L7 HAProxy / Envoy Load Balancer"]
    
    subgraph Gateway Layer
        LB --> APIGW["🛡️ API Gateway (Auth, Distributed Rate Limiting, Metrics)"]
    end
    
    subgraph Core Microservices & Event Stream
        APIGW --> ServiceA["⚙️ Ingestion & Validation Service (Go/Rust Workers)"]
        ServiceA --> Kafka["📨 Kafka / Redpanda Partitioned Event Bus"]
        Kafka --> Engine["🔥 Core Processing Engine ({archetype['p99_sla_target']})"]
    end
    
    subgraph Caching & State Storage
        Engine --> Cache["🚀 Redis Cluster ({ram_cache_gb} GB RAM - 80/20 Hot Keys)"]
        Engine --> PrimaryDB["🗄️ Primary Storage ({archetype['recommended_db']})"]
        PrimaryDB --> ReplicaDB["📚 Read Replicas (Multi-AZ Async Replication)"]
    end
"""

        # 3. Defensive Failure Mode & Edge Case Matrix
        failure_matrix = [
            {
                "failure_mode": "Cache Stampede / Thundering Herd",
                "risk": "Mass key expiration causes millions of concurrent queries to hammer the primary database, crashing DB pool.",
                "defensive_mitigation": "Implement Golang Singleflight mutex or Redis mutex lock + probabilistic early expiration (XFetch algorithm).",
            },
            {
                "failure_mode": "Hot Key / Celebrity Partition Imbalance",
                "risk": "A single popular key overloads one Redis shard while other nodes stay idle.",
                "defensive_mitigation": "Salting key with random shard suffix (e.g. key_#1 to key_#10) and local in-memory L1 LRU cache.",
            },
            {
                "failure_mode": "Split-Brain & Network Partition",
                "risk": "Two leaders accept conflicting writes during network partition, resulting in data divergence.",
                "defensive_mitigation": "Quorum-based Raft consensus (N/2 + 1 majority required for write commit) with automatic fencing tokens.",
            },
            {
                "failure_mode": "Backpressure Overload & OOM Crash",
                "risk": "Surge traffic floods unbounded in-memory queues, triggering Linux OOM Killer.",
                "defensive_mitigation": "Hard-bounded circular ring buffers with HTTP 429 adaptive throttling and Dead Letter Queue (DLQ).",
            },
        ]

        return {
            "status": "success",
            "archetype_id": archetype["archetype_id"],
            "title": archetype["title"],
            "domain": archetype["domain"],
            "p99_sla_target": archetype["p99_sla_target"],
            "capacity_estimates": {
                "daily_active_users": dau,
                "total_requests_per_day": total_requests_per_day,
                "avg_qps": avg_qps,
                "peak_qps": peak_qps,
                "daily_storage_gb": daily_storage_gb,
                "daily_storage_tb": daily_storage_tb,
                "annual_storage_tb": annual_storage_tb,
                "ram_cache_required_gb": ram_cache_gb,
                "network_egress_mbps": egress_mbps,
                "network_egress_gbps": egress_gbps,
            },
            "mermaid_diagram": mermaid_diagram,
            "failure_matrix": failure_matrix,
            "whiteboard_talking_points": [
                f"Peak QPS of {peak_qps:,.0f} req/s is easily handled by {max(2, int(peak_qps // 15000) + 1)} stateless Go instances behind Envoy.",
                f"RAM cache of {ram_cache_gb} GB accommodates the 80/20 hot data set across a 3-node Redis cluster.",
                f"Annual storage of {annual_storage_tb} TB is tiered between hot NVMe SSDs and cold S3 Parquet partitions.",
            ],
        }
