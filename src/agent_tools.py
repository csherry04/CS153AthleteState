"""Tool suite for the coaching agent to query athlete monitoring data and state."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.counterfactual_simulator import simulate_volume_reduction


class CoachingAgentTools:
    """Tools for an OpenRouter agent to interact with athlete state and monitoring."""

    def __init__(
        self,
        scores_csv: str | Path = "outputs/analysis/athlete_bone_stress_scores.csv",
        date_explorer_json: str | Path = "outputs/analysis/date_explorer.json",
        feedback_json: str | Path = "outputs/analysis/athlete_bone_stress_feedback.json",
        frontier_eval_json: str | Path = "outputs/analysis/frontier_outcome_evaluation.json",
        periods_csv: str | Path = "outputs/analysis/athlete_bone_stress_periods.csv",
        profile_json: str | Path = "outputs/analysis/athlete_profile.json",
    ):
        """Load athlete data into memory."""
        self.scores_csv = Path(scores_csv)
        self.date_explorer_json = Path(date_explorer_json)
        self.feedback_json = Path(feedback_json)
        self.frontier_eval_json = Path(frontier_eval_json)
        self.periods_csv = Path(periods_csv)
        self.profile_json = Path(profile_json)

        # Load primary data
        self.scores_df = pd.read_csv(self.scores_csv)
        self.scores_df["date"] = pd.to_datetime(self.scores_df["date"])
        self.scores_df = self.scores_df.sort_values("date").reset_index(drop=True)

        with open(self.date_explorer_json) as f:
            self.date_explorer = json.load(f)

        with open(self.feedback_json) as f:
            self.feedback = json.load(f)

        with open(self.frontier_eval_json) as f:
            self.frontier_eval = json.load(f)

        if self.periods_csv.exists():
            self.periods_df = pd.read_csv(self.periods_csv)
        else:
            self.periods_df = pd.DataFrame()

        if self.profile_json.exists():
            with open(self.profile_json) as f:
                self.profile = json.load(f)
        else:
            self.profile = {}

    def get_day(self, date_str: str) -> dict[str, Any]:
        """Retrieve all monitoring data for a single day.

        Args:
            date_str: Date as 'YYYY-MM-DD'

        Returns:
            Dictionary with scores, alert tier, reasons, and attribution.
        """
        try:
            query_date = pd.to_datetime(date_str).date()
        except Exception:
            return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

        # Find day in scores
        day_row = self.scores_df[self.scores_df["date"].dt.date == query_date]
        if day_row.empty:
            return {"error": f"No data for {date_str}. Data range: {self.scores_df['date'].min()} to {self.scores_df['date'].max()}"}

        row = day_row.iloc[0].to_dict()

        # Find day in date_explorer for alert info
        day_explorer = None
        for day in self.date_explorer["days"]:
            if day["date"] == date_str:
                day_explorer = day
                break

        if day_explorer is None:
            return {"error": f"Alert data missing for {date_str}"}

        return {
            "date": date_str,
            "alert_tier": day_explorer.get("tier", "unknown"),
            "alert_label": day_explorer.get("alertLabel", "Unknown"),
            "combined_score": round(row.get("integrated_bone_stress_score", row.get("bone_stress_risk_score", 0)), 2),
            "integrated_score": round(row.get("integrated_bone_stress_score", row.get("bone_stress_risk_score", 0)), 2),
            "combined_level": day_explorer.get("combinedLevel", "unknown"),
            "reason": day_explorer.get("reason", ""),
            "literature_score": round(row.get("literature_bone_stress_score", 0), 2),
            "personalized_score": round(row.get("personalized_bone_stress_score", 0), 2),
            "frontier_score": round(row.get("frontier_strain_score", 0), 2) if pd.notna(row.get("frontier_strain_score")) else None,
            "embedding_novelty_score": round(row.get("embedding_novelty_score", 0), 2) if pd.notna(row.get("embedding_novelty_score")) else None,
            "contrastive_novelty_score": round(row.get("contrastive_novelty_score", 0), 2) if pd.notna(row.get("contrastive_novelty_score")) else None,
            "readiness_forecast_error_score": round(row.get("readiness_forecast_error_score", 0), 2)
            if pd.notna(row.get("readiness_forecast_error_score"))
            else None,
            "reference_similarity_score": round(row.get("reference_block_similarity_score", 0), 2)
            if pd.notna(row.get("reference_block_similarity_score"))
            else None,
            "run_7d_km": round(row.get("running_7d_sum_m", 0) / 1000, 1) if pd.notna(row.get("running_7d_sum_m")) else 0,
            "run_28d_km": round(row.get("running_28d_sum_m", 0) / 1000, 1) if pd.notna(row.get("running_28d_sum_m")) else 0,
            "run_today_km": round(row.get("running_distance", 0) / 1000, 1) if pd.notna(row.get("running_distance")) else 0,
            "acwr": round(row.get("running_acwr_score", 0), 2),
            "acwr_zone": row.get("running_acwr_zone", "unknown"),
            "recovery_strain": round(row.get("recovery_strain_score", 0), 2),
            "accumulated_state": round(row.get("accumulated_bone_stress_state", 0), 2),
            "accumulated_level": day_explorer.get("accumulatedLevel", "unknown"),
            "agreement": day_explorer.get("agreement", "unknown"),
            "recommendation": day_explorer.get("recommendation", ""),
            "counterfactual": day_explorer.get("counterfactual", ""),
            "archetype": day_explorer.get("archetype"),
            "neighbors": day_explorer.get("neighbors"),
            "attribution": day_explorer.get("attribution"),
            "attribution_drivers": day_explorer.get("attributionDrivers"),
        }

    def compare_days(self, date1_str: str, date2_str: str) -> dict[str, Any]:
        """Compare two days side-by-side.

        Args:
            date1_str: First date as 'YYYY-MM-DD'
            date2_str: Second date as 'YYYY-MM-DD'

        Returns:
            Dictionary with scores and patterns for both dates.
        """
        day1 = self.get_day(date1_str)
        day2 = self.get_day(date2_str)

        if "error" in day1 or "error" in day2:
            return {"error": f"Could not retrieve one or both days. day1 error: {day1.get('error')}, day2 error: {day2.get('error')}"}

        return {
            "day1": day1,
            "day2": day2,
            "score_change": round((day1.get("combined_score", 0) - day2.get("combined_score", 0)), 2),
            "run_7d_change_km": round((day1.get("run_7d_km", 0) - day2.get("run_7d_km", 0)), 1),
            "run_28d_change_km": round((day1.get("run_28d_km", 0) - day2.get("run_28d_km", 0)), 1),
            "alert_change": f"{day2.get('alert_label')} → {day1.get('alert_label')}",
            "key_differences": self._extract_differences(day1, day2),
        }

    def get_periods_around(self, date_str: str, lookback_days: int = 7, lookahead_days: int = 7) -> dict[str, Any]:
        """Get period context: N days before and after a date.

        Args:
            date_str: Center date as 'YYYY-MM-DD'
            lookback_days: Days to look back (default 7)
            lookahead_days: Days to look ahead (default 7)

        Returns:
            Dictionary with alerts and peaks in the surrounding period.
        """
        try:
            center_date = pd.to_datetime(date_str).date()
        except Exception:
            return {"error": f"Invalid date format: {date_str}"}

        start = center_date - timedelta(days=lookback_days)
        end = center_date + timedelta(days=lookahead_days)

        mask = (self.scores_df["date"].dt.date >= start) & (self.scores_df["date"].dt.date <= end)
        window = self.scores_df[mask]

        if window.empty:
            return {"error": f"No data in window around {date_str}"}

        alerts = []
        for day in self.date_explorer["days"]:
            day_dt = pd.to_datetime(day["date"]).date()
            if start <= day_dt <= end:
                alerts.append(
                    {
                        "date": day["date"],
                        "tier": day.get("tier"),
                        "score": day.get("combinedScore"),
                        "run_7d_km": round(day.get("run7Km", 0), 1),
                    }
                )

        peaks = window.nlargest(3, "integrated_bone_stress_score")[["date", "integrated_bone_stress_score", "running_7d_sum_m"]].to_dict("records")

        return {
            "center_date": date_str,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "alerts_in_period": alerts,
            "top_3_scores": [
                {
                    "date": p["date"].strftime("%Y-%m-%d"),
                    "score": round(p["integrated_bone_stress_score"], 2),
                    "run_7d_km": round(p.get("running_7d_sum_m", 0) / 1000, 1),
                }
                for p in peaks
            ],
            "min_score": round(window["integrated_bone_stress_score"].min(), 2),
            "max_score": round(window["integrated_bone_stress_score"].max(), 2),
            "avg_run_7d": round(window["running_7d_sum_m"].mean() / 1000, 1),
        }

    def simulate_volume_cut(self, date_str: str, factor: float = 0.85) -> dict[str, Any]:
        """What-if: if volume on this day had been reduced by (1-factor)*100%, what would scores be?

        Args:
            date_str: Date to simulate as 'YYYY-MM-DD'
            factor: Volume multiplier (0.85 = 15% reduction, default)

        Returns:
            Dictionary with projected score under cutback scenario.
        """
        try:
            query_date = pd.to_datetime(date_str).date()
        except Exception:
            return {"error": f"Invalid date format: {date_str}"}

        day_row = self.scores_df[self.scores_df["date"].dt.date == query_date]
        if day_row.empty:
            return {"error": f"No data for {date_str}"}

        idx = int(day_row.index[0])
        row = self.scores_df.iloc[idx]
        current_score = row.get("integrated_bone_stress_score", row.get("bone_stress_risk_score", 0))
        scenario = simulate_volume_reduction(self.scores_df, idx, factor=factor, lookback_days=7)

        return {
            "date": date_str,
            "scenario": f"Volume cut to {factor*100:.0f}%",
            "current_score": round(current_score, 2),
            "actual_literature_score": round(float(row.get("literature_bone_stress_score", 0)), 2),
            "scenario_literature_score": round(float(scenario["scenario_literature_score"]), 2),
            "literature_score_change": round(float(scenario["delta_literature_score"]), 2),
            "actual_run7_km": round(float(scenario["baseline_run7_km"]), 1),
            "scenario_run7_km": round(float(scenario["scenario_run7_km"]), 1),
            "limitation": "This recomputes the literature/workload-rule score only. It does not rerun personalized percentiles, frontier embeddings, or accumulated tissue-state dynamics.",
        }

    def simulate_adjustment_plan(
        self,
        date_str: str,
        target_literature_score: float = 70.0,
        min_factor: float = 0.5,
    ) -> dict[str, Any]:
        """Search volume reductions and find the smallest cut that changes the literature workload score target.

        This is a conservative planning layer: it can recompute literature/workload score under lower volume,
        but it cannot fully rerun learned embeddings or personalized history.
        """
        try:
            query_date = pd.to_datetime(date_str).date()
        except Exception:
            return {"error": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}

        day_row = self.scores_df[self.scores_df["date"].dt.date == query_date]
        if day_row.empty:
            return {"error": f"No data for {date_str}"}

        idx = int(day_row.index[0])
        row = self.scores_df.iloc[idx]
        factors = [round(x / 100, 2) for x in range(95, int(min_factor * 100) - 1, -5)]
        scenarios = []
        for factor in factors:
            scenario = simulate_volume_reduction(self.scores_df, idx, factor=factor, lookback_days=7)
            scenarios.append(
                {
                    "volume_factor": factor,
                    "volume_reduction_pct": round((1 - factor) * 100),
                    "scenario_run7_km": round(float(scenario["scenario_run7_km"]), 1),
                    "scenario_literature_score": round(float(scenario["scenario_literature_score"]), 2),
                    "literature_score_change": round(float(scenario["delta_literature_score"]), 2),
                }
            )

        crossing = next((item for item in scenarios if item["scenario_literature_score"] < target_literature_score), None)
        actual = self.get_day(date_str)
        return {
            "date": date_str,
            "actual": actual,
            "target_literature_score": target_literature_score,
            "smallest_reduction_meeting_target": crossing,
            "scenario_grid": scenarios,
            "recommendation_guardrail": "Use the smallest_reduction_meeting_target as a workload-rule planning reference only. Do not claim it would prevent injury or directly lower frontier strain without rerunning the learned model.",
            "limitation": "Only the literature/workload score is recomputed under changed volume; personalized, frontier, and accumulated state are reported as actual context.",
        }

    def simulate_down_week_impact(self, start_date: str = "2024-02-05", factor: float = 0.8, days: int = 7) -> dict[str, Any]:
        """Estimate a down-week impact over a contiguous period.

        This recomputes the literature workload score under reduced running volume.
        It does not retrain or rerun frontier embeddings, personalized percentiles, or accumulated tissue state.
        """
        try:
            start = pd.to_datetime(start_date)
        except Exception:
            return {"error": f"Invalid date format: {start_date}. Use YYYY-MM-DD."}

        frame = self.scores_df.sort_values("date").reset_index(drop=True).copy()
        end = start + pd.Timedelta(days=days - 1)
        mask = (frame["date"] >= start) & (frame["date"] <= end)
        window = frame[mask]
        if window.empty:
            return {"error": f"No data from {start_date} for {days} days."}

        day_results = []
        for idx in window.index:
            scenario = simulate_volume_reduction(frame, int(idx), factor=factor, lookback_days=7)
            row = frame.iloc[int(idx)]
            actual_integrated = row.get("integrated_bone_stress_score", row.get("bone_stress_risk_score"))
            actual_literature = row.get("literature_bone_stress_score")
            actual_personalized = row.get("personalized_bone_stress_score")
            actual_frontier = row.get("frontier_strain_score")
            day_results.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "actual_integrated_score": round(float(actual_integrated), 2) if pd.notna(actual_integrated) else None,
                    "actual_literature_score": round(float(actual_literature), 2) if pd.notna(actual_literature) else None,
                    "actual_personalized_score": round(float(actual_personalized), 2) if pd.notna(actual_personalized) else None,
                    "actual_frontier_score": round(float(actual_frontier), 2) if pd.notna(actual_frontier) else None,
                    "actual_run7_km": round(float(row.get("running_7d_sum_m", 0)) / 1000, 1),
                    "scenario_run7_km": round(float(scenario["scenario_run7_km"]), 1),
                    "scenario_literature_score": round(float(scenario["scenario_literature_score"]), 2),
                    "literature_delta": round(float(scenario["delta_literature_score"]), 2),
                }
            )

        actual_integrated_values = [d["actual_integrated_score"] for d in day_results if d["actual_integrated_score"] is not None]
        actual_literature_values = [d["actual_literature_score"] for d in day_results if d["actual_literature_score"] is not None]
        scenario_literature_values = [d["scenario_literature_score"] for d in day_results]
        deltas = [d["literature_delta"] for d in day_results]

        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "volume_factor": factor,
            "volume_reduction_pct": round((1 - factor) * 100),
            "actual_integrated_range": [min(actual_integrated_values), max(actual_integrated_values)] if actual_integrated_values else None,
            "actual_literature_range": [min(actual_literature_values), max(actual_literature_values)] if actual_literature_values else None,
            "scenario_literature_range": [min(scenario_literature_values), max(scenario_literature_values)] if scenario_literature_values else None,
            "mean_literature_delta": round(float(pd.Series(deltas).mean()), 2) if deltas else None,
            "largest_literature_drop": round(float(min(deltas)), 2) if deltas else None,
            "days": day_results,
            "important_limitation": "This recomputes literature workload response only. Frontier embeddings, personalized percentile history, and accumulated tissue state are not fully recomputed.",
        }

    def get_frontier_evaluation(self) -> dict[str, Any]:
        """Retrieve frontier model evaluation: lead time before spring 2024 injury.

        Returns:
            Dictionary with validation metrics and key findings.
        """
        eval_summary = self.frontier_eval.get("summary", {})

        return {
            "title": "Frontier Model Validation",
            "target_injury": "Spring 2024 bone stress",
            "lead_days": eval_summary.get("lead_days_before_onset"),
            "peak_alert_date": eval_summary.get("peak_alert_date"),
            "flagging_rate": eval_summary.get("flagging_rate"),
            "precision": eval_summary.get("precision"),
            "recall": eval_summary.get("recall"),
            "agreement_level": eval_summary.get("agreement_level"),
            "key_finding": eval_summary.get("key_finding"),
            "full_eval": self.frontier_eval,
        }

    def get_riskiest_period(self, metric: str = "peak_accumulated_bone_stress_state") -> dict[str, Any]:
        """Return the single riskiest bone-stress period using the chosen metric.

        Args:
            metric: Column to rank by (default peak_accumulated_bone_stress_state).

        Returns:
            Dictionary with the top period and summary.
        """
        if self.periods_df.empty:
            return {"error": "Period data not available."}

        if metric not in self.periods_df.columns:
            return {"error": f"Metric '{metric}' not found in period data."}

        top = self.periods_df.sort_values(metric, ascending=False).iloc[0].to_dict()

        return {
            "metric": metric,
            "start_date": top.get("start_date"),
            "end_date": top.get("end_date"),
            "calendar_days": int(top.get("calendar_days", 0)),
            "elevated_days": int(top.get("elevated_days", 0)),
            "peak_state": round(float(top.get("peak_accumulated_bone_stress_state", 0)), 2),
            "mean_state": round(float(top.get("mean_accumulated_bone_stress_state", 0)), 2),
            "peak_7d_km": round(float(top.get("peak_running_7d_km", 0)), 1),
            "mean_7d_km": round(float(top.get("mean_running_7d_km", 0)), 1),
            "dominant_reason": top.get("dominant_bone_stress_reason"),
            "period_level": top.get("period_level"),
            "summary": top.get("period_summary"),
        }

    def get_highlighted_days(
        self,
        start_date: str = "2024-02-01",
        end_date: str = "2024-04-01",
        top_n: int = 8,
    ) -> dict[str, Any]:
        """Return days highlighted by literature, personalized, and frontier scoring.

        Args:
            start_date: Start date for the window.
            end_date: End date for the window.
            top_n: Max rows per scoring model.
        """
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        frame = self.scores_df[(self.scores_df["date"] >= start) & (self.scores_df["date"] <= end)].copy()
        if frame.empty:
            return {"error": f"No data between {start_date} and {end_date}."}

        def rows_for(score_col: str, level_col: str, label: str) -> list[dict[str, Any]]:
            subset = frame[frame[level_col].astype(str).str.lower().eq("high")].copy()
            if subset.empty:
                subset = frame.nlargest(top_n, score_col).copy()
            else:
                subset = subset.nlargest(top_n, score_col)
            rows = []
            for _, row in subset.iterrows():
                rows.append(
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "score": round(float(row.get(score_col, 0)), 2) if pd.notna(row.get(score_col)) else None,
                        "level": row.get(level_col),
                        "integrated_score": round(float(row.get("integrated_bone_stress_score", 0)), 2)
                        if pd.notna(row.get("integrated_bone_stress_score"))
                        else None,
                        "run_7d_km": round(float(row.get("running_7d_sum_m", 0)) / 1000, 1),
                        "run_28d_km": round(float(row.get("running_28d_sum_m", 0)) / 1000, 1),
                        "reason": row.get("bone_stress_risk_reason"),
                        "agreement": row.get("monitoring_signal_agreement"),
                        "frontier_drivers": row.get("frontier_attribution_drivers"),
                    }
                )
            return rows

        return {
            "window": {"start_date": start_date, "end_date": end_date},
            "literature": rows_for("literature_bone_stress_score", "literature_bone_stress_level", "literature"),
            "personalized": rows_for("personalized_bone_stress_score", "personalized_bone_stress_level", "personalized"),
            "frontier": rows_for("frontier_strain_score", "frontier_strain_level", "frontier"),
            "interpretation": "Literature highlights objective workload-rule risk, personalized highlights unusual load for this athlete, and frontier highlights learned multivariate strain/anomaly states.",
        }

    def explain_day_flag(self, date_str: str, model: str = "frontier") -> dict[str, Any]:
        """Return model-specific evidence for why a day was flagged.

        This tool separates model evidence from contextual facts. For example,
        ACWR is workload-rule/literature context, not a direct frontier cause.
        """
        day = self.get_day(date_str)
        if "error" in day:
            return day

        model = model.lower().strip()
        if model not in {"frontier", "literature", "personalized", "all"}:
            model = "frontier"

        literature_evidence = {
            "score": day.get("literature_score"),
            "basis": "Objective workload-rule features: ACWR/workload ratio, absolute 7-day running volume, speed/intensity, Foster monotony/strain.",
            "direct_context": {
                "run_7d_km": day.get("run_7d_km"),
                "run_28d_km": day.get("run_28d_km"),
                "acwr_score": day.get("acwr"),
                "acwr_zone": day.get("acwr_zone"),
                "reason": day.get("reason"),
            },
        }

        personalized_evidence = {
            "score": day.get("personalized_score"),
            "basis": "Athlete-specific percentile/context scoring versus this athlete's historical running patterns and recent progression.",
            "direct_context": {
                "run_7d_km": day.get("run_7d_km"),
                "run_28d_km": day.get("run_28d_km"),
                "accumulated_state": day.get("accumulated_state"),
                "reason": day.get("reason"),
            },
        }

        frontier_evidence = {
            "score": day.get("frontier_score"),
            "basis": "Learned-state strain from embedding novelty, readiness forecast error, and reference-block similarity. It should not be explained as ACWR-driven unless the stored frontier attribution specifically says so.",
            "direct_components": {
                "embedding_novelty_score": day.get("embedding_novelty_score"),
                "contrastive_novelty_score": day.get("contrastive_novelty_score"),
                "readiness_forecast_error_score": day.get("readiness_forecast_error_score"),
                "reference_similarity_score": day.get("reference_similarity_score"),
                "archetype": day.get("archetype"),
                "neighbors": day.get("neighbors"),
                "attribution": day.get("attribution"),
                "attribution_drivers": day.get("attribution_drivers"),
            },
            "context_not_direct_cause": {
                "run_7d_km": day.get("run_7d_km"),
                "run_28d_km": day.get("run_28d_km"),
                "accumulated_state": day.get("accumulated_state"),
                "acwr_score": day.get("acwr"),
                "acwr_zone": day.get("acwr_zone"),
            },
            "accuracy_guardrail": "If attribution/neighbors/components are missing, say that exact frontier feature causality is not available; provide contextual interpretation only.",
        }

        evidence = {
            "date": date_str,
            "alert": {
                "label": day.get("alert_label"),
                "tier": day.get("alert_tier"),
                "agreement": day.get("agreement"),
                "integrated_score": day.get("integrated_score"),
            },
            "literature": literature_evidence,
            "personalized": personalized_evidence,
            "frontier": frontier_evidence,
        }

        if model == "all":
            return evidence

        return {
            "date": date_str,
            "alert": evidence["alert"],
            "requested_model": model,
            "evidence": evidence[model],
            "other_scores": {
                "literature": day.get("literature_score"),
                "personalized": day.get("personalized_score"),
                "frontier": day.get("frontier_score"),
                "integrated": day.get("integrated_score"),
            },
        }

    def analyze_progression(
        self,
        end_date: str,
        lookback_days: int = 42,
        reference_weekly_increase_pct: float = 10.0,
    ) -> dict[str, Any]:
        """Analyze running volume progression into a flagged day.

        Computes week-by-week 7-day running volume, absolute and percent changes,
        and compares them with a conservative reference cap. This is not a claim
        that the cap is universally safe; it is a transparent benchmark.
        """
        try:
            end = pd.to_datetime(end_date)
        except Exception:
            return {"error": f"Invalid date format: {end_date}. Use YYYY-MM-DD."}

        start = end - pd.Timedelta(days=lookback_days)
        frame = self.scores_df[(self.scores_df["date"] >= start) & (self.scores_df["date"] <= end)].copy()
        if frame.empty:
            return {"error": f"No data available before {end_date}."}

        weekly_points = []
        current = start + pd.Timedelta(days=6)
        while current <= end:
            row = frame.iloc[(frame["date"] - current).abs().argsort()[:1]].iloc[0]
            run7 = float(row.get("running_7d_sum_m", 0) or 0) / 1000.0
            weekly_points.append({"date": row["date"].strftime("%Y-%m-%d"), "run_7d_km": round(run7, 1)})
            current += pd.Timedelta(days=7)

        steps = []
        for prev, curr in zip(weekly_points, weekly_points[1:]):
            prev_km = float(prev["run_7d_km"])
            curr_km = float(curr["run_7d_km"])
            delta = curr_km - prev_km
            pct = (delta / prev_km * 100.0) if prev_km > 0 else None
            reference_delta = prev_km * (reference_weekly_increase_pct / 100.0)
            reference_target = prev_km + reference_delta
            excess_delta = curr_km - reference_target
            steps.append(
                {
                    "from_date": prev["date"],
                    "to_date": curr["date"],
                    "from_7d_km": prev_km,
                    "to_7d_km": curr_km,
                    "actual_change_km": round(delta, 1),
                    "actual_change_pct": round(pct, 1) if pct is not None else None,
                    "reference_10pct_target_km": round(reference_target, 1),
                    "reference_change_km": round(reference_delta, 1),
                    "excess_vs_reference_km": round(excess_delta, 1),
                }
            )

        max_step = max(steps, key=lambda item: item["excess_vs_reference_km"]) if steps else None
        total_change = weekly_points[-1]["run_7d_km"] - weekly_points[0]["run_7d_km"] if len(weekly_points) > 1 else 0
        total_pct = (total_change / weekly_points[0]["run_7d_km"] * 100.0) if len(weekly_points) > 1 and weekly_points[0]["run_7d_km"] > 0 else None
        day = self.get_day(end.strftime("%Y-%m-%d"))

        return {
            "end_date": end.strftime("%Y-%m-%d"),
            "lookback_days": lookback_days,
            "reference_weekly_increase_pct": reference_weekly_increase_pct,
            "reference_note": "The 10% comparator is a conservative benchmark, not a personalized safe-limit claim.",
            "weekly_points": weekly_points,
            "week_to_week_steps": steps,
            "largest_excess_step": max_step,
            "total_7d_volume_change_km": round(total_change, 1),
            "total_7d_volume_change_pct": round(total_pct, 1) if total_pct is not None else None,
            "flagged_day": day,
            "interpretation_guardrail": "Use this to describe steepness and benchmark deviation. Do not call any volume window 'safe'; say 'lower-risk historically' or 'more conservative progression' only if supported by context.",
        }

    def get_athlete_profile_insights(self) -> dict[str, Any]:
        """Return grounded strengths, weaknesses, risk patterns, and recommendations from the generated athlete profile."""
        if not self.profile:
            return {"error": "Athlete profile not available."}
        return {
            "snapshot": self.profile.get("snapshot"),
            "identity": self.profile.get("identity"),
            "strengths": self.profile.get("strengths", []),
            "weaknesses": self.profile.get("weaknesses", []),
            "recommendations": self.profile.get("recommendations", []),
            "track_insights": self.profile.get("trackInsights", []),
            "risk_windows": self.profile.get("riskWindows", [])[:8],
            "grounding": "Generated from athlete_profile.json; use these as model/history-backed patterns, not generic advice.",
        }

    def compare_periods(self, start_a: str, end_a: str, start_b: str, end_b: str) -> dict[str, Any]:
        """Compare two date ranges across load, scores, and model agreement."""
        def summarize(start_str: str, end_str: str) -> dict[str, Any]:
            start = pd.to_datetime(start_str)
            end = pd.to_datetime(end_str)
            frame = self.scores_df[(self.scores_df["date"] >= start) & (self.scores_df["date"] <= end)].copy()
            if frame.empty:
                return {"error": f"No data from {start_str} to {end_str}."}
            agreement_counts = frame.get("monitoring_signal_agreement", pd.Series(dtype=str)).fillna("unknown").value_counts().head(6).to_dict()
            return {
                "start": start_str,
                "end": end_str,
                "days": int(len(frame)),
                "peak_integrated_score": round(float(frame["integrated_bone_stress_score"].max()), 2),
                "mean_integrated_score": round(float(frame["integrated_bone_stress_score"].mean()), 2),
                "peak_frontier_score": round(float(frame["frontier_strain_score"].max()), 2) if "frontier_strain_score" in frame else None,
                "peak_literature_score": round(float(frame["literature_bone_stress_score"].max()), 2),
                "peak_personalized_score": round(float(frame["personalized_bone_stress_score"].max()), 2),
                "peak_7d_km": round(float(frame["running_7d_sum_m"].max()) / 1000, 1),
                "mean_7d_km": round(float(frame["running_7d_sum_m"].mean()) / 1000, 1),
                "peak_accumulated_state": round(float(frame["accumulated_bone_stress_state"].max()), 2),
                "high_integrated_days": int((frame["integrated_bone_stress_score"] >= 70).sum()),
                "agreement_counts": agreement_counts,
                "top_days": [
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "integrated_score": round(float(row["integrated_bone_stress_score"]), 2),
                        "run_7d_km": round(float(row["running_7d_sum_m"]) / 1000, 1),
                        "reason": row.get("bone_stress_risk_reason"),
                    }
                    for _, row in frame.nlargest(3, "integrated_bone_stress_score").iterrows()
                ],
            }

        a = summarize(start_a, end_a)
        b = summarize(start_b, end_b)
        return {"period_a": a, "period_b": b, "grounding": "Computed from athlete_bone_stress_scores.csv."}

    def get_recent_trend(self, days: int = 30) -> dict[str, Any]:
        """Summarize recent load/risk trend from the latest available day."""
        end = self.scores_df["date"].max()
        start = end - pd.Timedelta(days=days - 1)
        frame = self.scores_df[self.scores_df["date"] >= start].copy()
        if frame.empty:
            return {"error": "No recent data available."}
        first = frame.iloc[0]
        last = frame.iloc[-1]
        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "days": int(len(frame)),
            "current": self.get_day(end.strftime("%Y-%m-%d")),
            "integrated_change": round(float(last["integrated_bone_stress_score"] - first["integrated_bone_stress_score"]), 2),
            "run_7d_change_km": round(float(last["running_7d_sum_m"] - first["running_7d_sum_m"]) / 1000, 1),
            "accumulated_state_change": round(float(last["accumulated_bone_stress_state"] - first["accumulated_bone_stress_state"]), 2),
            "peak_integrated_score": round(float(frame["integrated_bone_stress_score"].max()), 2),
            "peak_7d_km": round(float(frame["running_7d_sum_m"].max()) / 1000, 1),
            "alert_counts": frame.get("operational_alert_label", pd.Series(dtype=str)).fillna("unknown").value_counts().to_dict(),
            "top_recent_days": [
                {"date": row["date"].strftime("%Y-%m-%d"), "score": round(float(row["integrated_bone_stress_score"]), 2), "run_7d_km": round(float(row["running_7d_sum_m"]) / 1000, 1)}
                for _, row in frame.nlargest(5, "integrated_bone_stress_score").iterrows()
            ],
        }

    def analyze_workout(self, date_str: str) -> dict[str, Any]:
        """Analyze a day's workout/load in historical context."""
        day = self.get_day(date_str)
        if "error" in day:
            return day
        row = self.scores_df[self.scores_df["date"].dt.strftime("%Y-%m-%d") == date_str].iloc[0]
        run_days = self.scores_df[pd.to_numeric(self.scores_df.get("running_distance", 0), errors="coerce") > 0].copy()
        distance_km = day.get("run_today_km", 0)
        percentile = None
        if not run_days.empty and distance_km is not None:
            percentile = round(float((run_days["running_distance"] / 1000 <= distance_km).mean() * 100), 1)
        return {
            "date": date_str,
            "workout": {
                "run_distance_km": distance_km,
                "avg_speed": row.get("running_avg_speed"),
                "max_speed": row.get("running_max_speed"),
                "aerobic_training_effect": row.get("running_aerobic_te"),
                "anaerobic_training_effect": row.get("running_anaerobic_te"),
                "distance_percentile_vs_run_days": percentile,
            },
            "context": day,
            "interpretation_guardrail": "Explain whether the day was flagged as a single-session issue or because it sat inside accumulated/recent load context.",
        }

    def analyze_recovery_context(self, date_str: str) -> dict[str, Any]:
        """Return recovery/autonomic context for a day where available."""
        day = self.get_day(date_str)
        if "error" in day:
            return day
        row = self.scores_df[self.scores_df["date"].dt.strftime("%Y-%m-%d") == date_str].iloc[0]
        keys = [
            "actual",
            "prediction",
            "readiness_forecast_error",
            "readiness_forecast_error_score",
            "readiness_model_pessimism_score",
            "recovery_strain_score",
        ]
        return {
            "date": date_str,
            "recovery_values": {key: (round(float(row.get(key)), 2) if pd.notna(row.get(key)) else None) for key in keys},
            "load_context": {"run_7d_km": day.get("run_7d_km"), "run_28d_km": day.get("run_28d_km"), "accumulated_state": day.get("accumulated_state")},
            "frontier_context": {"frontier_score": day.get("frontier_score"), "readiness_forecast_error_score": day.get("readiness_forecast_error_score")},
            "limitation": "Recovery context is limited to fields available in the scored dataset; missing values should be reported as missing, not inferred.",
        }

    def explain_model_disagreement(self, date_str: str) -> dict[str, Any]:
        """Explain why model tracks agree or disagree on a day."""
        evidence = self.explain_day_flag(date_str, model="all")
        if "error" in evidence:
            return evidence
        scores = {
            "literature": evidence["literature"]["score"],
            "personalized": evidence["personalized"]["score"],
            "frontier": evidence["frontier"]["score"],
            "integrated": evidence["alert"].get("integrated_score"),
        }
        available_scores = [score for score in scores.values() if score is not None]
        spread = round(max(available_scores) - min(available_scores), 2) if available_scores else None
        return {
            "date": date_str,
            "scores": scores,
            "score_spread": spread,
            "agreement": evidence["alert"].get("agreement"),
            "literature_basis": evidence["literature"],
            "personalized_basis": evidence["personalized"],
            "frontier_basis": evidence["frontier"],
            "interpretation_guardrail": "Explain disagreements by model design: workload rules vs athlete-history percentiles vs learned-state strain. Do not imply one model is universally right.",
        }

    def suggest_training_adjustment(self, date_str: str | None = None) -> dict[str, Any]:
        """Return grounded adjustment options from current/recent model state and profile recommendations."""
        if not date_str:
            date_str = self.scores_df["date"].max().strftime("%Y-%m-%d")
        day = self.get_day(date_str)
        trend = self.get_recent_trend(30)
        profile = self.get_athlete_profile_insights()
        return {
            "date": date_str,
            "current_state": day,
            "recent_trend": trend,
            "profile_recommendations": profile.get("recommendations", []),
            "grounding": "Use current_state, recent_trend, and profile recommendations. Do not invent a plan beyond these data-backed levers; avoid medical certainty.",
        }

    def investigate_training_state(self, date_str: str | None = None, lookback_days: int = 42) -> dict[str, Any]:
        """Run an agent-ready diagnostic case file for a date.

        This meta-tool collects model state, flag explanations, progression, recovery context,
        recent trend, similar context, and simulation planning into one auditable object.
        """
        if not date_str:
            date_str = self.scores_df["date"].max().strftime("%Y-%m-%d")

        day = self.get_day(date_str)
        if "error" in day:
            return day

        return {
            "case_file_version": "training_state_v1",
            "date": date_str,
            "summary_state": day,
            "model_explanations": self.explain_day_flag(date_str, model="all"),
            "model_disagreement": self.explain_model_disagreement(date_str),
            "progression": self.analyze_progression(date_str, lookback_days=lookback_days),
            "recovery_context": self.analyze_recovery_context(date_str),
            "recent_trend": self.get_recent_trend(30),
            "period_context": self.get_periods_around(date_str, lookback_days=14, lookahead_days=0),
            "adjustment_plan": self.simulate_adjustment_plan(date_str),
            "profile_context": {
                "identity": self.profile.get("identity"),
                "weaknesses": self.profile.get("weaknesses", [])[:4],
                "recommendations": self.profile.get("recommendations", [])[:5],
            },
            "evidence_labels": {
                "strong": "Current scores, load history, model agreement, and progression calculations are directly computed from scored data.",
                "moderate": "Simulation recomputes literature/workload response only.",
                "uncertain": "Exact frontier feature causality is only available when stored attribution/neighbors/components are present.",
            },
        }

    def _extract_differences(self, day1: dict, day2: dict) -> list[str]:
        """Extract key differences between two days."""
        diffs = []
        if day1.get("alert_tier") != day2.get("alert_tier"):
            diffs.append(f"Alert tier: {day2.get('alert_tier')} → {day1.get('alert_tier')}")
        if abs(day1.get("combined_score", 0) - day2.get("combined_score", 0)) > 10:
            diffs.append(f"Score difference: {abs(day1.get('combined_score', 0) - day2.get('combined_score', 0)):.1f} pts")
        if abs(day1.get("run_7d_km", 0) - day2.get("run_7d_km", 0)) > 5:
            diffs.append(f"7-day volume: {day2.get('run_7d_km', 0)} km → {day1.get('run_7d_km', 0)} km")
        if day1.get("acwr_zone") != day2.get("acwr_zone"):
            diffs.append(f"ACWR zone: {day2.get('acwr_zone')} → {day1.get('acwr_zone')}")
        return diffs if diffs else ["No major differences"]

    def list_tool_descriptions(self) -> list[dict[str, Any]]:
        """Return tool definitions for OpenRouter function calling.

        Returns:
            List of tool definitions with parameters and descriptions.
        """
        return [
            {
                "name": "get_day",
                "description": "Retrieve all monitoring data (scores, alert tier, attribution, recommendation) for a single day.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format, e.g. '2026-05-15'",
                        }
                    },
                    "required": ["date_str"],
                },
            },
            {
                "name": "compare_days",
                "description": "Compare two days side-by-side to see how scores, volume, and alert tier changed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date1_str": {
                            "type": "string",
                            "description": "First date in YYYY-MM-DD format",
                        },
                        "date2_str": {
                            "type": "string",
                            "description": "Second date in YYYY-MM-DD format",
                        },
                    },
                    "required": ["date1_str", "date2_str"],
                },
            },
            {
                "name": "get_periods_around",
                "description": "Get context around a date: alert history, peaks, and averages in a +/- N day window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {
                            "type": "string",
                            "description": "Center date in YYYY-MM-DD format",
                        },
                        "lookback_days": {
                            "type": "integer",
                            "description": "Days to look back (default 7)",
                        },
                        "lookahead_days": {
                            "type": "integer",
                            "description": "Days to look ahead (default 7)",
                        },
                    },
                    "required": ["date_str"],
                },
            },
            {
                "name": "simulate_volume_cut",
                "description": "What-if: estimate how bone-stress scores would change if volume were reduced on a specific day.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format",
                        },
                        "factor": {
                            "type": "number",
                            "description": "Volume multiplier. 0.85 = 15% reduction (default).",
                        },
                    },
                    "required": ["date_str"],
                },
            },
            {
                "name": "simulate_down_week_impact",
                "description": "Estimate a reduced-volume down week over a date window, reporting actual scores and recomputed literature-score impact.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                        "factor": {"type": "number", "description": "Volume multiplier; 0.8 means 20% lower."},
                        "days": {"type": "integer", "description": "Number of days in the down-week window."},
                    },
                    "required": [],
                },
            },
            {
                "name": "simulate_adjustment_plan",
                "description": "Search volume-reduction scenarios and find the smallest cut that moves the literature/workload score below a target threshold.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                        "target_literature_score": {"type": "number", "description": "Target literature/workload score threshold, default 70."},
                        "min_factor": {"type": "number", "description": "Lowest volume factor to test, default 0.5."},
                    },
                    "required": ["date_str"],
                },
            },
            {
                "name": "get_frontier_evaluation",
                "description": "Retrieve frontier model validation: lead time, accuracy, and key findings from spring 2024.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "get_riskiest_period",
                "description": "Return the single riskiest bone-stress period across the full history, ranked by a metric.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {
                            "type": "string",
                            "description": "Period metric to rank by (default peak_accumulated_bone_stress_state).",
                        }
                    },
                    "required": [],
                },
            },
            {
                "name": "get_highlighted_days",
                "description": "Return days highlighted by literature, personalized, and frontier models in a date window, with scores and reasons.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                        "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
                        "top_n": {"type": "integer", "description": "Max rows per model."},
                    },
                    "required": [],
                },
            },
            {
                "name": "explain_day_flag",
                "description": "Return model-specific evidence for why a day was flagged, carefully separating direct model evidence from contextual workload facts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                        "model": {
                            "type": "string",
                            "description": "Which model to explain: frontier, literature, personalized, or all.",
                        },
                    },
                    "required": ["date_str"],
                },
            },
            {
                "name": "analyze_progression",
                "description": "Analyze how steep running-volume progression was into a flagged date, comparing actual week-to-week changes with a transparent reference progression cap.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "end_date": {"type": "string", "description": "Flagged/end date in YYYY-MM-DD format."},
                        "lookback_days": {"type": "integer", "description": "Days to look back for progression analysis."},
                        "reference_weekly_increase_pct": {"type": "number", "description": "Benchmark weekly progression percentage, default 10."},
                    },
                    "required": ["end_date"],
                },
            },
            {
                "name": "get_athlete_profile_insights",
                "description": "Return grounded strengths, weaknesses, risk patterns, and recommendations from athlete_profile.json.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
            {
                "name": "compare_periods",
                "description": "Compare two date ranges across load, scores, high days, and model agreement.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_a": {"type": "string", "description": "Start date for first period."},
                        "end_a": {"type": "string", "description": "End date for first period."},
                        "start_b": {"type": "string", "description": "Start date for second period."},
                        "end_b": {"type": "string", "description": "End date for second period."},
                    },
                    "required": ["start_a", "end_a", "start_b", "end_b"],
                },
            },
            {
                "name": "get_recent_trend",
                "description": "Summarize recent load/risk trend from the latest available day.",
                "parameters": {
                    "type": "object",
                    "properties": {"days": {"type": "integer", "description": "Number of recent days, default 30."}},
                    "required": [],
                },
            },
            {
                "name": "analyze_workout",
                "description": "Analyze a workout/day in historical context, including workout load, percentile, and model state.",
                "parameters": {
                    "type": "object",
                    "properties": {"date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."}},
                    "required": ["date_str"],
                },
            },
            {
                "name": "analyze_recovery_context",
                "description": "Return recovery/autonomic context for a date where fields are available.",
                "parameters": {
                    "type": "object",
                    "properties": {"date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."}},
                    "required": ["date_str"],
                },
            },
            {
                "name": "explain_model_disagreement",
                "description": "Explain why literature, personalized, and frontier tracks agree or disagree on a day.",
                "parameters": {
                    "type": "object",
                    "properties": {"date_str": {"type": "string", "description": "Date in YYYY-MM-DD format."}},
                    "required": ["date_str"],
                },
            },
            {
                "name": "suggest_training_adjustment",
                "description": "Return grounded adjustment options from current/recent model state and athlete profile recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {"date_str": {"type": "string", "description": "Optional date in YYYY-MM-DD format; defaults to latest."}},
                    "required": [],
                },
            },
            {
                "name": "investigate_training_state",
                "description": "Run a full auditable diagnostic case file for a date: model state, explanations, progression, recovery, trend, period context, simulation, and evidence labels.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Optional date in YYYY-MM-DD format; defaults to latest."},
                        "lookback_days": {"type": "integer", "description": "Progression lookback window, default 42."},
                    },
                    "required": [],
                },
            },
        ]
