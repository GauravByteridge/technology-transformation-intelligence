"""
Query Classifier Service.

Classifies user questions to determine the appropriate processing pipeline:
- STRUCTURED: Numerical, financial, aggregation questions
- UNSTRUCTURED: Document content, qualitative questions
- HYBRID: Questions requiring both structured data and document context
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of queries."""
    STRUCTURED = "STRUCTURED"
    UNSTRUCTURED = "UNSTRUCTURED"
    HYBRID = "HYBRID"


@dataclass
class QueryClassification:
    """Result of query classification."""
    query_type: QueryType
    confidence: float
    
    # For structured queries
    intent: Optional[str] = None  # aggregation, lookup, filter, comparison
    operation: Optional[str] = None  # sum, avg, max, min, count, lookup
    target_dataset: Optional[str] = None  # file or sheet name
    target_columns: list[str] = field(default_factory=list)
    filter_conditions: list[dict] = field(default_factory=list)
    
    # For unstructured queries
    document_type: Optional[str] = None  # brd, audit, policy, etc.
    search_terms: list[str] = field(default_factory=list)
    
    reason: str = ""


class QueryClassifier:
    """
    Classifies queries based on linguistic patterns and keywords.
    
    Uses rule-based classification with keyword matching for:
    - Aggregation keywords (total, sum, average, count)
    - Financial terms (budget, cost, variance, expense)
    - Document keywords (audit, BRD, policy, report)
    - Comparison terms (compare, versus, difference)
    """
    
    # Aggregation keywords
    AGGREGATION_KEYWORDS = {
        "sum": "sum",
        "total": "sum",
        "add up": "sum",
        "combined": "sum",
        "aggregate": "sum",
        "average": "avg",
        "mean": "avg",
        "avg": "avg",
        "maximum": "max",
        "highest": "max",
        "max": "max",
        "top": "max",
        "largest": "max",
        "minimum": "min",
        "lowest": "min",
        "min": "min",
        "smallest": "min",
        "count": "count",
        "how many": "count",
        "number of": "count",
    }
    
    # Financial column keywords
    FINANCIAL_COLUMNS = {
        "budget": "approved_budget",
        "approved budget": "approved_budget",
        "approved_budget": "approved_budget",
        "forecast": "forecast_total_cost",
        "forecast cost": "forecast_total_cost",
        "forecast_total_cost": "forecast_total_cost",
        "actual": "actual_cost",
        "actual cost": "actual_cost",
        "actual_cost": "actual_cost",
        "variance": "cost_variance",
        "cost variance": "cost_variance",
        "cost_variance": "cost_variance",
        "expense": "actual_cost",
        "spending": "actual_cost",
    }
    
    # Dataset/sheet indicators
    DATASET_KEYWORDS = {
        "financial health": "Financial Health",
        "financial": "Financial Health",
        "finance": "Financial Health",
        "budget": "Financial Health",
        "project health": "Project Health",
        "health status": "Project Health",
        "delivery": "Delivery Milestones",
        "milestone": "Delivery Milestones",
        "milestones": "Delivery Milestones",
        "risk": "Enterprise Risks",
        "risks": "Enterprise Risks",
        "enterprise risk": "Enterprise Risks",
        "capacity": "Capacity Summary",
        "team capacity": "Capacity Summary",
        "utilization": "Capacity Summary",
        "executive": "Executive Summary",
        "summary": "Executive Summary",
        "portfolio": None,  # General portfolio - pick based on context
    }
    
    # Document type keywords (unstructured)
    DOCUMENT_KEYWORDS = {
        "brd": "brd",
        "business requirement": "brd",
        "audit": "audit",
        "audit report": "audit",
        "audit finding": "audit",
        "policy": "policy",
        "procedure": "policy",
        "guideline": "policy",
        "jira": "jira",
        "issue": "jira",
        "ticket": "jira",
        "meeting notes": "notes",
        "notes": "notes",
        "remediation": "remediation",
        "control": "controls",
        "controls": "controls",
    }
    
    # Unstructured query patterns
    UNSTRUCTURED_PATTERNS = [
        r"what does .+ say",
        r"what are the .+ mentioned",
        r"summarize",
        r"summarise",
        r"describe",
        r"explain",
        r"what is the purpose",
        r"what are the objectives",
        r"what are the requirements",
        r"what are the risks",
        r"what does .+ recommend",
        r"according to",
        r"based on .+ document",
        r"in the .+ report",
    ]
    
    # Structured query patterns
    STRUCTURED_PATTERNS = [
        r"what is the total",
        r"what is the sum",
        r"how much is",
        r"what is the .+ budget",
        r"what is the .+ cost",
        r"what is the .+ for .+",
        r"which .+ has the highest",
        r"which .+ has the lowest",
        r"list .+ with .+ above",
        r"list .+ with .+ below",
        r"show .+ where",
        r"how many .+ have",
        r"what is the average",
        r"compare .+ and",
        r"what is .+ actual",
        r"what is .+ forecast",
    ]
    
    # Hybrid patterns
    HYBRID_PATTERNS = [
        r"which .+ have .+ and .+ audit",
        r"projects with .+ and .+ risk",
        r"compare .+ financial .+ with .+ findings",
        r"high .+ projects .+ also .+ issues",
    ]
    
    def classify(self, question: str) -> QueryClassification:
        """
        Classify a user question.
        
        Args:
            question: The user's question
            
        Returns:
            QueryClassification with type, confidence, and extracted parameters
        """
        question_lower = question.lower().strip()
        
        # Check for hybrid patterns first (they're most specific)
        if self._matches_patterns(question_lower, self.HYBRID_PATTERNS):
            return self._classify_hybrid(question, question_lower)
        
        # Check for unstructured patterns
        if self._matches_patterns(question_lower, self.UNSTRUCTURED_PATTERNS):
            return self._classify_unstructured(question, question_lower)
        
        # Check for structured patterns
        if self._matches_patterns(question_lower, self.STRUCTURED_PATTERNS):
            return self._classify_structured(question, question_lower)
        
        # Keyword-based classification
        structured_score = self._calculate_structured_score(question_lower)
        unstructured_score = self._calculate_unstructured_score(question_lower)
        
        logger.debug(
            f"Classification scores - Structured: {structured_score}, "
            f"Unstructured: {unstructured_score}"
        )
        
        if structured_score > unstructured_score and structured_score > 0.3:
            return self._classify_structured(question, question_lower)
        elif unstructured_score > structured_score and unstructured_score > 0.3:
            return self._classify_unstructured(question, question_lower)
        elif structured_score > 0 and unstructured_score > 0:
            return self._classify_hybrid(question, question_lower)
        else:
            # Default to unstructured for general questions
            return QueryClassification(
                query_type=QueryType.UNSTRUCTURED,
                confidence=0.5,
                reason="Default classification - no strong indicators"
            )
    
    def _matches_patterns(self, text: str, patterns: list[str]) -> bool:
        """Check if text matches any of the patterns."""
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _calculate_structured_score(self, text: str) -> float:
        """Calculate score for structured query classification."""
        score = 0.0
        
        # Aggregation keywords
        for keyword in self.AGGREGATION_KEYWORDS:
            if keyword in text:
                score += 0.3
        
        # Financial terms
        for keyword in self.FINANCIAL_COLUMNS:
            if keyword in text:
                score += 0.25
        
        # Numbers and comparisons
        if re.search(r'\d+', text):
            score += 0.1
        if any(op in text for op in ["above", "below", "more than", "less than", "greater", "fewer"]):
            score += 0.15
        
        # Dataset references
        for keyword in self.DATASET_KEYWORDS:
            if keyword in text:
                score += 0.1
                break
        
        return min(score, 1.0)
    
    def _calculate_unstructured_score(self, text: str) -> float:
        """Calculate score for unstructured query classification."""
        score = 0.0
        
        # Document keywords
        for keyword in self.DOCUMENT_KEYWORDS:
            if keyword in text:
                score += 0.3
        
        # Qualitative terms
        qualitative_terms = [
            "describe", "explain", "summarize", "summarise", "what does",
            "according to", "mentioned", "stated", "objective", "purpose",
            "strategy", "approach", "recommendation", "concern", "issue"
        ]
        for term in qualitative_terms:
            if term in text:
                score += 0.2
        
        return min(score, 1.0)
    
    def _classify_structured(self, question: str, 
                            question_lower: str) -> QueryClassification:
        """Extract structured query parameters."""
        # Detect operation
        operation = None
        intent = None
        
        for keyword, op in self.AGGREGATION_KEYWORDS.items():
            if keyword in question_lower:
                operation = op
                intent = "aggregation"
                break
        
        if not operation:
            # Check for lookup
            if any(kw in question_lower for kw in ["what is the", "get", "show me"]):
                operation = "lookup"
                intent = "lookup"
            elif any(kw in question_lower for kw in ["list", "which", "show all"]):
                operation = "filter"
                intent = "filter"
        
        # Detect target columns
        columns = []
        for keyword, column in self.FINANCIAL_COLUMNS.items():
            if keyword in question_lower:
                if column not in columns:
                    columns.append(column)
        
        # Detect dataset
        dataset = None
        for keyword, ds in self.DATASET_KEYWORDS.items():
            if keyword in question_lower and ds:
                dataset = ds
                break
        
        # If portfolio mentioned without specific dataset, default to Financial Health
        if "portfolio" in question_lower and not dataset:
            if any(fin_kw in question_lower for fin_kw in ["budget", "cost", "financial", "expense"]):
                dataset = "Financial Health"
        
        return QueryClassification(
            query_type=QueryType.STRUCTURED,
            confidence=0.8,
            intent=intent or "query",
            operation=operation or "lookup",
            target_dataset=dataset,
            target_columns=columns,
            reason=f"Structured query detected - operation: {operation}, columns: {columns}"
        )
    
    def _classify_unstructured(self, question: str,
                              question_lower: str) -> QueryClassification:
        """Extract unstructured query parameters."""
        # Detect document type
        doc_type = None
        for keyword, dtype in self.DOCUMENT_KEYWORDS.items():
            if keyword in question_lower:
                doc_type = dtype
                break
        
        # Extract key search terms
        search_terms = []
        important_words = re.findall(r'\b[a-z]{4,}\b', question_lower)
        stopwords = {"what", "does", "that", "this", "with", "from", "about", "have", "been"}
        search_terms = [w for w in important_words if w not in stopwords][:5]
        
        return QueryClassification(
            query_type=QueryType.UNSTRUCTURED,
            confidence=0.75,
            document_type=doc_type,
            search_terms=search_terms,
            reason=f"Unstructured query - document type: {doc_type}"
        )
    
    def _classify_hybrid(self, question: str,
                        question_lower: str) -> QueryClassification:
        """Extract parameters for hybrid query."""
        # Get both structured and unstructured parameters
        structured = self._classify_structured(question, question_lower)
        unstructured = self._classify_unstructured(question, question_lower)
        
        return QueryClassification(
            query_type=QueryType.HYBRID,
            confidence=0.7,
            intent=structured.intent,
            operation=structured.operation,
            target_dataset=structured.target_dataset,
            target_columns=structured.target_columns,
            document_type=unstructured.document_type,
            search_terms=unstructured.search_terms,
            reason="Hybrid query - requires both structured data and document context"
        )
