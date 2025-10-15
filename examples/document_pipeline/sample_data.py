"""Sample data for document analysis demo."""

Q4_2024_SALES_REPORT = """
QUARTERLY SALES REPORT - Q4 2024
================================

Executive Summary
-----------------
Q4 2024 showed strong performance across all product lines with total revenue 
reaching $15.2M, representing a 23% increase year-over-year. Customer acquisition 
grew by 18%, while customer retention remained steady at 94%.

Key Metrics
-----------
Total Revenue: $15,200,000 (+23% YoY)
Gross Margin: 68% (+3 percentage points)
New Customers: 1,247 (+18% YoY)
Customer Retention: 94% (stable)
Average Deal Size: $12,180 (+7% YoY)
Sales Cycle: 45 days (-5 days vs Q3)

Product Performance
-------------------
1. Enterprise Suite: $8.5M (56% of revenue, +28% YoY)
   - Strongest performer, driven by large enterprise deals
   - Average contract value increased to $85K

2. Professional Edition: $4.2M (28% of revenue, +15% YoY)
   - Steady growth in mid-market segment
   - High renewal rate of 96%

3. Starter Package: $2.5M (16% of revenue, +20% YoY)
   - Strong SMB adoption
   - Excellent upsell potential to Professional

Regional Breakdown
------------------
North America: $9.1M (60% of revenue)
Europe: $4.3M (28% of revenue, fastest growing at +35%)
Asia-Pacific: $1.8M (12% of revenue, +18%)

Sales Team Performance
----------------------
- Top performers exceeded quota by average of 132%
- Team expansion: Hired 8 new sales reps
- Training program completion: 100%
- Customer satisfaction score: 4.7/5.0

Challenges & Opportunities
--------------------------
Challenges:
- Increased competition in mid-market segment
- Longer sales cycles for enterprise deals (up from 42 to 45 days)
- Need for more technical resources in pre-sales

Opportunities:
- Strong pipeline for Q1 2025 ($22M qualified opportunities)
- New partnership agreements signed with 3 major system integrators
- Product expansion into adjacent markets
- European market showing exceptional growth potential

Key Wins
--------
1. Secured largest deal in company history: $2.3M multi-year contract
2. Achieved 100% of quarterly quota for first time in 2024
3. Successfully launched new partner program with 15 active partners
4. Customer Net Promoter Score increased to 68 (from 61 in Q3)

Forecast for Q1 2025
--------------------
Based on current pipeline and market conditions:
- Revenue target: $16.8M (+11% vs Q4 2024)
- Expected new customers: 1,400
- Focus areas: European expansion, enterprise segment, partner channel

Strategic Recommendations
-------------------------
1. Accelerate hiring in Europe to capitalize on growth momentum
2. Invest in sales enablement tools to reduce enterprise sales cycle
3. Expand technical pre-sales team by 3 resources
4. Launch targeted campaign for mid-market segment differentiation
5. Increase marketing investment in APAC region by 25%
6. Develop upsell playbooks for Starter to Professional conversion
7. Implement customer success automation for retention
8. Create dedicated partner success program

Conclusion
----------
Q4 2024 exceeded expectations across all key metrics. The strong foundation 
positions us well for continued growth in 2025. Focus areas for Q1 should be 
European expansion, enterprise segment penetration, and operational scaling to 
support increased demand.
"""

SAMPLE_DOCUMENTS = {
    "quarterly_sales_report_q4_2024": Q4_2024_SALES_REPORT,
    "q4_sales": Q4_2024_SALES_REPORT,
}


def get_sample_document(doc_id: str) -> str:
    """Get a sample document by ID.
    
    Args:
        doc_id: Document identifier
        
    Returns:
        Document text content
    """
    return SAMPLE_DOCUMENTS.get(doc_id.lower(), "")

