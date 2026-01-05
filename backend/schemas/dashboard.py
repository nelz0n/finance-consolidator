"""Dashboard API response schemas"""
from pydantic import BaseModel, Field
from typing import List, Optional


class CategoryAggregation(BaseModel):
    """Category aggregation data"""
    category: str
    income: float
    expenses: float
    net: float
    count: int
    percentage: float = Field(description="Percentage of total expenses/income")


class MonthlyTrend(BaseModel):
    """Monthly trend data"""
    month: str = Field(description="Month in YYYY-MM format")
    income: float
    expenses: float
    net: float
    count: int
    savings_rate: float = Field(description="Savings rate percentage")


class TopCounterparty(BaseModel):
    """Top counterparty/merchant data"""
    counterparty: str
    total: float
    count: int
    average: float


class SavingsRateData(BaseModel):
    """Savings rate over time"""
    period: str = Field(description="Period in YYYY-MM or YYYY-QX format")
    income: float
    expenses: float
    savings: float
    rate: float = Field(description="Savings rate percentage")


class PeriodMetrics(BaseModel):
    """Metrics for a specific period"""
    income: float
    expenses: float
    net: float
    count: int


class ComparisonResponse(BaseModel):
    """Comparison between two periods"""
    current: PeriodMetrics
    previous: PeriodMetrics
    change: PeriodMetrics
    change_percent: dict = Field(description="Percentage changes for each metric")
