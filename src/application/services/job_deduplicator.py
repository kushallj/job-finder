"""
Application Service: JobDeduplicator
Provides O(1) in-memory fingerprint hashing and set-based deduplication.
"""
from typing import List, Set, Tuple
from src.domain.entities.job import Job


class JobDeduplicator:
    """
    Deduplication engine ensuring duplicate jobs from multiple aggregators are eliminated.

    Time Complexity:
        deduplicate_batch(): O(N) where N is number of jobs.
    Space Complexity:
        O(N) for seen hashes set.
    """

    @staticmethod
    def deduplicate_batch(
        incoming_jobs: List[Job], existing_fingerprints: Set[str] = None
    ) -> Tuple[List[Job], List[Job]]:
        """
        Partition incoming jobs into new distinct jobs vs duplicates.

        Returns:
            Tuple[List[Job], List[Job]]: (unique_jobs, duplicate_jobs)
        """
        seen: Set[str] = set(existing_fingerprints or set())
        unique: List[Job] = []
        duplicates: List[Job] = []

        for job in incoming_jobs:
            fp = job.job_id or job.generate_fingerprint()
            if fp in seen:
                duplicates.append(job)
            else:
                seen.add(fp)
                unique.append(job)

        return unique, duplicates
