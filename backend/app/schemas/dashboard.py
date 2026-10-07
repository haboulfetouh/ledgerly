from pydantic import BaseModel


class DashboardMetricsOut(BaseModel):
    invoices_processed: int
    needs_review: int
    touchless_rate: float | None
    avg_cost_per_invoice: float | None
    exception_count: int
    exception_aging_days_avg: float | None
    pending_approval_count: int
